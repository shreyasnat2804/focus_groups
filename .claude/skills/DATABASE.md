# DATABASE.md — Postgres + pgvector

## Local Setup

```bash
docker-compose up -d
psql -h localhost -U fg_user -d focusgroups
```

Password: set in `.env` as `POSTGRES_PASSWORD`, defaults to `localdev`.

## Schema

The init script lives at `db/init.sql`. Migrations in `db/migrations/`.

### Lookup tables (small, seeded once)

```sql
demographic_dimensions  (id SMALLSERIAL, name VARCHAR(50) UNIQUE)
    -- age_group | gender | parent_status | income_bracket

demographic_values      (id SMALLSERIAL, dimension_id FK, value VARCHAR(100), UNIQUE(dimension_id,value))
    -- e.g. (age_group, 25-34) | (gender, female) | (income_bracket, middle_income)

sectors                 (id SMALLSERIAL, name VARCHAR(50) UNIQUE)
    -- tech | financial | political

embedding_models        (id SMALLSERIAL, name VARCHAR(100) UNIQUE, dimensions SMALLINT)
    -- all-MiniLM-L6-v2 / 384
```

### Core tables

```sql
-- Raw scraped posts
CREATE TABLE posts (
    id           BIGSERIAL PRIMARY KEY,
    source       VARCHAR(20)  NOT NULL DEFAULT 'reddit',
    source_id    VARCHAR(100) UNIQUE NOT NULL,
    subreddit    VARCHAR(100),
    author       VARCHAR(100),
    title        TEXT,
    text         TEXT NOT NULL,
    score        INT,
    num_comments INT,
    created_utc  TIMESTAMPTZ NOT NULL,
    scraped_at   TIMESTAMPTZ DEFAULT NOW(),
    metadata     JSONB DEFAULT '{}'        -- sector, permalink, etc.
);

-- Demographic tags — FK to demographic_values instead of raw strings
CREATE TABLE demographic_tags (
    id                   BIGSERIAL PRIMARY KEY,
    post_id              BIGINT   NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    demographic_value_id SMALLINT NOT NULL REFERENCES demographic_values(id),
    confidence           FLOAT    NOT NULL,   -- 0.0-1.0
    method               VARCHAR(30) NOT NULL, -- self_disclosure | subreddit_prior
    created_at           TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (post_id, demographic_value_id, method)
);

-- Embeddings for similarity search
CREATE TABLE post_embeddings (
    id       BIGSERIAL PRIMARY KEY,
    post_id  BIGINT   NOT NULL REFERENCES posts(id) ON DELETE CASCADE UNIQUE,
    model_id SMALLINT NOT NULL REFERENCES embedding_models(id),
    embedding vector(384) NOT NULL
);

-- Sector classification
CREATE TABLE post_sectors (
    id         BIGSERIAL PRIMARY KEY,
    post_id    BIGINT   NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    sector_id  SMALLINT NOT NULL REFERENCES sectors(id),
    confidence FLOAT    NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Key decision**: HNSW index is commented out in `init.sql`. Build it *after* bulk embedding insertion — building during inserts is 10x slower.

### To recover dimension/value strings in queries

```sql
-- demographic_tags → human-readable
JOIN demographic_values     dv ON dv.id  = dt.demographic_value_id
JOIN demographic_dimensions dd ON dd.id  = dv.dimension_id
-- dd.name = dimension, dv.value = value

-- post_sectors → sector name
JOIN sectors s ON s.id = ps.sector_id

-- post_embeddings → model name
JOIN embedding_models em ON em.id = pe.model_id
```

## Connection Pattern (Python)

```python
import psycopg2
from psycopg2.extras import execute_values
import os

def get_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5432"),
        dbname=os.getenv("PG_DB", "focusgroups"),
        user=os.getenv("PG_USER", "fg_user"),
        password=os.getenv("PG_PASSWORD", "localdev"),
    )
```

## Bulk Insert Pattern

```python
# Posts — unchanged
insert_posts(conn, posts)   # list of dicts with scraper fields

# Tags — pass pre-loaded value_ids map to avoid a round-trip per batch
from src.db import load_demographic_value_ids, insert_tags

value_ids = load_demographic_value_ids(conn)   # call once at startup
insert_tags(conn, tags, value_ids=value_ids)   # tags: [{post_id, dimension, value, confidence, method}]
```

## Pitfalls

- **pgvector dimensions are fixed per column.** If you change embedding models, you need a new column or table. The schema uses 384 (MiniLM). If switching to a larger model, ALTER the column dimension.
- **Don't build HNSW index before bulk insert.** Each insert triggers index rebuild. Insert all embeddings first, then `CREATE INDEX`.
- **Use `ON CONFLICT DO NOTHING`** for scraped data — duplicate source_ids are expected across runs.
- **JSONB `metadata`** is the escape hatch. Put anything non-standard there rather than adding columns.

## Migration to Cloud SQL

When moving to GCP Cloud SQL:
1. Cloud SQL Postgres supports pgvector natively (enable via database flags)
2. Use Cloud SQL Auth Proxy for connections: `cloud-sql-proxy PROJECT:REGION:INSTANCE`
3. Same schema, same code — just change connection env vars
