import os
import re
import logging
from src.services.TtsService import ElevenLabsTtsService

logger = logging.getLogger(__name__)

# Gemini model — fastest / lowest latency
GEMINI_MODEL = "gemini-2.5-flash-lite"

# Tamil script Unicode range
TAMIL_CHAR_RANGES = [(0x0B80, 0x0C00)]

# Common Tamil words in Latin script (Tanglish)
TAMIL_WORDS_LATIN = {
    'enakku', 'ennakku', 'neenga', 'ninga', 'pathi', 'sollu', 'enna',
    'adi', 'illai', 'irukku', 'pannu', 'oru', 'ava', 'avar', 'paathu',
    'vandhu', 'seiyanum', 'sollrenu', 'neeya', 'avarukkana', 'pannuvai',
    'pannuvan', 'pannungal', 'pannanum', 'pannirukke', 'ungaluku', 'unkalai',
}


def is_tamil_text(text: str) -> bool:
    """Return True if text contains Tamil Unicode chars or Tanglish words."""
    for char in text:
        cp = ord(char)
        for start, end in TAMIL_CHAR_RANGES:
            if start <= cp < end:
                return True
    words = re.findall(r'\b[a-z]+\b', text.lower())
    return sum(1 for w in words if w in TAMIL_WORDS_LATIN) >= 1


# Prompt templates
ENGLISH_PROMPT = """You are a helpful AI assistant answering questions.

Answer in MAXIMUM 2 short paragraphs. Be concise - give only the asked information.
Plain text only, NO markdown, NO emojis.
If you don't know, say: "I couldn't find information about that."

Question: {question}

Answer:"""

TAMIL_PROMPT = """நீ ஒரு உதவிகரமான AI உதவி.

அதிகபட்சம் 2 சிறிய பத்திகள் மட்டுமே விடை கொடுக்க வேண்டும். சுருக்கமாக - கேட்ட தகவலை மட்டும் சொல்லுங்கள்.
சுத்தமான தமிழ் மட்டுமே. எந்த markdown, emojis இல்லை.
தகவல் இல்லாவிட்டால்: "இந்த விஷயத்தைப் பற்றி தகவல் கிடைக்கவில்லை."

கேள்வி: {question}

விடை:"""


class WebSearchChatService:
    """
    Web-based Q&A service using Gemini (no langchain dependency).
    Generates answers and optionally converts them to speech via ElevenLabs.
    """

    def __init__(self):
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set.")
        self.google_api_key = google_api_key

        import google.generativeai as genai
        genai.configure(api_key=google_api_key)
        self._model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            generation_config=genai.types.GenerationConfig(temperature=0.7),
        )
        logger.info(f"WebSearchChatService initialised with model: {GEMINI_MODEL}")

        el_key = os.getenv("ELEVENLABS_API_KEY")
        el_voice = os.getenv("ELEVENLABS_VOICE_ID")
        if el_key and el_voice:
            self.tts_service = ElevenLabsTtsService(api_key=el_key, voice_id=el_voice)
            logger.info(f"TTS Service initialised with voice ID: {el_voice}")
        else:
            self.tts_service = None
            logger.warning("ElevenLabs credentials not found — TTS disabled")

    async def ask_question(self, question: str) -> dict:
        try:
            if not question or not question.strip():
                return {"answer": "Please ask a valid question.", "type": "error", "audio_url": None}

            logger.info(f"Web search question: {question}")

            is_tamil = is_tamil_text(question)
            prompt_tmpl = TAMIL_PROMPT if is_tamil else ENGLISH_PROMPT
            logger.info(f"Detected language: {'Tamil/Tanglish' if is_tamil else 'English'}")

            prompt = prompt_tmpl.format(question=question)
            response = self._model.generate_content(prompt)
            answer = (response.text or "").strip()

            if not answer:
                answer = (
                    "உனது கேள்விக்கு பதிலை உருவாக்க முடியவில்லை."
                    if is_tamil else
                    "I could not generate an answer to your question."
                )

            logger.info(f"Generated answer length: {len(answer)}")

            # TTS
            audio_url = None
            if self.tts_service:
                try:
                    audio_url = self.tts_service.generate_audio(answer.strip())
                    logger.info("TTS audio generated successfully")
                except Exception as e:
                    logger.warning(f"TTS generation failed: {e}")

            return {"answer": answer, "type": "normal", "audio_url": audio_url}

        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {"answer": f"An error occurred: {e}", "type": "error", "audio_url": None}
