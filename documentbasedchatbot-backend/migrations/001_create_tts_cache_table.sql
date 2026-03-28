-- Create TTS Cache Table for storing ElevenLabs audio URLs
-- Run this migration in Supabase SQL Editor to set up the table

CREATE TABLE IF NOT EXISTS tts_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text_hash VARCHAR(64) UNIQUE NOT NULL,
    tanglish_text TEXT NOT NULL,
    audio_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hits INT DEFAULT 0
);

-- Create index for fast lookups by text_hash
CREATE INDEX IF NOT EXISTS idx_tts_cache_hash ON tts_cache(text_hash);

-- Create index for sorting by hits (popular cached items)
CREATE INDEX IF NOT EXISTS idx_tts_cache_hits ON tts_cache(hits DESC);

-- Optionally, create a function to delete old cache entries
CREATE OR REPLACE FUNCTION delete_old_cache(days INT DEFAULT 30)
RETURNS INT AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM tts_cache
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * days;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions if needed
-- GRANT SELECT, INSERT ON tts_cache TO authenticated;

COMMIT;
