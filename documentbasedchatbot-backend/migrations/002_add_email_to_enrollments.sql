-- Add email column to enrollments table
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS email VARCHAR(255);

-- Add index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_enrollments_email ON enrollments(email);
