-- Migration 0005_add_company_tags.sql
-- Add company_tags and company_count columns to problems table

ALTER TABLE problems ADD COLUMN IF NOT EXISTS company_tags TEXT[] DEFAULT '{}';
ALTER TABLE problems ADD COLUMN IF NOT EXISTS company_count INTEGER DEFAULT 0;
ALTER TABLE problems ADD COLUMN IF NOT EXISTS acceptance_rate FLOAT DEFAULT 0.0;
ALTER TABLE problems ADD COLUMN IF NOT EXISTS leetcode_id INTEGER DEFAULT 0;

-- Indexes for company filtering and sorting
CREATE INDEX IF NOT EXISTS idx_problems_company_count ON problems(company_count DESC);
CREATE INDEX IF NOT EXISTS idx_problems_company_tags ON problems USING GIN(company_tags);

