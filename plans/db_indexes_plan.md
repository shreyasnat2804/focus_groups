# Fix: Add Missing Database Indexes

## Problem
Missing indexes on frequently queried columns:
- `posts.author` — used in `get_authors_with_multiple_posts()` (GROUP BY author)
- `posts.metadata->>'sector'` — used in `get_posts_with_embeddings()` WHERE clause

## Severity: MEDIUM

## Changes

### 1. Create migration SQL file `db/003_add_indexes.sql`

```sql
-- Index on author for multi-post author lookups
CREATE INDEX IF NOT EXISTS idx_posts_author ON posts (author);

-- Index on sector stored in metadata JSONB
CREATE INDEX IF NOT EXISTS idx_posts_sector ON posts ((metadata->>'sector'));

-- Index on focus_group_sessions.deleted_at for soft-delete filtering
CREATE INDEX IF NOT EXISTS idx_sessions_deleted_at ON focus_group_sessions (deleted_at);

-- Index on focus_group_sessions.created_at for ORDER BY pagination
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON focus_group_sessions (created_at DESC);
```

### 2. Apply
- Run manually or add to DB init script
- All use `IF NOT EXISTS` so safe to re-run

## Files Touched
- `db/003_add_indexes.sql` (new)
