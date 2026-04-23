import re
import os
import logging
import unicodedata
from src.services.ChatService.IChatService import IChatService
from src.repository.vector_db import retrieve_relevant_documents
from src.services.TtsService import ElevenLabsTtsService
from src.services.CacheService import CacheService

logger = logging.getLogger(__name__)

# Gemini free-tier models in priority order (falls back on rate limit)
GEMINI_MODELS = [
    "gemini-2.5-flash-lite",  # fastest, lowest latency
    "gemini-2.5-flash",       # fallback
]

# Restricted keywords blocklist
RESTRICTED_KEYWORDS = {
    "revenue", "salary", "password", "confidential",
    "secret", "salaries", "credentials", "passwords",
}

# Tamil script Unicode range
TAMIL_CHAR_RANGES = [(0x0B80, 0x0C00)]

# Common Tamil words in Latin script (Tanglish)
TAMIL_WORDS_LATIN = {
    'enakku', 'ennakku', 'neenga', 'ninga', 'pathi', 'sollu', 'solluga',
    'enna', 'adi', 'illai', 'irukku', 'pannu', 'oru', 'ava', 'avar',
    'paathu', 'vandhu', 'seiyanum', 'sollrenu', 'neeya', 'avarukkana',
    'pannuvai', 'pannuvan', 'pannungal', 'pannanum', 'pannirukke',
    'ungaluku', 'unkalai', 'neerai', 'yeruthu', 'yeta', 'yeppadi',
    'da', 'di', 'ra', 'ri', 'le', 'li', 'dei', 'vai', 'vaai',
    'naan', 'neeya', 'avan', 'avaL', 'avangal', 'naangal', 'ungal',
    'idhu', 'athu', 'ithu', 'indha', 'anhu', 'athille',
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


def detect_language(text: str) -> str:
    return "tamil" if is_tamil_text(text) else "english"


def clean_context(text: str) -> str:
    """Remove zero-width and control characters, then normalise whitespace."""
    if not text:
        return text
    text = "".join(c for c in text if not unicodedata.category(c).startswith("C"))
    return re.sub(r"\s+", " ", text).strip()


def clean_text_for_tts(text: str) -> str:
    """Strip markdown / emojis for clean TTS output."""
    if not text:
        return text
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"[*_]", "", text)
    text = re.sub(r"\[(.+?)\]", r"\1", text)
    text = re.sub(r"\(https?://[^\)]+\)", "", text)
    text = re.sub(r"^[\s\-*•]+", "", text, flags=re.MULTILINE)
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

TANGLISH_PROMPT_TEMPLATE = """
நீ ஒரு document-based Q&A chatbot. Context-ல் கொடுக்கப்பட்ட தகவல்களை மட்டுமே பயன்படுத்தி பதிலளிக்க வேண்டும்.

**CRITICAL RULES - இவை முக்கியம்:**
1. ONLY Context-ல் கொடுக்கப்பட்ட தகவல்களை மட்டுமே பயன்படுத்தவும்.
2. Context-ல் தகவல் இல்லாவிட்டால்: "இந்த தகவல் கிடைக்கவில்லை."
3. பதிலை 2-3 வாக்கியங்கள் மட்டுமே கொடுக்கவும்.
4. தமிழ் மொழியில் மட்டுமே பதிலளிக்கவும்.
5. Context-ல் இருக்கும் ஆங்கில வார்த்தைகளை அப்படியே வைக்கவும்.

Context:
{context}

Question: {question}

**ANSWER (Context-ல் இருக்கிற தகவல்களை மட்டுமே பயன்படுத்தி, தமிழ்ல், 2-3 வாக்கியங்கள்):**"""

ENGLISH_PROMPT_TEMPLATE = """
You are a document-based Q&A chatbot. You ONLY answer based on the Context provided below.

**CRITICAL RULES - MUST FOLLOW:**
1. ONLY use information from the Context below - NEVER use outside knowledge.
2. If the Context does NOT contain the answer, say: "The requested information is not available."
3. Answer in 2-3 sentences MAXIMUM.
4. NO markdown, NO special formatting, NO emojis - plain text ONLY.
5. Be truthful to the Context - do NOT hallucinate or invent information.

Context:
{context}

Question: {question}

ANSWER (ONLY from Context above, 2-3 sentences max, plain text):**"""


# ---------------------------------------------------------------------------
# Service implementation
# ---------------------------------------------------------------------------

class ChatServiceImpl(IChatService):
    """
    RAG pipeline: pgvector similarity search → Gemini answer.
    Supports Tamil + English. Falls back across Gemini models on rate-limit.
    No langchain dependency — uses google-generativeai directly.
    """

    def __init__(self):
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set.")
        self.google_api_key = google_api_key

        # Configure Gemini once at startup
        import google.generativeai as genai
        genai.configure(api_key=google_api_key)

        # Pre-build GenerativeModel instances for each fallback model
        self._models: list[tuple[str, object]] = []
        for model_name in GEMINI_MODELS:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config=genai.types.GenerationConfig(temperature=0),
                )
                self._models.append((model_name, model))
                logger.info(f"Initialized Gemini model: {model_name}")
            except Exception as e:
                logger.warning(f"Could not initialise Gemini model {model_name}: {e}")

        if not self._models:
            raise ValueError("No Gemini models could be initialised. Check your GOOGLE_API_KEY.")

        logger.info(f"Gemini fallback chain ready: {[m for m, _ in self._models]}")

        # TTS
        el_key = os.getenv("ELEVENLABS_API_KEY")
        el_voice = os.getenv("ELEVENLABS_VOICE_ID")
        if el_key and el_voice:
            self.tts_service = ElevenLabsTtsService(api_key=el_key, voice_id=el_voice)
            logger.info(f"TTS Service initialised with voice ID: {el_voice}")
        else:
            self.tts_service = None
            logger.warning("ElevenLabs credentials not found — TTS disabled")

        self.cache_service = CacheService()

    # ------------------------------------------------------------------

    def _invoke_with_fallback(self, prompt: str) -> str:
        """Call Gemini, auto-falling back on rate-limit errors."""
        last_error = None
        for model_name, model in self._models:
            try:
                response = model.generate_content(prompt)
                logger.info(f"Successfully used Gemini model: {model_name}")
                return response.text
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = any(
                    x in err_str for x in
                    ["429", "quota", "resource exhausted", "rate limit", "too many requests", "limit exceeded"]
                )
                if is_rate_limit:
                    logger.warning(f"Rate limit on {model_name}, trying next model…")
                    last_error = e
                    continue
                logger.error(f"Error from {model_name}: {e}")
                raise
        raise Exception(
            f"All Gemini models rate-limited. Please wait and try again. Last error: {last_error}"
        )

    def _run_tamil_chain(self, question: str) -> str:
        context = clean_context(retrieve_relevant_documents(question, k=7))
        return self._invoke_with_fallback(
            TANGLISH_PROMPT_TEMPLATE.format(context=context, question=question)
        )

    def _run_english_chain(self, question: str) -> str:
        context = clean_context(retrieve_relevant_documents(question, k=7))
        return self._invoke_with_fallback(
            ENGLISH_PROMPT_TEMPLATE.format(context=context, question=question)
        )

    def _is_restricted(self, question: str) -> bool:
        normalized = re.sub(r"[^a-zA-Z\s]", "", question).lower()
        return bool(set(normalized.split()).intersection(RESTRICTED_KEYWORDS))

    def _detect_enrollment_query(self, text: str) -> bool:
        if not text or not text.strip():
            return False
        enrollment_en = [
            "join", "enroll", "register", "sign up", "how to join",
            "subscribe", "admission", "application", "apply",
            "i want to", "i would like to", "can i join", "how do i join",
            "want to enroll", "want to register", "want to participate",
        ]
        enrollment_ta = [
            "சேர", "சேர்", "சேரண", "சேரணும்", "சேர்ந்து", "சேர்த்து", "சேர்க்க", "சேர்க",
            "பங்கு", "மாணவ", "பதிவு", "வேண்டும்", "எப்படி", "விவரம்", "விபரம்",
            "விண்ணப்பம்", "கட்ணம்", "கோரி", "செலவு", "பணம்",
            "ஜாயின்", "எனரோல்", "ரெஜிஸ்டர்", "கோர்ஸ்", "பாடம்", "கல்வி",
        ]
        text_lower = text.lower()
        for kw in enrollment_en:
            if kw in text_lower:
                logger.info(f"📝 Enrollment detected (EN): '{kw}' in '{text[:50]}'")
                return True
        for kw in enrollment_ta:
            if kw in text:
                logger.info(f"📝 Enrollment detected (TA): '{kw}' in '{text[:50]}'")
                return True
        if re.search(r"[\u0B80-\u0BFF]", text):
            critical = ["சேர", "பதிவு", "சேர்", "சேரணும்", "விண்ணப்பம்",
                        "ஜாயின்", "எனரோல்", "ரெஜிஸ்டர்", "கோர்ஸ்"]
            matched = [kw for kw in critical if kw in text]
            if matched:
                logger.info(f"📝 Enrollment detected (TA pattern): {matched}")
                return True
        return False

    async def ask_question(self, question: str) -> dict:
        # 1. Enrollment check
        is_enrollment = self._detect_enrollment_query(question)
        if is_enrollment:
            logger.info("📝 Enrollment inquiry — will show form AND answer from documents")

        # 2. Keyword blocklist
        if self._is_restricted(question):
            return {"answer": "You do not have the privilege to access this information.",
                    "type": "restricted", "audio_url": None}

        # 3. Language detection
        language = detect_language(question)
        logger.info(f"Detected language: {language}")

        # 4. RAG generation
        answer = (self._run_tamil_chain(question) if language == "tamil"
                  else self._run_english_chain(question))
        logger.info(f"Generated {language} response")

        # 5. Not-found fallback
        not_found_msg = "The requested information is not available."
        not_found_ta  = "இந்த தகவல் கிடைக்கவில்லை."
        is_not_found = (not_found_msg.lower() in answer.lower()) or (not_found_ta in answer)
        if is_not_found and not is_enrollment:
            return {"answer": not_found_msg if language == "english" else not_found_ta,
                    "type": "not_found", "audio_url": None}

        # 6. Clean for TTS
        answer = clean_text_for_tts(answer)

        # 7. TTS
        audio_url = None
        if self.tts_service:
            try:
                audio_url = self.cache_service.get_cached_audio(answer)
                if not audio_url:
                    audio_url = self.tts_service.generate_audio(answer)
                    if audio_url:
                        self.cache_service.cache_audio(answer, audio_url)
                        logger.info("Generated and cached TTS audio")
                    else:
                        logger.warning("Failed to generate TTS audio")
                else:
                    logger.info("Using cached TTS audio")
            except Exception as e:
                logger.error(f"TTS error: {e}")

        # 8. Return
        return {
            "answer": answer.strip(),
            "type": "enrollment_form" if is_enrollment else "normal",
            "audio_url": audio_url,
            "language": language,
        }
