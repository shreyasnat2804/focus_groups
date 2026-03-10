-- Migration 006: Add missing indexes for frequently queried columns.
-- See plans/db_indexes_plan.md for rationale.

BEGIN;

-- Index on author for multi-post author lookups (GROUP BY author)
CREATE INDEX IF NOT EXISTS idx_posts_author ON posts (author);

-- Index on sector stored in metadata JSONB (WHERE metadata->>'sector' = ...)
CREATE INDEX IF NOT EXISTS idx_posts_sector ON posts ((metadata->>'sector'));

-- Index on created_at for ORDER BY pagination on sessions
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON focus_group_sessions (created_at DESC);

COMMIT;
