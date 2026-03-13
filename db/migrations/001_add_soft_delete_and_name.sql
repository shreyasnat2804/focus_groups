-- Migration 001: Add soft delete and name columns to focus_group_sessions
--
-- These columns are already present in init.sql (for fresh databases).
-- This migration exists to upgrade existing databases that were created
-- before these columns were added to the schema.

BEGIN;

-- Soft delete support: allows "trash" / recently-deleted functionality
ALTER TABLE focus_group_sessions
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_sessions_deleted_at
    ON focus_group_sessions(deleted_at);

-- Optional display name for sessions
ALTER TABLE focus_group_sessions
    ADD COLUMN IF NOT EXISTS name VARCHAR(255) DEFAULT NULL;

COMMIT;
