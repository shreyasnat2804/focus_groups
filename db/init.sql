CREATE EXTENSION IF NOT EXISTS vector;

-- ── Lookup tables (seeded once, rarely change) ────────────────────────────────

CREATE TABLE IF NOT EXISTS demographic_dimensions (
    id   SMALLSERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS demographic_values (
    id           SMALLSERIAL PRIMARY KEY,
    dimension_id SMALLINT    NOT NULL REFERENCES demographic_dimensions(id),
    value        VARCHAR(100) NOT NULL,
    UNIQUE (dimension_id, value)
);

CREATE TABLE IF NOT EXISTS sectors (
    id   SMALLSERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS embedding_models (
    id         SMALLSERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL UNIQUE,
    dimensions SMALLINT     NOT NULL
);

-- Seed data
INSERT INTO demographic_dimensions (name) VALUES
    ('age_group'), ('gender'), ('parent_status'), ('income_bracket')
ON CONFLICT DO NOTHING;

INSERT INTO demographic_values (dimension_id, value)
SELECT dd.id, v.value
FROM (VALUES
    ('age_group',      'under_18'),
    ('age_group',      '18-24'),
    ('age_group',      '25-34'),
    ('age_group',      '35-44'),
    ('age_group',      '45-54'),
    ('age_group',      '55-64'),
    ('age_group',      '65+'),
    ('gender',         'male'),
    ('gender',         'female'),
    ('parent_status',  'parent'),
    ('parent_status',  'non_parent'),
    ('income_bracket', 'lower_income'),
    ('income_bracket', 'middle_income'),
    ('income_bracket', 'high_income')
) AS v(dimension, value)
JOIN demographic_dimensions dd ON dd.name = v.dimension
ON CONFLICT DO NOTHING;

INSERT INTO sectors (name) VALUES ('tech'), ('financial'), ('political')
ON CONFLICT DO NOTHING;

INSERT INTO embedding_models (name, dimensions) VALUES ('all-MiniLM-L6-v2', 384)
ON CONFLICT DO NOTHING;

-- ── Core tables ───────────────────────────────────────────────────────────────

-- Raw scraped posts
CREATE TABLE IF NOT EXISTS posts (
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
    metadata     JSONB DEFAULT '{}'
);

-- Demographic tags (one post can have multiple inferred tags)
CREATE TABLE IF NOT EXISTS demographic_tags (
    id                   BIGSERIAL  PRIMARY KEY,
    post_id              BIGINT     NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    demographic_value_id SMALLINT   NOT NULL REFERENCES demographic_values(id),
    confidence           FLOAT      NOT NULL,
    method               VARCHAR(30) NOT NULL,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

-- Embeddings for similarity search
CREATE TABLE IF NOT EXISTS post_embeddings (
    id       BIGSERIAL PRIMARY KEY,
    post_id  BIGINT   NOT NULL REFERENCES posts(id) ON DELETE CASCADE UNIQUE,
    model_id SMALLINT NOT NULL REFERENCES embedding_models(id),
    embedding vector(384) NOT NULL      -- dimension must match embedding_models.dimensions
);

-- Sector classification
CREATE TABLE IF NOT EXISTS post_sectors (
    id          BIGSERIAL  PRIMARY KEY,
    post_id     BIGINT     NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    sector_id   SMALLINT   NOT NULL REFERENCES sectors(id),
    confidence  FLOAT      NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Indexes ───────────────────────────────────────────────────────────────────

CREATE INDEX        IF NOT EXISTS idx_posts_subreddit ON posts(subreddit);
CREATE INDEX        IF NOT EXISTS idx_posts_created   ON posts(created_utc);
CREATE INDEX        IF NOT EXISTS idx_tags_post        ON demographic_tags(post_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tags_unique      ON demographic_tags(post_id, demographic_value_id, method);
CREATE INDEX        IF NOT EXISTS idx_tags_value       ON demographic_tags(demographic_value_id);
CREATE INDEX        IF NOT EXISTS idx_embeddings_post  ON post_embeddings(post_id);
CREATE INDEX        IF NOT EXISTS idx_sectors_post     ON post_sectors(post_id);

-- HNSW vector index: build AFTER bulk embedding insert, not before
-- CREATE INDEX idx_embeddings_vector ON post_embeddings USING hnsw (embedding vector_cosine_ops);

-- ── Focus group sessions (Stage 3) ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS focus_group_sessions (
    id                 UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
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
    session_id      UUID        NOT NULL REFERENCES focus_group_sessions(id) ON DELETE CASCADE,
    post_id         BIGINT      NOT NULL REFERENCES posts(id),
    persona_summary TEXT        NOT NULL,
    system_prompt   TEXT        NOT NULL,
    response_text   TEXT        NOT NULL,
    model           VARCHAR(100) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_responses_session ON focus_group_responses(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status   ON focus_group_sessions(status);
