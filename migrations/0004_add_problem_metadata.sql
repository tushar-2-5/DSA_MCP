-- Add problem metadata columns
ALTER TABLE problems ADD COLUMN IF NOT EXISTS study_priority TEXT;
ALTER TABLE problems ADD COLUMN IF NOT EXISTS tags TEXT[];
ALTER TABLE problems ADD COLUMN IF NOT EXISTS prerequisites TEXT[];
ALTER TABLE problems ADD COLUMN IF NOT EXISTS interview_relevance TEXT;
ALTER TABLE problems ADD COLUMN IF NOT EXISTS master_id INT;
