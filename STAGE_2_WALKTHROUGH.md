# Stage 2 Walkthrough — Persona Engine

What we built, how it works, and how to migrate to GCP when credits land.

---

## What Stage 2 Does

Stage 1 left us with 23,933 tagged Reddit posts in Postgres. Stage 2 turns that into a queryable persona system:

1. **Embed every post** — convert raw text into a 384-dimensional vector using `all-MiniLM-L6-v2`
2. **Store vectors in pgvector** — build a cosine similarity index for fast lookups
3. **Persona selection** — given a demographic filter (e.g., "25–34 year old male, tech sector"), pull a pool of matching posts and run MMR to pick N maximally diverse personas
4. **Persona cards** — each persona is a `PersonaCard`: post id, demographic tags, sector, and a 300-char text excerpt

Everything runs locally with zero cloud cost. The only change needed for GCP is two env vars.

---

## Embedding Generation

### Why `all-MiniLM-L6-v2`

- 80MB model, 384-dimensional output
- Fast on CPU (~26 posts/sec on a MacBook), very fast on GPU
- Good quality for clustering and retrieval tasks
- Fits comfortably in Postgres `vector(384)` columns

Alternatives: `all-mpnet-base-v2` (768 dims, better quality, needs schema change) or Vertex AI `text-embedding-004` (768 dims, no local GPU needed, see GCP migration section).

### What Gets Embedded

Each post's title and body text are concatenated:

```
{title}\n{text}
```

Capped at 2,000 characters (well within the 512-token limit). Title is included because it often carries the strongest signal — the body can be long and unfocused.

Vectors are **L2-normalized** (`normalize_embeddings=True`). This is non-negotiable: pgvector's cosine distance operator `<=>` assumes unit vectors, and without normalization dot-product similarity doesn't equal cosine similarity.

### Resume Support

The pipeline uses cursor-style pagination — it always queries `WHERE post_id > last_id` rather than `OFFSET N`. This means:

- Safe to kill and restart at any point — already-embedded posts are skipped via `LEFT JOIN ... WHERE pe.post_id IS NULL`
- No performance cliff as the table grows (OFFSET degrades linearly; cursor pagination stays constant)
- Uses `ON CONFLICT (post_id) DO NOTHING` so re-runs are safe

### Results

```
Posts processed : 23,933
Embeddings written : 23,933 (100%)
Speed : ~26 posts/sec (MacBook M-series CPU)
Total time : 93 seconds
ivfflat index build : 0.8 seconds
```

---

## pgvector Index

We use `ivfflat` (Inverted File with Flat compression), not `hnsw`:

```sql
CREATE INDEX idx_embeddings_vector
ON post_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Why ivfflat over hnsw at this scale:**

| | ivfflat | hnsw |
|---|---|---|
| Build time | Fast (~1s for 24K rows) | Slow (minutes at 100K+) |
| Query speed | Good enough (<5ms for 24K) | Faster at scale |
| Memory | Lower | Higher |
| Sweet spot | < 100K rows | > 100K rows |

`lists = 100` is the number of partition buckets. Rule of thumb: `sqrt(num_rows)` ≈ 155 for 24K rows, but 100 is standard and good for this dataset size. Switch to `hnsw` on Cloud SQL if you grow past ~100K posts and query latency matters.

**Critical:** the index is built **after** all embeddings are inserted, not during. Building HNSW or ivfflat during bulk inserts forces an index rebuild on every row — ~10x slower.

---

## Persona Selection Algorithm

### The Problem

Naively picking the top N posts matching a demographic filter is bad: you'll get N very similar posts from the same subreddit thread, or 50 variants of the same opinion. That doesn't simulate a diverse focus group.

### Maximal Marginal Relevance (MMR)

MMR iteratively picks the next item that maximizes a tradeoff between:
- **Relevance** — how well it matches the query (here, all candidates are equally relevant since we pre-filtered by demographics)
- **Diversity** — how different it is from already-selected items (measured by cosine distance)

```
score(i) = λ · relevance(i) − (1 − λ) · max_similarity(i, selected)
```

With `λ = 0.5` (equal weight to relevance and diversity), the algorithm:
1. Seeds with one candidate (arbitrary)
2. Each iteration picks the candidate with highest MMR score
3. Repeats until N personas are selected

Since all candidates are equally relevant (pre-filtered), this reduces to: **always pick the candidate most dissimilar to the current selection**. The result is a set of personas that cover the space of opinions rather than clustering around the majority view.

### Pipeline

```
demographic_filter + sector
        ↓
SQL query (up to 500 candidates, random ORDER)
        ↓
MMR over 384-dim embeddings
        ↓
N PersonaCards
```

The SQL random ordering + MMR together produce non-deterministic but consistently diverse results. Each call to `select_personas()` returns a different set.

### Diversity Results

Manual spot-check (5 personas, no filters):

```
Avg pairwise cosine distance: 1.056  (target: > 0.3)
```

Cosine distance for unit vectors ranges from 0 (identical) to 2 (opposite directions). A value of 1.0+ means the vectors point into completely different regions of the embedding space — the personas are genuinely talking about different things.

---

## Files Built

| File | What it does |
|------|-------------|
| `src/embeddings.py` | `embed(texts)` — switches between local MiniLM and Vertex AI via `EMBEDDING_PROVIDER` env var |
| `src/persona.py` | `select_personas()`, `mmr_select()`, `PersonaCard` dataclass |
| `src/db.py` | Added `get_unembedded_posts`, `insert_embeddings`, `create_ivfflat_index`, `get_posts_with_embeddings` |
| `scripts/generate_embeddings.py` | Resumable batch pipeline; builds ivfflat index at end |
| `scripts/persona_report.py` | CLI spot-check: prints N diverse PersonaCards with diversity metric |
| `tests/test_embeddings.py` | 6 tests: unit norm, batch, empty input, return types |
| `tests/test_persona.py` | 7 tests: MMR correctness, no duplicates, fewer-than-n, PersonaCard structure |

---

## How to Re-run Anything

```bash
# Generate embeddings for all posts (resumes automatically if stopped)
python3 scripts/generate_embeddings.py

# Faster batches (tweak to available RAM)
python3 scripts/generate_embeddings.py --chunk-size 2000 --batch-size 512

# Just rebuild the vector index (e.g. after adding more posts)
python3 scripts/generate_embeddings.py --index-only

# Spot-check 5 personas (any sector/demographic)
python3 scripts/persona_report.py --n 5

# Filter by sector
python3 scripts/persona_report.py --sector tech --n 10

# Filter by demographics
python3 scripts/persona_report.py --sector financial --age-group 25-34 --gender male --n 10

# Run all tests
python3 -m pytest tests/ -v
```

---

## Current Data State

```
Total posts       : 23,933
Posts embedded    : 23,933  (100%)
Embedding model   : all-MiniLM-L6-v2 (384 dims)
Vector index      : ivfflat (lists=100, cosine ops)

SECTOR SPLIT
  financial : 10,246  (42.8%)
  tech      :  7,926  (33.1%)
  political :  5,743  (24.0%)

DEMOGRAPHIC COVERAGE
  income_bracket : 17,029 posts  (71.2%)
  age_group      : 13,293 posts  (55.5%)
  gender         :  2,884 posts  (12.1%)
  parent_status  :    563 posts   (2.4%)

TAG METHOD SPLIT
  subreddit_prior  : 28,701  (85%)
  self_disclosure  :  5,071  (15%)
```

---

## Migrating to GCP

When GCP credits land, the migration is **two env var changes and one CLI command**. No code changes.

### Step 1 — Switch Embedding Provider to Vertex AI

Set in your `.env` or shell:

```bash
EMBEDDING_PROVIDER=vertexai
EMBEDDING_MODEL=text-embedding-004
EMBEDDING_DIM=768
```

**Important:** Vertex AI's model outputs 768-dimensional vectors, not 384. You'll need to alter the pgvector column before embedding on Cloud SQL:

```sql
ALTER TABLE post_embeddings ALTER COLUMN embedding TYPE vector(768);
```

Then re-run `scripts/generate_embeddings.py` against Cloud SQL. At 24K posts, cost is ~$0.002 (Vertex AI charges $0.0001 per 1K characters; avg post ≈ 200 chars).

Install the SDK first:
```bash
pip install google-cloud-aiplatform
```

The `_embed_vertexai()` function in `src/embeddings.py` is already wired up — it just needs the SDK installed and ADC configured.

### Step 2 — Point at Cloud SQL

```bash
DATABASE_URL=postgresql://fg_user:PASSWORD@/focusgroups?host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME
```

Or use individual vars:
```bash
PG_HOST=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME
PG_DB=focusgroups
PG_USER=fg_user
PG_PASSWORD=your_password
```

The connection string format changes for Cloud SQL Auth Proxy (Unix socket path instead of TCP). No Python code changes — `src/db.py:get_conn()` reads from env vars.

### Step 3 — Run Cloud SQL Auth Proxy

Cloud SQL requires the proxy for secure connections:

```bash
# Install (once)
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.x.x/cloud-sql-proxy.darwin.amd64
chmod +x cloud-sql-proxy

# Run (keep alive in a separate terminal)
./cloud-sql-proxy PROJECT_ID:REGION:INSTANCE_NAME
```

The proxy listens on `localhost:5432` by default, so you can also use TCP (`PG_HOST=localhost`) if the proxy is running locally.

### Step 4 — Enable pgvector on Cloud SQL

Cloud SQL Postgres supports pgvector natively. Enable it once after creating the instance:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

The schema in `db/init.sql` already includes this — just re-run init against the Cloud SQL instance.

### Step 5 — Re-run Embedding Pipeline on Cloud SQL

```bash
# With EMBEDDING_PROVIDER=vertexai and DATABASE_URL pointing at Cloud SQL:
python3 scripts/generate_embeddings.py --chunk-size 500
```

Chunk size of 500 is safer for the first cloud run — Vertex AI has a 250 texts/request limit; the pipeline handles batching automatically.

### Full Migration Checklist

```
[ ] Create Cloud SQL Postgres 16 instance with pgvector flag enabled
[ ] Run db/init.sql against Cloud SQL to create schema + seed lookup tables
[ ] Install cloud-sql-proxy and verify connection
[ ] Set EMBEDDING_PROVIDER=vertexai, EMBEDDING_MODEL=text-embedding-004, EMBEDDING_DIM=768
[ ] ALTER TABLE post_embeddings ALTER COLUMN embedding TYPE vector(768)
[ ] Set DATABASE_URL / PG_* vars pointing at Cloud SQL
[ ] Run scripts/generate_embeddings.py (embeds from scratch on cloud, ~$0.002 total)
[ ] Run scripts/persona_report.py --n 5 to verify personas work on cloud
[ ] Run python3 -m pytest tests/ to confirm all tests pass against cloud DB
```

### What Does NOT Change

- All Python source code in `src/` and `scripts/`
- The MMR persona selection logic
- The pgvector query syntax (`<=>` operator is identical on Cloud SQL)
- The normalized schema
- The test suite

The abstraction held: local and cloud are the same system, just different connection strings and embedding backends.

---

## What's Next — Stage 3

Stage 3 is the actual product:

- **FastAPI backend** on Cloud Run — `/sessions`, `/personas`, `/respond` endpoints
- **React frontend** on Cloud Run — focus group creation UI
- **Claude API** for generating persona responses (conditioned on demographic profile + representative post text)
- **Session management** — create a focus group, specify criteria, get back responses from 20–50 AI personas
- **Export** — PDF/CSV of session results

The persona cards built in Stage 2 become the context fed to Claude: each persona's demographic tags + text excerpt become a system prompt grounding Claude's response in a real person's voice and concerns.
