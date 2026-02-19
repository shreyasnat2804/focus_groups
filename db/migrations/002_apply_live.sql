-- One-time apply script for the existing focusgroups DB.
-- Equivalent to 002_normalize_tags_sectors_models.sql but handles the fact
-- that post_embeddings does not yet exist in the live DB (creates it fresh).
--
-- Safe to run in a transaction — rolls back on any failure.
-- Run: psql $DB_URL -f db/migrations/002_apply_live.sql

BEGIN;

-- ── 1. Lookup tables ──────────────────────────────────────────────────────────

CREATE TABLE demographic_dimensions (
    id   SMALLSERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE demographic_values (
    id           SMALLSERIAL PRIMARY KEY,
    dimension_id SMALLINT    NOT NULL REFERENCES demographic_dimensions(id),
    value        VARCHAR(100) NOT NULL,
    UNIQUE (dimension_id, value)
);

CREATE TABLE sectors (
    id   SMALLSERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE embedding_models (
    id         SMALLSERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL UNIQUE,
    dimensions SMALLINT     NOT NULL
);

-- ── 2. Seed ───────────────────────────────────────────────────────────────────

INSERT INTO demographic_dimensions (name) VALUES
    ('age_group'), ('gender'), ('parent_status'), ('income_bracket');

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
JOIN demographic_dimensions dd ON dd.name = v.dimension;

INSERT INTO sectors (name) VALUES ('tech'), ('financial'), ('political');

INSERT INTO embedding_models (name, dimensions) VALUES ('all-MiniLM-L6-v2', 384);

-- ── 3. Migrate demographic_tags (13,670 rows) ─────────────────────────────────

ALTER TABLE demographic_tags
    ADD COLUMN demographic_value_id SMALLINT REFERENCES demographic_values(id);

UPDATE demographic_tags dt
SET demographic_value_id = dv.id
FROM demographic_values dv
JOIN demographic_dimensions dd ON dd.id = dv.dimension_id
WHERE dd.name = dt.dimension AND dv.value = dt.value;

-- Abort if any rows couldn't be mapped
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM demographic_tags WHERE demographic_value_id IS NULL) THEN
        RAISE EXCEPTION
            'demographic_tags has % unmapped rows — check dimension/value against seed data',
            (SELECT COUNT(*) FROM demographic_tags WHERE demographic_value_id IS NULL);
    END IF;
END $$;

ALTER TABLE demographic_tags
    ALTER COLUMN demographic_value_id SET NOT NULL,
    DROP COLUMN dimension,
    DROP COLUMN value;

DROP INDEX IF EXISTS idx_tags_dimension_value;
DROP INDEX IF EXISTS idx_tags_unique;
CREATE UNIQUE INDEX idx_tags_unique ON demographic_tags(post_id, demographic_value_id, method);
CREATE        INDEX idx_tags_value  ON demographic_tags(demographic_value_id);

-- ── 4. Migrate post_sectors (0 rows — schema change only) ─────────────────────

ALTER TABLE post_sectors
    ADD COLUMN sector_id SMALLINT REFERENCES sectors(id);

-- no rows to update, but run the same safety pattern for consistency
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM post_sectors WHERE sector_id IS NULL) THEN
        RAISE EXCEPTION
            'post_sectors has % unmapped rows',
            (SELECT COUNT(*) FROM post_sectors WHERE sector_id IS NULL);
    END IF;
END $$;

ALTER TABLE post_sectors
    ALTER COLUMN sector_id SET NOT NULL,
    DROP COLUMN sector;

-- ── 5. Create post_embeddings fresh (did not exist in live DB) ────────────────

CREATE TABLE post_embeddings (
    id       BIGSERIAL PRIMARY KEY,
    post_id  BIGINT   NOT NULL REFERENCES posts(id) ON DELETE CASCADE UNIQUE,
    model_id SMALLINT NOT NULL REFERENCES embedding_models(id),
    embedding vector(384) NOT NULL
);

CREATE INDEX idx_embeddings_post ON post_embeddings(post_id);

-- HNSW vector index: build AFTER bulk embedding insert, not before
-- CREATE INDEX idx_embeddings_vector ON post_embeddings USING hnsw (embedding vector_cosine_ops);

COMMIT;
