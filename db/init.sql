CREATE EXTENSION IF NOT EXISTS vector;

-- Raw scraped posts
CREATE TABLE IF NOT EXISTS posts (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(20) NOT NULL DEFAULT 'reddit',
    source_id VARCHAR(100) UNIQUE NOT NULL,
    subreddit VARCHAR(100),
    author VARCHAR(100),
    title TEXT,
    text TEXT NOT NULL,
    score INT,
    num_comments INT,
    created_utc TIMESTAMPTZ NOT NULL,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Demographic tags (one post can have multiple inferred tags)
CREATE TABLE IF NOT EXISTS demographic_tags (
    id BIGSERIAL PRIMARY KEY,
    post_id BIGINT REFERENCES posts(id) ON DELETE CASCADE,
    dimension VARCHAR(50) NOT NULL,
    value VARCHAR(100) NOT NULL,
    confidence FLOAT NOT NULL,
    method VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Embeddings for similarity search
CREATE TABLE IF NOT EXISTS post_embeddings (
    id BIGSERIAL PRIMARY KEY,
    post_id BIGINT REFERENCES posts(id) ON DELETE CASCADE UNIQUE,
    model VARCHAR(100) NOT NULL,
    embedding vector(384) NOT NULL
);

-- Sector classification
CREATE TABLE IF NOT EXISTS post_sectors (
    id BIGSERIAL PRIMARY KEY,
    post_id BIGINT REFERENCES posts(id) ON DELETE CASCADE,
    sector VARCHAR(50) NOT NULL,
    confidence FLOAT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_posts_subreddit ON posts(subreddit);
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_utc);
CREATE INDEX IF NOT EXISTS idx_tags_post ON demographic_tags(post_id);
CREATE INDEX IF NOT EXISTS idx_tags_dimension_value ON demographic_tags(dimension, value);
CREATE INDEX IF NOT EXISTS idx_embeddings_post ON post_embeddings(post_id);
CREATE INDEX IF NOT EXISTS idx_sectors_post ON post_sectors(post_id);

-- HNSW vector index: build AFTER bulk embedding insert, not before
-- CREATE INDEX idx_embeddings_vector ON post_embeddings USING hnsw (embedding vector_cosine_ops);
