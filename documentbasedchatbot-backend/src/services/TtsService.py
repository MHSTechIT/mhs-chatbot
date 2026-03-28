"""
ElevenLabs Text-to-Speech Service
Integrates ElevenLabs API for generating audio from Tanglish text.
"""

import os
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ElevenLabsTtsService:
    """
    Service for generating TTS audio using ElevenLabs API.
    """

    def __init__(self, api_key: str, voice_id: str):
        """
        Initialize ElevenLabs TTS Service.

        Args:
            api_key: ElevenLabs API key
            voice_id: Voice ID to use (e.g., Ahq9IAlmr15JKZ2Fa5ov)
        """
        self.api_key = api_key
        self.voice_id = voice_id
        self.api_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def generate_audio(self, text: str) -> Optional[str]:
        """
        Generate audio from text using ElevenLabs API.
        Returns a backend endpoint URL that the frontend can call to get audio.

        Args:
            text: The Tanglish text to convert to speech

        Returns:
            Backend TTS endpoint URL if successful, None if failed
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to TTS service")
            return None

        try:
            # Return the backend proxy endpoint URL directly
            # The frontend will call this URL with POST and JSON body containing the full text
            # The backend will handle authentication with ElevenLabs
            logger.info(f"TTS service ready for text-to-speech conversion with voice_id: {self.voice_id}")
            return "http://127.0.0.1:8001/tts/generate"

        except Exception as e:
            logger.error(f"Unexpected error in TTS generation: {str(e)}")
            return None

    def add_emotional_tags(self, text: str) -> str:
        """
        Add minimal emotional tags for natural-sounding speech.
        Optimized for speed - only adds essential tags.

        Args:
            text: Plain text to enhance with emotional tags

        Returns:
            Text with emotional pronunciation marks
        """
        # Minimal tags for speed
        text_with_tags = text

        # Add pauses only at major breaks for natural pacing
        text_with_tags = text_with_tags.replace(". ", ". <break time=\"300ms\"/>")

        return text_with_tags

    def generate_audio_base64(self, text: str) -> Optional[str]:
        """
        Generate audio and return as base64 (for embedding in responses).
        Uses enhanced voice settings for natural, emotional speech.

        Args:
            text: The text to convert to speech

        Returns:
            Base64-encoded audio data if successful, None if failed
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to TTS service")
            return None

        try:
            # Add emotional tags for natural speech
            enhanced_text = self.add_emotional_tags(text)

            # Optimized voice settings for speed and quality
            payload = {
                "text": enhanced_text,
                "model_id": "eleven_turbo_v2_5",  # Latest model for natural speech
                "voice_settings": {
                    "stability": 0.70,           # Slightly higher for stability
                    "similarity_boost": 0.75,   # Balanced for speed
                },
            }

            logger.info(f"Calling ElevenLabs API with voice_id: {self.voice_id}")
            logger.info(f"Enhanced text with emotional tags: {enhanced_text[:100]}...")

            response = requests.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                timeout=30,
            )

            if response.status_code == 200:
                import base64
                audio_base64 = base64.b64encode(response.content).decode("utf-8")
                logger.info("Successfully generated base64 audio from ElevenLabs with emotional tags")
                return audio_base64
            else:
                logger.error(
                    f"ElevenLabs API error: {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error generating base64 audio: {str(e)}")
            return None
