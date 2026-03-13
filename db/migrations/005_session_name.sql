-- Add optional display name to sessions.
-- When NULL, the frontend falls back to parsing the product name from the question field.
ALTER TABLE focus_group_sessions
    ADD COLUMN IF NOT EXISTS name TEXT;
