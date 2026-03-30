import re
import os
import logging
import unicodedata
from src.services.ChatService.IChatService import IChatService
from src.repository.vector_db import get_vector_store
from src.services.TtsService import ElevenLabsTtsService
from src.services.CacheService import CacheService
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

# Environment variables are loaded by main.py - no need to load again here
logger = logging.getLogger(__name__)

# Gemini free-tier models in priority order (falls back on rate limit)
# gemini-2.0-flash: 15 RPM - good quality
# gemini-2.0-flash-lite: 30 RPM - more quota, lighter fallback
# gemini-2.5-flash: newer, medium quota
GEMINI_MODELS = [
    "gemini-2.5-flash-lite",  # fastest, lowest latency
    "gemini-2.5-flash",       # fallback
]

# Restricted keywords blocklist
RESTRICTED_KEYWORDS = {"revenue", "salary", "password", "confidential", "secret", "salaries", "credentials", "passwords"}

# Tamil script character ranges
TAMIL_CHAR_RANGES = [
    (0x0B80, 0x0C00),  # Tamil Unicode range
]

# Common Tamil words in Latin script (Tanglish) for detection
TAMIL_WORDS_LATIN = {
    'enakku', 'ennakku', 'neenga', 'ninga', 'pathi', 'sollu', 'solluga',
    'enna', 'adi', 'illai', 'irukku', 'pannu', 'oru', 'ava', 'avar',
    'paathu', 'vandhu', 'seiyanum', 'sollrenu', 'neeya', 'avarukkana',
    'pannuvai', 'pannuvan', 'pannungal', 'pannanum', 'pannirukke',
    'ungaluku', 'unkalai', 'neerai', 'yeruthu', 'yeta', 'yeppadi',
    'da', 'di', 'ra', 'ri', 'le', 'li', 'dei', 'dei', 'vai', 'vaai',
    'naan', 'neeya', 'avan', 'avaL', 'avangal', 'naangal', 'ungal',
    'idhu', 'athu', 'ithu', 'indha', 'athu', 'anhu', 'athille'
}

def is_tamil_text(text: str) -> bool:
    """
    Check if text contains Tamil characters or Tamil words in Latin script (Tanglish).
    Returns True if Tamil text is detected.
    """
    # Check for Tamil Unicode characters
    for char in text:
        code_point = ord(char)
        for start, end in TAMIL_CHAR_RANGES:
            if start <= code_point < end:
                return True

    # Check for Tamil words in Latin script (Tanglish)
    text_lower = text.lower()
    words = re.findall(r'\b[a-z]+\b', text_lower)
    tamil_word_count = sum(1 for word in words if word in TAMIL_WORDS_LATIN)

    # If more than 1 Tamil word found in Latin script, treat as Tamil
    if tamil_word_count >= 1:
        return True

    return False

def detect_language(text: str) -> str:
    """
    Detect if text is in Tamil or English.
    Returns 'tamil' or 'english'
    """
    if is_tamil_text(text):
        return 'tamil'
    return 'english'

def clean_context(text: str) -> str:
    """
    Remove zero-width spaces, control characters, and other invisible unicode characters
    that can break response generation.
    """
    if not text:
        return text
    # Remove control characters (category C) which includes zero-width spaces
    text = ''.join(c for c in text if not unicodedata.category(c).startswith('C'))
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def clean_text_for_tts(text: str) -> str:
    """Remove markdown and emojis from text for clean TTS output."""
    if not text:
        return text

    # Remove markdown headers (# ## ###, etc)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'[*_]', '', text)
    # Remove brackets and links
    text = re.sub(r'\[(.+?)\]', r'\1', text)
    text = re.sub(r'\(https?://[^\)]+\)', '', text)  # URL in parentheses
    # Remove bullet points and list markers
    text = re.sub(r'^[\s\-*•]+', '', text, flags=re.MULTILINE)
    # Remove extra spaces and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# TANGLISH PROMPT - for Tamil questions (Tamil text format, English kept for proper nouns/terms)
TANGLISH_PROMPT_TEMPLATE = """
நீ ஒரு document-based Q&A chatbot. Context-ல் கொடுக்கப்பட்ட தகவல்களை மட்டுமே பயன்படுத்தி பதிலளிக்க வேண்டும்.

**CRITICAL RULES - இவை முக்கியம்:**
1. ONLY Context-ல் கொடுக்கப்பட்ட தகவல்களை மட்டுமே பயன்படுத்தவும். நீ புரிந்து கொண்ட தகவல்கள் அல்ல.
2. Context-ல் தகவல் இல்லாவிட்டால் எப்பொழுதும் சொல்ல வேண்டும்: "இந்த தகவல் கிடைக்கவில்லை."
3. பதிலை 2-3 வாக்கியங்கள் மட்டுமே கொடுக்கவும்.
4. தமிழ் மொழியில் மட்டுமே பதிலளிக்கவும்.
5. Context-ல் இருக்கும் ஆங்கில வார்த்தைகளை அப்படியே வைக்கவும், மொழிமாற்றம் செய்யாதே.

Context:
{context}

Question: {question}

**ANSWER (Context-ல் இருக்கிற தகவல்களை மட்டுமே பயன்படுத்தி, தமிழ்ல், 2-3 வாக்கியங்கள்):**"""

# ENGLISH PROMPT - for English questions
ENGLISH_PROMPT_TEMPLATE = """
You are a document-based Q&A chatbot. You ONLY answer based on the Context provided below.

**CRITICAL RULES - MUST FOLLOW:**
1. ONLY use information from the Context below - NEVER use outside knowledge.
2. If the Context does NOT contain the answer, you MUST say: "The requested information is not available."
3. Answer in 2-3 sentences MAXIMUM.
4. NO markdown, NO special formatting, NO emojis - plain text ONLY.
5. MUST be truthful to the Context - do NOT hallucinate or invent information.

Context:
{context}

Question: {question}

ANSWER (ONLY from Context above, 2-3 sentences max, plain text):**"""

class ChatServiceImpl(IChatService):
    """
    Implementation of the IChatService.
    Handles RAG pipeline initialization, semantic guardrails, and querying the Google Gemini LLM.
    Supports both Tamil and English responses based on input language.
    Automatically falls back to the next Gemini model when rate limits are hit.
    """
    def __init__(self):
        """
        Initializes the vector database connection, Google Gemini LLM models (with fallback),
        TTS service, cache service, and constructs the RAG chain.
        """
        # Initialize Vector Store (may be None if connection fails)
        try:
            self.vector_store = get_vector_store()
            if not self.vector_store:
                raise ValueError("Vector store initialization returned None")
        except Exception as e:
            logger.warning(f"Vector store initialization failed: {str(e)}")
            raise ValueError(f"Cannot initialize ChatServiceImpl without vector database: {str(e)}")

        # Initialize Google Gemini with auto-fallback across free-tier models
        google_api_key = os.getenv("GOOGLE_API_KEY")

        # Debug logging
        logger.info(f"DEBUG: GOOGLE_API_KEY from os.getenv: {'SET' if google_api_key else 'NOT SET'}")
        logger.info(f"DEBUG: GOOGLE_API_KEY in os.environ: {'GOOGLE_API_KEY' in os.environ}")
        logger.info(f"DEBUG: All environ keys starting with GOOGLE: {[k for k in os.environ.keys() if 'GOOGLE' in k]}")

        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set. Please add it to your .env file.")

        self.google_api_key = google_api_key

        # Pre-initialize all Gemini model instances for fast fallback
        self.llm_instances = []
        for model_name in GEMINI_MODELS:
            try:
                llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=0,
                    google_api_key=google_api_key
                )
                self.llm_instances.append((model_name, llm))
                logger.info(f"Initialized Gemini model: {model_name}")
            except Exception as e:
                logger.warning(f"Could not initialize Gemini model {model_name}: {e}")

        if not self.llm_instances:
            raise ValueError("No Gemini models could be initialized. Check your GOOGLE_API_KEY.")

        logger.info(f"Gemini fallback chain ready: {[m for m, _ in self.llm_instances]}")

        # Initialize TTS Service (ElevenLabs)
        elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        elevenlabs_voice_id = os.getenv("ELEVENLABS_VOICE_ID")

        if elevenlabs_api_key and elevenlabs_voice_id:
            self.tts_service = ElevenLabsTtsService(
                api_key=elevenlabs_api_key,
                voice_id=elevenlabs_voice_id
            )
            logger.info(f"TTS Service initialized with voice ID: {elevenlabs_voice_id}")
        else:
            self.tts_service = None
            logger.warning("ElevenLabs credentials not found - TTS disabled")

        # Initialize Cache Service
        self.cache_service = CacheService()

        # Setup Retriever: fetch more chunks so short queries still get relevant context
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 7})

    def _invoke_with_fallback(self, messages: list) -> str:
        """
        Invoke the LLM with automatic fallback to the next model on rate limit errors.
        Tries gemini-2.0-flash → gemini-1.5-flash → gemini-1.5-pro in order.

        Args:
            messages: List of LangChain message objects.

        Returns:
            str: The LLM response text.

        Raises:
            Exception: If all models are exhausted or a non-rate-limit error occurs.
        """
        last_error = None
        for model_name, llm in self.llm_instances:
            try:
                response = llm.invoke(messages)
                logger.info(f"Successfully used Gemini model: {model_name}")
                return response.content
            except Exception as e:
                error_str = str(e).lower()
                is_rate_limit = any(x in error_str for x in [
                    "429", "quota", "resource exhausted", "rate limit",
                    "exhausted", "too many requests", "limit exceeded"
                ])
                if is_rate_limit:
                    logger.warning(f"Rate limit hit for {model_name}, switching to next model...")
                    last_error = e
                    continue
                else:
                    # Non-rate-limit error — re-raise immediately
                    logger.error(f"Error from {model_name}: {e}")
                    raise

        # All models exhausted
        raise Exception(
            f"All Gemini models rate-limited. Please wait a moment and try again. Last error: {last_error}"
        )

    def _format_docs(self, docs) -> str:
        return "\n\n".join(doc.page_content for doc in docs)

    def _run_tamil_chain(self, question: str) -> str:
        """Generate a Tamil response (with English kept for proper nouns/terms)."""
        docs = self.retriever.invoke(question)
        context = self._format_docs(docs)
        context = clean_context(context)
        full_prompt = TANGLISH_PROMPT_TEMPLATE.format(context=context, question=question)
        messages = [HumanMessage(content=full_prompt)]
        return self._invoke_with_fallback(messages)

    def _run_english_chain(self, question: str) -> str:
        """Generate an English response."""
        docs = self.retriever.invoke(question)
        context = self._format_docs(docs)
        context = clean_context(context)
        full_prompt = ENGLISH_PROMPT_TEMPLATE.format(context=context, question=question)
        messages = [HumanMessage(content=full_prompt)]
        return self._invoke_with_fallback(messages)

    def _is_restricted(self, question: str) -> bool:
        """
        Check if the question contains restricted keywords using simple semantic guardrails.

        Args:
            question (str): The user's input question.

        Returns:
            bool: True if restricted keywords are found, False otherwise.
        """
        normalized_q = re.sub(r'[^a-zA-Z\s]', '', question).lower()
        words = set(normalized_q.split())
        return bool(words.intersection(RESTRICTED_KEYWORDS))

    def _detect_enrollment_query(self, text: str) -> bool:
        """
        Detect if user is asking about joining/enrolling in the program.
        Supports both English and Tamil keywords.
        """
        if not text or not text.strip():
            return False

        enrollment_keywords_en = [
            'join', 'enroll', 'register', 'sign up', 'how to join',
            'subscribe', 'admission', 'application', 'apply',
            'i want to', 'i would like to', 'can i join', 'how do i join',
            'want to enroll', 'want to register', 'want to participate'
        ]

        # Tamil keywords - comprehensive list for enrollment detection
        enrollment_keywords_ta = [
            'சேர',      # join (base form)
            'சேர்',      # join (alternate)
            'சேரண',     # should join
            'சேரணும்',   # should join
            'சேர்ந்து',   # joined
            'சேர்த்து',   # added
            'சேர்க்க',   # to join
            'சேர்க',     # join
            'பங்கு',     # participate/share
            'மாணவ',     # student
            'பதிவு',     # registration
            'வேண்டும்',  # need/want
            'எப்படி',    # how
            'விவரம்',    # details
            'விபரம்',    # information
            'விண்ணப்பம்', # application
            'கட்ணம்',    # fees
            'கோரி',      # ask for
            'செலவு',     # cost
            'பணம்',      # money
            # English words transliterated in Tamil script
            'ஜாயின்',    # join (English in Tamil script)
            'எனரோல்',   # enroll (English in Tamil script)
            'ரெஜிஸ்டர்', # register (English in Tamil script)
            'கோர்ஸ்',    # course (English in Tamil script)
            'பாடம்',     # course/lesson
            'கல்வி',     # education
        ]

        text_lower = text.lower()

        # Debug: Log text info
        logger.debug(f"🔍 Checking enrollment - Text: '{text[:50]}', Len: {len(text)}, Bytes: {text.encode('utf-8')[:50]}")

        # Check English keywords first
        for keyword in enrollment_keywords_en:
            if keyword in text_lower:
                logger.info(f"📝 Enrollment detected (EN): '{keyword}' in '{text[:50]}'")
                return True

        # Check Tamil keywords - these are case-sensitive
        # Try checking the original text directly
        for keyword in enrollment_keywords_ta:
            if keyword in text:
                logger.info(f"📝 Enrollment detected (TA): '{keyword}' in '{text[:50]}'")
                return True

        # Additional check: if text contains any Tamil character and has enrollment-like structure
        has_tamil = bool(re.search(r'[\u0B80-\u0BFF]', text))
        logger.debug(f"🔍 Has Tamil chars: {has_tamil}")

        if has_tamil:
            # Check for word patterns like "சேர" or "பதிவு" or transliterated English words
            critical_kws = ['சேர', 'பதிவு', 'சேர்', 'சேரணும்', 'விண்ணப்பம்', 'ஜாயின்', 'எனரோல்', 'ரெஜிஸ்டர்', 'கோர்ஸ்']
            matched = [kw for kw in critical_kws if kw in text]
            logger.debug(f"🔍 Critical keyword matches: {matched}")

            if matched:
                logger.info(f"📝 Enrollment detected (TA pattern): {matched} in '{text[:50]}'")
                return True

        return False

    async def ask_question(self, question: str) -> dict:
        """
        Processes a user question through guardrails and the RAG pipeline.
        Generates responses in Tamil or English based on input language.
        Automatically falls back to next Gemini model on rate limit.
        Includes TTS audio generation.

        Args:
            question (str): The text question asked by the user.

        Returns:
            dict: Contains 'answer', 'type', and 'audio_url' (if TTS enabled).
        """
        # 1. Check if this is an enrollment query
        is_enrollment = self._detect_enrollment_query(question)
        if is_enrollment:
            logger.info("📝 Enrollment inquiry detected - will show form AND answer from documents")

        # 2. Semantic guardrail / keyword blocklist
        if self._is_restricted(question):
            return {
                "answer": "You do not have the privilege to access this information.",
                "type": "restricted",
                "audio_url": None
            }

        # 3. Detect input language
        language = detect_language(question)
        logger.info(f"Detected language: {language}")

        # 4. RAG generation - use appropriate chain based on language
        if language == 'tamil':
            answer = self._run_tamil_chain(question)
            logger.info("Generated Tamil response")
        else:
            answer = self._run_english_chain(question)
            logger.info("Generated English response")

        # 5. Handle 'Not Found' fallback safely
        not_found_msg = "The requested information is not available."
        not_found_tamil = "இந்த தகவல் கிடைக்கவில்லை."

        is_not_found = not_found_msg.lower() in answer.lower() or not_found_tamil in answer

        # If not found but it's an enrollment query, still show the form with the "not found" answer
        if is_not_found and not is_enrollment:
            return {
                "answer": not_found_msg if language == 'english' else not_found_tamil,
                "type": "not_found",
                "audio_url": None
            }

        # 5.5. Clean markdown and emojis for TTS compatibility
        answer = clean_text_for_tts(answer)

        # 6. Generate TTS audio if service is enabled
        audio_url = None
        if self.tts_service:
            try:
                # Check cache first
                audio_url = self.cache_service.get_cached_audio(answer)

                if not audio_url:
                    # Generate new audio
                    logger.info(f"Generating TTS audio for {language} response")
                    audio_url = self.tts_service.generate_audio(answer)

                    if audio_url:
                        # Cache the result
                        self.cache_service.cache_audio(answer, audio_url)
                        logger.info(f"Generated and cached TTS audio")
                    else:
                        logger.warning("Failed to generate TTS audio")
                else:
                    logger.info("Using cached TTS audio")

            except Exception as e:
                logger.error(f"Error generating TTS audio: {str(e)}")
                audio_url = None

        # 7. Determine response type - if enrollment query, show form + answer
        response_type = "enrollment_form" if is_enrollment else "normal"

        # 8. Return answer with audio
        return {
            "answer": answer.strip(),
            "type": response_type,
            "audio_url": audio_url,
            "language": language  # Include language in response for debugging
        }
