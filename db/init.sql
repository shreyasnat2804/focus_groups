CREATE EXTENSION IF NOT EXISTS vector;

-- Raw scraped posts
CREATE TABLE posts (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(20) NOT NULL DEFAULT 'reddit',
    source_id VARCHAR(100) UNIQUE NOT NULL,
    subreddit VARCHAR(100),
    author VARCHAR(100),
    text TEXT NOT NULL,
    score INT,
    created_utc TIMESTAMPTZ NOT NULL,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Demographic tags
CREATE TABLE demographic_tags (
    id BIGSERIAL PRIMARY KEY,
    post_id BIGINT REFERENCES posts(id) ON DELETE CASCADE,
    dimension VARCHAR(50) NOT NULL,
    value VARCHAR(100) NOT NULL,
    confidence FLOAT NOT NULL,
    method VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Embeddings
CREATE TABLE post_embeddings (
    id BIGSERIAL PRIMARY KEY,
    post_id BIGINT REFERENCES posts(id) ON DELETE CASCADE UNIQUE,
    model VARCHAR(100) NOT NULL,
    embedding vector(384) NOT NULL
);

-- Sector classification
CREATE TABLE post_sectors (
    id BIGSERIAL PRIMARY KEY,
    post_id BIGINT REFERENCES posts(id) ON DELETE CASCADE,
    sector VARCHAR(50) NOT NULL,
    confidence FLOAT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_posts_subreddit ON posts(subreddit);
CREATE INDEX idx_posts_created ON posts(created_utc);
CREATE INDEX idx_tags_post ON demographic_tags(post_id);
CREATE INDEX idx_tags_dimension_value ON demographic_tags(dimension, value);
CREATE INDEX idx_embeddings_post ON post_embeddings(post_id);
CREATE INDEX idx_sectors_post ON post_sectors(post_id);
