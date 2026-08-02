-- Migration 0002_add_problem_url.sql
-- Add nullable url column to problems table

ALTER TABLE problems ADD COLUMN IF NOT EXISTS url TEXT;
