-- Migration 004: Soft delete support for focus group sessions
-- Adds deleted_at column for trash/recently-deleted functionality.

BEGIN;

ALTER TABLE focus_group_sessions
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_sessions_deleted_at
    ON focus_group_sessions(deleted_at);

COMMIT;
