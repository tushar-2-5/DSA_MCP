-- Migration 0001_init.sql
-- Initial schema for Recall MCP server

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    display_name TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS problems (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    statement TEXT NOT NULL,
    difficulty TEXT CHECK (difficulty IN ('easy', 'medium', 'hard')),
    topic_id UUID REFERENCES topics(id) ON DELETE SET NULL,
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    problem_id UUID REFERENCES problems(id) ON DELETE CASCADE,
    code_s3_key TEXT,
    outcome TEXT CHECK (outcome IN ('pass', 'fail', 'partial')),
    complexity_achieved TEXT,
    time_taken_seconds INT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_attempts_user_created ON attempts (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS mastery (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    mastery_score FLOAT DEFAULT 0.0 CHECK (mastery_score >= 0.0 AND mastery_score <= 1.0),
    last_practiced_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, topic_id)
);

CREATE TABLE IF NOT EXISTS mistakes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    attempt_id UUID REFERENCES attempts(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type TEXT CHECK (source_type IN ('problem', 'code_submission', 'mistake')),
    source_id UUID,
    embedding VECTOR(1024),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw ON embeddings USING HNSW (embedding vector_cosine_ops);
