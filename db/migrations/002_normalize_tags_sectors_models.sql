-- Migration 002: normalize demographic_tags, post_sectors, post_embeddings
--
-- Creates lookup tables and migrates existing data to FK references.
-- Safe to run in a transaction — rolls back entirely on any mapping failure.
--
-- Run AFTER stopping any active ingestion jobs.
-- Run: psql $DB_URL -f db/migrations/002_normalize_tags_sectors_models.sql

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

-- ── 2. Seed data ──────────────────────────────────────────────────────────────

INSERT INTO demographic_dimensions (name) VALUES
    ('age_group'),
    ('gender'),
    ('parent_status'),
    ('income_bracket');

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

-- ── 3. Migrate demographic_tags ───────────────────────────────────────────────

ALTER TABLE demographic_tags
    ADD COLUMN demographic_value_id SMALLINT REFERENCES demographic_values(id);

UPDATE demographic_tags dt
SET demographic_value_id = dv.id
FROM demographic_values dv
JOIN demographic_dimensions dd ON dd.id = dv.dimension_id
WHERE dd.name = dt.dimension AND dv.value = dt.value;

-- Abort if any existing rows used a dimension/value not in the seed data
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM demographic_tags WHERE demographic_value_id IS NULL) THEN
        RAISE EXCEPTION
            'demographic_tags has % rows with unmapped dimension/value — add them to the seed data above and retry',
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

-- ── 4. Migrate post_sectors ───────────────────────────────────────────────────

ALTER TABLE post_sectors
    ADD COLUMN sector_id SMALLINT REFERENCES sectors(id);

UPDATE post_sectors ps
SET sector_id = s.id
FROM sectors s
WHERE s.name = ps.sector;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM post_sectors WHERE sector_id IS NULL) THEN
        RAISE EXCEPTION
            'post_sectors has % rows with unmapped sector — add them to sectors seed and retry',
            (SELECT COUNT(*) FROM post_sectors WHERE sector_id IS NULL);
    END IF;
END $$;

ALTER TABLE post_sectors
    ALTER COLUMN sector_id SET NOT NULL,
    DROP COLUMN sector;

-- ── 5. Migrate post_embeddings ────────────────────────────────────────────────

ALTER TABLE post_embeddings
    ADD COLUMN model_id SMALLINT REFERENCES embedding_models(id);

UPDATE post_embeddings pe
SET model_id = em.id
FROM embedding_models em
WHERE em.name = pe.model;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM post_embeddings WHERE model_id IS NULL) THEN
        RAISE EXCEPTION
            'post_embeddings has % rows with unmapped model — add them to embedding_models seed and retry',
            (SELECT COUNT(*) FROM post_embeddings WHERE model_id IS NULL);
    END IF;
END $$;

ALTER TABLE post_embeddings
    ALTER COLUMN model_id SET NOT NULL,
    DROP COLUMN model;

COMMIT;
