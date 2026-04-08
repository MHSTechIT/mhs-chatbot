import os
import base64
import requests
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from src.database import get_db
from src.repository.enrollment_repo import EnrollmentRepository
# Heavy service imports are deferred inside factory functions to keep startup fast

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request validation and response schemas
class AskRequest(BaseModel):
    question: str = Field(..., description="The user's question.", examples=["What are the office hours?"])
    mode: str = Field(
        default="health",
        description="Assistant mode: 'health' = MHS policy-grounded lifestyle/metabolic assistant (Gemini + optional admin facts); 'web' = Gemini web search.",
    )
    language: str = Field(default="en", description="Response language: 'en' for English, 'ta' for Tamil, 'tanglish' for Tanglish (Tamil script + English mix)")

class AskResponse(BaseModel):
    answer: str = Field(..., description="Assistant reply: Tanglish (Tamil UI) or simple English (English UI), plain text.")
    type: str = Field(..., description="Response classification: 'normal', 'restricted', or 'not_found'.")
    audio_url: Optional[str] = Field(default=None, description="ElevenLabs TTS audio URL for the response (if available).")
    emotion: Optional[str] = Field(default=None, description="Detected emotion tag for voice (e.g., '🤝 Empathetic', '✨ Encouraging')")
    voice_settings: Optional[dict] = Field(default=None, description="ElevenLabs voice settings with emotion-based parameters")

# Lazily instantiate services as Singletons
web_search_service_instance = None
health_service_instance = None

def get_web_search_service():
    global web_search_service_instance
    if web_search_service_instance is None:
        try:
            from src.services.ChatService.WebSearchChatService import WebSearchChatService
            web_search_service_instance = WebSearchChatService()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Web search init failed: {str(e)}")
    return web_search_service_instance

def get_health_service():
    global health_service_instance
    if health_service_instance is None:
        try:
            from src.services.HealthChatService import HealthChatService
            health_service_instance = HealthChatService()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Health service init failed: {str(e)}")
    return health_service_instance

@router.post("/ask", response_model=AskResponse, summary="Ask the Chatbot a Question")
async def ask_question(request: AskRequest, db: Session = Depends(get_db)):
    """
    Accepts a user question and returns a generated answer with optional TTS hook.
    Modes:
    - 'health' (default): MHS assistant — Gemini follows config/mhs_assistant_rules.md; optional admin-uploaded facts appended when present.
    - 'web': Gemini with web search.
    Other mode values are treated like 'health' for backward compatibility.
    """
    try:
        if not request.question or not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty.")

        logger.info(
            f"Processing question (mode={request.mode}, language={request.language!r}): {request.question[:120]}"
        )

        # Use appropriate service based on mode
        # Default to health service for fast health Q&A about My Health School
        mode = request.mode.lower() if request.mode else "health"

        if mode == "web":
            service = get_web_search_service()
            result = await service.ask_question(request.question)
        else:
            # health, document, or default — policy-grounded MHS assistant (+ optional admin docs)
            service = get_health_service()
            result = await service.ask_question(request.question, req_language=request.language)

        logger.info(f"Service returned answer length: {len(result.get('answer', ''))}")
        logger.info(f"Answer sample (first 150): {result.get('answer', '')[:150]}")
        logger.info(f"Emotion detected: {result.get('emotion')}")

        return AskResponse(
            answer=result["answer"],
            type=result["type"],
            audio_url=result.get("audio_url"),
            emotion=result.get("emotion"),
            voice_settings=result.get("voice_settings")
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        import traceback
        logger.error(f"Error processing question: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


class TTSRequest(BaseModel):
    text: str = Field(..., description="The text to convert to speech.")
    voice_settings: Optional[dict] = Field(default=None, description="Optional emotional voice settings (stability, similarity_boost, style, use_speaker_boost)")
    emotion_label: Optional[str] = Field(default=None, description="Emotional tone label for logging")
    language: Optional[str] = Field(default=None, description="Response language: 'ta' for Tamil - converts numbers to Tamil words for clearer pronunciation")

@router.post("/tts/generate", summary="Generate TTS Audio for Text with Emotional Voice Settings")
async def generate_tts_audio(request: TTSRequest):
    """
    Generate TTS audio directly from text with emotion-aware voice settings.
    Returns streaming audio that can be played in the browser.
    Accepts text in JSON body to avoid URL length limitations.

    Supports emotion-based voice parameters:
    - 🤝 Empathetic: Lower stability for warmth
    - ✨ Encouraging: Higher similarity for confidence
    - 📊 Informative: Balanced settings for clarity
    - 💬 Conversational: Natural flow settings
    - 👨‍⚕️ Professional: High stability for authority
    """
    try:
        text = request.text
        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty.")

        # For Tamil, convert numbers to English words so TTS pronounces them clearly
        lang = (request.language or "").lower()
        has_tamil = any("\u0B80" <= c <= "\u0BFF" for c in text)
        if lang == "ta" or (not lang and has_tamil):
            try:
                from src.utils.tts_numbers import numbers_to_english_words
                text = numbers_to_english_words(text)
                logger.info(f"TTS: Converted numbers to English words for clear pronunciation in Tamil speech")
            except Exception as e:
                logger.warning(f"TTS number conversion failed, using original text: {e}")

        elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        elevenlabs_voice_id = os.getenv("ELEVENLABS_VOICE_ID")

        if not elevenlabs_api_key or not elevenlabs_voice_id:
            raise HTTPException(status_code=500, detail="ElevenLabs credentials not configured")

        # Call ElevenLabs streaming API
        streaming_url = f"https://api.elevenlabs.io/v1/text-to-speech/{elevenlabs_voice_id}/stream"

        # Use provided voice settings or defaults
        if request.voice_settings:
            voice_settings = {
                "stability": request.voice_settings.get("stability", 0.35),
                "similarity_boost": request.voice_settings.get("similarity_boost", 0.82),
                "style": request.voice_settings.get("style", 0.45),
                "use_speaker_boost": request.voice_settings.get("use_speaker_boost", True),
            }
            emotion_label = request.emotion_label or "Custom"
        else:
            # Natural Tamil-optimised defaults: mid-range stability for clear, steady voice;
            # low style prevents theatrical over-exaggeration
            voice_settings = {
                "stability": 0.55,
                "similarity_boost": 0.80,
                "style": 0.15,
                "use_speaker_boost": True,
            }
            emotion_label = "Default"

        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": voice_settings,
        }

        headers = {
            "xi-api-key": elevenlabs_api_key,
            "Content-Type": "application/json",
        }

        logger.info(f"📢 TTS generation ({emotion_label}): Stability={voice_settings['stability']}, Style={voice_settings['style']}, Similarity={voice_settings['similarity_boost']}")

        response = requests.post(
            streaming_url,
            json=payload,
            headers=headers,
            timeout=30,
            stream=True,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"ElevenLabs error: {response.text}"
            )

        logger.info(f"✅ TTS audio generated successfully with {emotion_label} voice settings")

        # Stream the audio directly to the client
        return StreamingResponse(
            response.iter_content(chunk_size=1024),
            media_type="audio/mpeg"
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"TTS generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# /transcribe  –  Audio → Text using Gemini multimodal transcription
# Replaces unreliable Chrome Web Speech API with server-side AI transcription.
# ─────────────────────────────────────────────────────────────────────────────

class TranscribeRequest(BaseModel):
    audio: str = Field(..., description="Base64-encoded audio data from MediaRecorder.")
    mime_type: str = Field(default="audio/webm", description="MIME type of the audio (e.g. audio/webm;codecs=opus).")


@router.post("/transcribe", summary="Transcribe Audio Using Gemini AI")
async def transcribe_audio(request: TranscribeRequest):
    """
    Accepts base64-encoded audio recorded by the browser's MediaRecorder API,
    sends it to Gemini's multimodal model for transcription, and returns the
    spoken text. Works with Tamil, English, and Tanglish (mixed) speech.
    """
    try:
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured in backend.")

        # Decode base64 → raw audio bytes
        try:
            audio_bytes = base64.b64decode(request.audio)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 audio data.")

        if len(audio_bytes) < 500:
            raise HTTPException(status_code=400, detail="Audio too short to transcribe.")

        logger.info(f"Transcribing audio: {len(audio_bytes)} bytes, mime={request.mime_type}")

        # Use google-generativeai SDK (already installed for ChatService)
        import google.generativeai as genai
        genai.configure(api_key=google_api_key)

        model = genai.GenerativeModel("gemini-2.5-flash-lite")

        # Build multimodal prompt: audio part + instruction
        audio_part = {
            "mime_type": request.mime_type.split(";")[0],  # strip codec suffix for compatibility
            "data": audio_bytes
        }
        prompt = (
            "Transcribe the spoken words in this audio exactly as heard. "
            "The speaker may speak in Tamil, English, or a mix of both (Tanglish). "
            "Return ONLY the spoken words — no explanations, no punctuation changes, no translations. "
            "If the audio is silent or inaudible, return exactly: [SILENCE]"
        )

        response = model.generate_content([audio_part, prompt])
        transcribed = response.text.strip() if response.text else ""

        logger.info(f"Transcription result: '{transcribed[:100]}'")

        # Return empty text for silence so frontend can handle gracefully
        if transcribed == "[SILENCE]" or not transcribed:
            return {"text": ""}

        return {"text": transcribed}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# /submit-enrollment  –  Store enrollment form submissions in database
# ─────────────────────────────────────────────────────────────────────────────

class EnrollmentSubmissionRequest(BaseModel):
    name: str = Field(..., description="User's full name")
    phone: str = Field(..., description="User's phone number")
    age: int = Field(..., description="User's age")
    location: str = Field(..., description="User's location/city")
    sugar_level: Optional[str] = Field(None, description="User's blood sugar level (optional)")

@router.post("/submit-enrollment", summary="Submit Enrollment Form")
async def submit_enrollment(request: EnrollmentSubmissionRequest, db: Session = Depends(get_db)):
    """
    Receives enrollment form submissions and stores them in the database.
    Required fields: name, phone, age, location
    Optional fields: sugar_level
    """
    try:
        # Validate required fields
        if not request.name or not request.name.strip():
            raise HTTPException(status_code=400, detail="Name is required")

        if not request.phone or not request.phone.strip():
            raise HTTPException(status_code=400, detail="Phone number is required")

        if not request.age or request.age <= 0:
            raise HTTPException(status_code=400, detail="Age is required and must be a positive number")

        if not request.location or not request.location.strip():
            raise HTTPException(status_code=400, detail="Location is required")

        logger.info(f"Processing enrollment: {request.name} ({request.phone}), Age: {request.age}, Location: {request.location}")

        # Save to database
        enrollment = EnrollmentRepository.create_enrollment(
            db=db,
            name=request.name,
            phone=request.phone,
            age=request.age,
            location=request.location,
            sugar_level=request.sugar_level
        )

        logger.info(f"✅ Enrollment {enrollment.id} stored successfully")

        return {
            "success": True,
            "message": "Enrollment submitted successfully",
            "enrollment_id": enrollment.id
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Enrollment submission error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Enrollment submission failed: {str(e)}")


# Alias endpoint for enrollment endpoint used by frontend
@router.post("/enrollment", summary="Submit Enrollment Form")
async def submit_enrollment_alias(request: EnrollmentSubmissionRequest, db: Session = Depends(get_db)):
    """
    Alias for /submit-enrollment endpoint.
    Receives enrollment form submissions and stores them in the database.
    Required fields: name, phone
    Optional fields: email, sugar_level
    """
    return await submit_enrollment(request, db)
