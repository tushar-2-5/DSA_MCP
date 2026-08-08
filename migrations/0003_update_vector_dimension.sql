-- Migration 0003_update_vector_dimension.sql
-- Update embedding vector dimension from 1024 (Bedrock) to 768 (Gemini text-embedding-004)

DROP INDEX IF EXISTS idx_embeddings_hnsw;

ALTER TABLE embeddings ALTER COLUMN embedding TYPE VECTOR(768);

CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw ON embeddings USING HNSW (embedding vector_cosine_ops);
