# DATABASE.md — Postgres + pgvector

## Local Setup

```bash
docker-compose up -d
psql -h localhost -U fg_user -d focusgroups
```

Password: set in `.env` as `POSTGRES_PASSWORD`, defaults to `localdev`.

## Schema

The init script lives at `db/init.sql`. Core tables:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- Raw scraped posts
CREATE TABLE posts (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(20) NOT NULL DEFAULT 'reddit',  -- reddit, twitter, etc.
    source_id VARCHAR(100) UNIQUE NOT NULL,         -- reddit post/comment id
    subreddit VARCHAR(100),
    author VARCHAR(100),
    text TEXT NOT NULL,
    score INT,
    created_utc TIMESTAMPTZ NOT NULL,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'                     -- flair, parent_id, etc.
);

-- Demographic tags (one post can have multiple inferred tags)
CREATE TABLE demographic_tags (
    id BIGSERIAL PRIMARY KEY,
    post_id BIGINT REFERENCES posts(id) ON DELETE CASCADE,
    dimension VARCHAR(50) NOT NULL,    -- age_group, gender, income_bracket, etc.
    value VARCHAR(100) NOT NULL,       -- 25-34, female, middle_income, etc.
    confidence FLOAT NOT NULL,         -- 0.0-1.0
    method VARCHAR(30) NOT NULL,       -- self_disclosure, subreddit_prior, nlp_classifier
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Embeddings for similarity search
CREATE TABLE post_embeddings (
    id BIGSERIAL PRIMARY KEY,
    post_id BIGINT REFERENCES posts(id) ON DELETE CASCADE UNIQUE,
    model VARCHAR(100) NOT NULL,       -- all-MiniLM-L6-v2, etc.
    embedding vector(384) NOT NULL     -- dimension matches model output
);

-- Sector classification
CREATE TABLE post_sectors (
    id BIGSERIAL PRIMARY KEY,
    post_id BIGINT REFERENCES posts(id) ON DELETE CASCADE,
    sector VARCHAR(50) NOT NULL,       -- tech, financial, political
    confidence FLOAT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_posts_subreddit ON posts(subreddit);
CREATE INDEX idx_posts_created ON posts(created_utc);
CREATE INDEX idx_tags_post ON demographic_tags(post_id);
CREATE INDEX idx_tags_dimension_value ON demographic_tags(dimension, value);
CREATE INDEX idx_embeddings_post ON post_embeddings(post_id);
CREATE INDEX idx_sectors_post ON post_sectors(post_id);

-- HNSW index for vector similarity (build after bulk insert for speed)
-- CREATE INDEX idx_embeddings_vector ON post_embeddings USING hnsw (embedding vector_cosine_ops);
```

**Key decision**: HNSW index is commented out. Build it *after* bulk embedding insertion — building during inserts is 10x slower.

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
def insert_posts(conn, posts: list[dict]):
    """posts: list of dicts with keys matching columns."""
    cols = ["source_id", "subreddit", "author", "text", "score", "created_utc", "metadata"]
    values = [[p[c] for c in cols] for p in posts]
    with conn.cursor() as cur:
        execute_values(
            cur,
            f"INSERT INTO posts ({','.join(cols)}) VALUES %s ON CONFLICT (source_id) DO NOTHING",
            values,
        )
    conn.commit()
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
