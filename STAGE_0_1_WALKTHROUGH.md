# Stage 0 & 1 Walkthrough

What we built, how it works, and where things stand.

---

## Stage 0 — Reddit Scraper + Postgres Pipeline

**Goal:** Get raw text data into a database with zero cost and no Reddit API credentials.

### The Problem with Reddit's API

Reddit killed self-service API access in 2023. PRAW (the standard Python Reddit wrapper) now requires OAuth credentials, which means an approved app, rate limits, and a terms agreement. For a POC, that's unnecessary friction.

**Solution:** Reddit exposes public JSON endpoints for every subreddit — just append `.json` to any URL. No auth required. `https://www.reddit.com/r/personalfinance/top.json?limit=100&t=year` returns the top 100 posts from the past year as plain JSON. We built the scraper entirely on this.

### What `src/scraper.py` Does

**Subreddit targets** — 24 subreddits across 3 sectors, chosen specifically for being text-heavy (self-posts with body text, not just links):

| Sector | Subreddits |
|--------|-----------|
| `financial` | personalfinance, povertyfinance, financialindependence, fatFIRE, Bogleheads, Frugal, investing, wallstreetbets |
| `tech` | cscareerquestions, programming, homelab, buildapc, techsupport, apple, Android, AskTechnology |
| `political` | NeutralPolitics, moderatepolitics, AskTrumpsupporters, Ask_Politics, PoliticalDiscussion, conservative, Libertarian, centrist |

**Rate limiting** — Reddit blocks scrapers that hammer the API. The scraper:
- Waits 6–9 seconds (randomised) between each subreddit page request
- Rotates user agents across 4 different browser strings every 3 pages
- Handles 429 responses with `Retry-After` header backoff
- Handles 403/404 (unavailable subreddits) gracefully without crashing

**Post filtering** — not everything is useful for training:
- `score < 5` → skip (low-signal posts)
- `body < 50 chars` → skip (too short for demographic inference)
- `body == "[deleted]" or "[removed]"` → skip
- `author == "AutoModerator"` → skip

**Dual-write** — the scraper writes to two places simultaneously:
1. `data/posts.jsonl` — newline-delimited JSON, one post per line (JSONL), append-only
2. Postgres `posts` table — via `src/db.py:insert_posts()`

The JSONL file is the source-of-truth backup. If Postgres is unreachable, the scraper keeps writing to JSONL and logs a warning. A separate `scripts/load_jsonl.py` can replay JSONL into Postgres later.

**Deduplication** — on startup, the scraper loads all existing `source_id` values from the JSONL file into a `seen_ids` set. Any post already collected (identified by Reddit's post ID) is skipped. The DB insert also uses `ON CONFLICT (source_id) DO NOTHING` so re-runs are safe.

### Database Schema (Stage 0)

Single table to start:

```sql
posts (
    id           BIGSERIAL PRIMARY KEY,
    source       VARCHAR(20)  DEFAULT 'reddit',
    source_id    VARCHAR(100) UNIQUE,   -- Reddit's post ID (e.g. "t3_abc123")
    subreddit    VARCHAR(100),
    author       VARCHAR(100),
    title        TEXT,
    text         TEXT,
    score        INT,
    num_comments INT,
    created_utc  TIMESTAMPTZ,
    scraped_at   TIMESTAMPTZ DEFAULT NOW(),
    metadata     JSONB                  -- sector, permalink stored here
)
```

**Postgres setup** — local Docker or native Homebrew `postgresql@16`. The `db/init.sql` script creates all tables and indexes idempotently (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`), so it's safe to re-run.

### Result

After running the scraper across all 24 subreddits: **10,209 posts** collected, all stored in local Postgres.

---

## Stage 1 — Demographic Tagging Pipeline

**Goal:** Infer demographic attributes from post text so each post can be associated with a persona (age group, gender, parent status, income bracket).

### Why Demographic Tags?

The end product is a synthetic focus group simulator. To simulate responses from "a 35-year-old middle-income parent," you need training data where you know the demographic profile of the person who wrote each post. Reddit users often reveal this naturally in their writing.

### Two-Layer Tagger (`src/tagger.py`)

#### Layer 1 — Self-Disclosure Regex (confidence 0.85–0.95)

Scans post text for explicit first-person statements. Takes priority over Layer 2 for any dimension it covers.

**Age** — 7 patterns, e.g.:
- `"I'm 28 years old"` → `age_group: 25-34`
- `"as a 34-year-old"` → `age_group: 25-34`
- `"25yo"`, `"34F"`, `"age: 28"`, `"just turned 45"` → all handled
- Raw age → bucket mapping: under_18 / 18-24 / 25-34 / 35-44 / 45-54 / 55-64 / 65+

**Gender** — 16 patterns:
- Direct: `"I'm a woman"`, `"34F"`, `"she/her"`, `"I identify as male"`
- Relational inference: `"my husband"` → female, `"my wife"` → male

**Parent status:**
- `"my kids"`, `"as a mom/dad"`, `"my toddler"` → parent
- `"no kids"`, `"childfree"`, `"don't have any kids"` → non_parent

**Income** — three sub-patterns in priority order:
1. Narrative: `"six figures"` → high_income, `"living paycheck to paycheck"` → lower_income
2. `"$120k"` → parse to annual salary → bracket (< $30k: lower, $30–75k: middle, $75k+: high)
3. `"$125,000"` raw amounts (≥ $20k threshold to avoid purchase prices)

#### Layer 2 — Subreddit Priors (confidence 0.4–0.7)

Applied only to dimensions not already covered by Layer 1. Based on known community demographics:

- `povertyfinance` → `income_bracket: lower_income` (0.6)
- `fatFIRE` → `income_bracket: high_income` (0.7)
- `homelab`, `buildapc` → `gender: male` (0.5)
- `cscareerquestions`, `programming` → `age_group: 25-34` (0.4), `income_bracket: middle_income` (0.5)
- `conservative`, `AskTrumpsupporters` → `age_group: 35-44` (0.4)

Lower confidence scores reflect that these are population-level guesses, not individual disclosures.

### Tag Storage (Normalized Schema)

Tags are stored as integer foreign keys rather than raw strings. This was done via a schema normalization in a separate branch and merged + applied during Stage 1.

```
demographic_dimensions  →  demographic_values  →  demographic_tags
(age_group, gender...)     (age_group / 25-34)     (post_id, value_id, confidence, method)
```

Lookup tables are seeded once at DB init. 4 dimensions, 14 possible values, 3 sectors, 1 embedding model — all referenced by SMALLINT IDs throughout.

**Why normalize?** Integer FK lookups are faster, the schema enforces valid values at the DB level, and queries are unambiguous (no typo risks in string matching). The tradeoff is slightly more verbose queries — every read JOINs through `demographic_values` and `demographic_dimensions` to recover the human-readable strings.

### Supporting Scripts

| Script | What it does |
|--------|-------------|
| `scripts/tag_existing.py` | Re-tags all posts already in DB. Uses cursor pagination (`WHERE id > last_id`) instead of OFFSET to avoid drift on large tables. Skips already-tagged posts in-loop. |
| `scripts/quality_report.py` | Coverage analysis — what % of posts have each dimension tagged, top values, method breakdown. |
| `scripts/export_csv.py` | Exports `posts + demographic_tags` to `data/posts_tagged.csv`. Text truncated in Python (not SQL) to avoid `CharacterNotInRepertoire` errors from malformed UTF-8 in scraped content. |
| `scripts/check_deps.py` | Verifies Python version, required packages, and Postgres connectivity. Prints fix hints on failure. |

### Tagging Results (Live Data)

```
Total posts       : 10,209
Posts with ≥1 tag :  10,197  (99.9%)

DIMENSION COVERAGE
  income_bracket   6,459  (63.3%)   ← strong, driven by financial subreddits
  age_group        5,017  (49.1%)   ← moderate
  gender           1,847  (18.1%)   ← low — people don't mention gender often
  parent_status      345   (3.4%)   ← very low — niche signal

TAG METHOD BREAKDOWN
  subreddit_prior   11,070  (81%)
  self_disclosure    2,600  (19%)
```

99.9% coverage is high because subreddit priors fire on almost every post (any post in `personalfinance` gets `income_bracket: middle_income`). The more meaningful number is self-disclosure rate: 19% of tags came from actual first-person text — those are the high-confidence signals.

**Sector split:**
- financial: 4,359 posts (100% tagged)
- tech: 3,216 posts (100% tagged)
- political: 2,616 posts (100% tagged)

---

## What's Not Done Yet

- **pgvector embeddings** — `post_embeddings` table exists and is ready, but no embeddings have been generated. This is Stage 2 (sentence-transformers on Lambda GPU or Colab).
- **`post_sectors` table** — exists but empty. Sector is currently stored in `posts.metadata->>'sector'` (set at scrape time from the subreddit mapping). The `post_sectors` table is for future classifier-assigned confidence scores.
- **30k post target** — we have 10k. The scraper only ran 2 pages per subreddit. Running 5 pages per sub would reach ~25k; adding more subreddits gets to 30k+.
- **LoRA fine-tuning** — Stage 3. Requires embeddings first.

---

## How to Re-run Anything

```bash
# Scrape more posts (add to existing data)
python3 src/scraper.py

# Tag any untagged posts
python3 scripts/tag_existing.py -v

# Check tagging quality
python3 scripts/quality_report.py -v

# Export to CSV
python3 scripts/export_csv.py -v

# Check all dependencies
python3 scripts/check_deps.py -v
```
