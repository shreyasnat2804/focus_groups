-- Migration 003: Focus group session tables
-- Stores session metadata and per-persona responses for the RAG + Claude POC.

BEGIN;

CREATE TABLE IF NOT EXISTS focus_group_sessions (
    id                 BIGSERIAL    PRIMARY KEY,
    sector             VARCHAR(50),
    demographic_filter JSONB        DEFAULT '{}',
    question           TEXT         NOT NULL,
    num_personas       SMALLINT     NOT NULL,
    status             VARCHAR(20)  NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    created_at         TIMESTAMPTZ  DEFAULT NOW(),
    completed_at       TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS focus_group_responses (
    id              BIGSERIAL   PRIMARY KEY,
    session_id      BIGINT      NOT NULL REFERENCES focus_group_sessions(id) ON DELETE CASCADE,
    post_id         BIGINT      NOT NULL REFERENCES posts(id),
    persona_summary TEXT        NOT NULL,
    system_prompt   TEXT        NOT NULL,
    response_text   TEXT        NOT NULL,
    model           VARCHAR(100) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_responses_session ON focus_group_responses(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status   ON focus_group_sessions(status);

COMMIT;
