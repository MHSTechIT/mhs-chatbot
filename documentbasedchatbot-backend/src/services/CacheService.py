"""
Cache Service for storing and retrieving cached TTS audio URLs from Supabase.
"""

import hashlib
import logging
from typing import Optional
from supabase import create_client
import os

logger = logging.getLogger(__name__)


class CacheService:
    """
    Service for caching TTS audio URLs in Supabase PostgreSQL.
    """

    def __init__(self):
        """Initialize Supabase client for caching."""
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")

            if not supabase_url or not supabase_key:
                logger.warning("Supabase credentials not found - caching disabled")
                self.client = None
            else:
                self.client = create_client(supabase_url, supabase_key)
                logger.info("Cache Service initialized with Supabase")
        except Exception as e:
            logger.error(f"Failed to initialize Cache Service: {str(e)}")
            self.client = None

    @staticmethod
    def _hash_text(text: str) -> str:
        """
        Generate SHA256 hash of text for cache lookup.

        Args:
            text: The text to hash

        Returns:
            SHA256 hash string
        """
        return hashlib.sha256(text.encode()).hexdigest()

    def get_cached_audio(self, text: str) -> Optional[str]:
        """
        Retrieve cached audio URL for given text.

        Args:
            text: The Tanglish text to look up

        Returns:
            Cached audio URL if found, None otherwise
        """
        if not self.client:
            logger.debug("Cache Service not initialized, skipping lookup")
            return None

        try:
            text_hash = self._hash_text(text)
            logger.info(f"Looking up cache for hash: {text_hash}")

            response = self.client.table("tts_cache").select("audio_url, id").eq(
                "text_hash", text_hash
            ).execute()

            if response.data and len(response.data) > 0:
                audio_url = response.data[0]["audio_url"]
                cache_id = response.data[0]["id"]

                # Increment hit counter
                try:
                    self.client.table("tts_cache").update(
                        {"hits": (response.data[0].get("hits", 0) + 1)}
                    ).eq("id", cache_id).execute()
                except Exception as e:
                    logger.debug(f"Could not update hit counter: {str(e)}")

                logger.info(f"Cache hit for text hash: {text_hash}")
                return audio_url
            else:
                logger.debug(f"Cache miss for text hash: {text_hash}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None

    def cache_audio(self, text: str, audio_url: str) -> bool:
        """
        Store audio URL in cache.

        Args:
            text: The Tanglish text
            audio_url: The ElevenLabs audio URL

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.debug("Cache Service not initialized, skipping cache write")
            return False

        try:
            text_hash = self._hash_text(text)
            logger.info(f"Caching audio for hash: {text_hash}")

            # Insert or ignore if already exists (upsert-like behavior)
            response = self.client.table("tts_cache").insert(
                {
                    "text_hash": text_hash,
                    "tanglish_text": text,
                    "audio_url": audio_url,
                    "hits": 0,
                }
            ).execute()

            logger.info(f"Successfully cached audio for hash: {text_hash}")
            return True

        except Exception as e:
            # Might fail if record already exists (unique constraint)
            # This is acceptable - the audio is already cached
            logger.debug(f"Cache insert failed (may already exist): {str(e)}")
            return False

    def clear_cache(self, older_than_days: int = 30) -> int:
        """
        Clear old cache entries.

        Args:
            older_than_days: Clear entries older than this many days

        Returns:
            Number of entries deleted
        """
        if not self.client:
            logger.debug("Cache Service not initialized, skipping cache clear")
            return 0

        try:
            # Delete entries older than specified days
            response = self.client.rpc(
                "delete_old_cache",
                {"days": older_than_days}
            ).execute()

            logger.info(f"Cleared cache entries older than {older_than_days} days")
            return len(response.data) if response.data else 0

        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return 0
