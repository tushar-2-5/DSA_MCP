-- Migration 0006_add_code_blob.sql
-- Add code_blob, code_language, and storage_backend columns to attempts table

ALTER TABLE attempts 
ADD COLUMN IF NOT EXISTS code_blob TEXT,
ADD COLUMN IF NOT EXISTS code_language VARCHAR(50) DEFAULT 'python',
ADD COLUMN IF NOT EXISTS storage_backend VARCHAR(20) DEFAULT 'cockroachdb';
