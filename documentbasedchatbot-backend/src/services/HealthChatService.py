import os
import logging
import requests
import re

logger = logging.getLogger(__name__)

# gemini-2.5-flash-lite: fastest, lowest latency, works for new API keys
GEMINI_MODEL = "gemini-2.5-flash-lite"

# Language detection - detect if text is Tamil, Tanglish, or English
def detect_language(text: str) -> str:
    """Detect language: 'tamil', 'tanglish', or 'english'."""
    # Tamil Unicode range: U+0B80 to U+0BFF
    tamil_pattern = r'[\u0B80-\u0BFF]'
    has_tamil = bool(re.search(tamil_pattern, text))
    if has_tamil:
        return 'tamil'  # Tamil or Tanglish (Tamil + English)
    else:
        return 'english'  # English only

# Tamil-to-English keyword mapping for common health terms
TAMIL_TO_ENGLISH_KEYWORDS = {
    'சர்க்கரை': 'diabetes',
    'நோய்': 'disease',
    'சர்க்கரை நோய்': 'diabetes',
    'குணமாக்க': 'reverse',
    'குணம்': 'cure',
    'நிறுத்த': 'stop',
    'தடுக்க': 'prevent',
    'சிகிச்சை': 'treatment',
    'மருந்து': 'medicine',
    'மாத்திரை': 'tablet',
    'உணவு': 'diet',
    'உணவுக்கட்டுப்பாடு': 'diet control',
    'உடல் பயிற்சி': 'exercise',
    'தவ': 'fast',
    'விளக்கம்': 'information',
    'பற்றி': 'about',
    'பற்றி சொல்ல': 'tell about',
    'என்ன': 'what',
    'எப்படி': 'how',
    'ஆரம்ப': 'initial',
    'இரத்தம்': 'blood',
    'அளவு': 'level',
}

# Translate Tamil question to English for document search
def translate_tamil_to_english(text: str, llm) -> str:
    """Translate Tamil question to English for better document matching."""
    try:
        # First, try keyword replacement for common terms
        translated = text.lower()
        for tamil, english in TAMIL_TO_ENGLISH_KEYWORDS.items():
            translated = translated.replace(tamil.lower(), english.lower())

        # If keyword replacement produced something meaningful, use it
        if len(translated) > 5 and translated != text.lower():
            logger.info(f"🔤 Tamil→English (keyword): '{text[:50]}' → '{translated[:50]}'")
            return translated

        # Fallback: use LLM for translation
        from langchain_core.messages import HumanMessage
        translate_prompt = f"""Translate the following Tamil question to English. Return ONLY the English translation, nothing else.

Tamil: {text}

English translation:"""

        messages = [HumanMessage(content=translate_prompt)]
        response = llm.invoke(messages)
        translated = response.content.strip() if response.content else text
        logger.info(f"🔤 Tamil→English (LLM): '{text[:50]}' → '{translated[:50]}'")
        return translated
    except Exception as e:
        logger.warning(f"Translation failed: {e}, using original text")
        return text

# Detect if user is asking about joining/enrolling in the program
def detect_enrollment_query(text: str) -> bool:
    """Detect if user is asking about joining program, webinar, or course."""
    if not text or not text.strip():
        return False

    enrollment_keywords_en = [
        'join', 'enroll', 'enrollment', 'register', 'sign up', 'how to join',
        'subscribe', 'admission', 'application', 'apply',
        'i want to', 'i would like to', 'can i join', 'how do i join',
        'want to enroll', 'want to register', 'want to participate',
        'course', 'fees', 'fee', 'program', 'how can i join', 'interested in joining'
    ]

    # Tamil keywords - ONLY enrollment-specific keywords (removed generic words like "எப்படி" that cause false positives)
    enrollment_keywords_ta = [
        'சேர',      # join (base form)
        'சேர்',      # join (alternate)
        'சேரண',     # should join
        'சேரணும்',   # should join
        'சேர்ந்து',   # joined
        'சேர்க்க',   # to join
        'சேர்க',     # join
        'பதிவு',     # registration
        'விண்ணப்பம்', # application
        'கட்ணம்',    # fees
        'செலவு',     # cost
        'பணம்',      # money
        # English words transliterated in Tamil script
        'ஜாயின்',    # join (English in Tamil script)
        'எனரோல்',   # enroll (English in Tamil script)
        'ரெஜிஸ்டர்', # register (English in Tamil script)
        'கோர்ஸ்',    # course (English in Tamil script)
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

# Emotion Detection - Keywords for different tones
EMOTION_KEYWORDS = {
    'empathetic': ['understand', 'sorry', 'concerned', 'care', 'help you', 'pain', 'suffer', 'difficult', 'challenge'],
    'encouraging': ['great', 'excellent', 'wonderful', 'success', 'improve', 'healthy', 'strong', 'confident', 'achieve'],
    'informative': ['research shows', 'studies', 'evidence', 'according', 'findings', 'clinical', 'data', 'proven'],
    'conversational': ['let me', 'think about', 'consider', 'perhaps', 'likely', 'you might', 'could be'],
    'professional': ['treatment', 'medication', 'consult', 'doctor', 'medical', 'condition', 'diagnosis', 'therapy']
}

# Function to detect emotional tone and return settings
def detect_emotion_and_get_settings(text: str):
    """
    Detect emotional tone from response text and return emotion tag + optimized voice settings.
    Returns: (emotion_type, emotion_label, voice_settings_dict)
    """
    text_lower = text.lower()
    emotion_scores = {emotion: 0 for emotion in EMOTION_KEYWORDS}

    # Count keyword matches
    for emotion, keywords in EMOTION_KEYWORDS.items():
        for keyword in keywords:
            emotion_scores[emotion] += text_lower.count(keyword)

    # Determine dominant emotion
    max_emotion = max(emotion_scores, key=emotion_scores.get)

    # Map emotions to voice settings for ElevenLabs
    emotion_settings = {
        'empathetic': {
            'stability': 0.35,           # Lower stability = warmer, more emotional
            'similarity_boost': 0.80,    # Slightly lower for warmth
            'style': 0.85,               # High style for emotional expression
            'use_speaker_boost': True,
            'emotion_label': '🤝 Empathetic'
        },
        'encouraging': {
            'stability': 0.50,           # Moderate stability for uplifting tone
            'similarity_boost': 0.90,    # Higher for confident delivery
            'style': 0.95,               # Maximum style for enthusiasm
            'use_speaker_boost': True,
            'emotion_label': '✨ Encouraging'
        },
        'informative': {
            'stability': 0.65,           # Higher stability for clarity
            'similarity_boost': 0.85,    # Clear natural voice
            'style': 0.75,               # Moderate style for professional tone
            'use_speaker_boost': True,
            'emotion_label': '📊 Informative'
        },
        'conversational': {
            'stability': 0.45,           # Lower for natural flow
            'similarity_boost': 0.80,    # Natural conversational quality
            'style': 0.80,               # Good style for engaging tone
            'use_speaker_boost': True,
            'emotion_label': '💬 Conversational'
        },
        'professional': {
            'stability': 0.70,           # High stability for authority
            'similarity_boost': 0.90,    # Clear and confident
            'style': 0.70,               # Lower style for formal tone
            'use_speaker_boost': True,
            'emotion_label': '👨‍⚕️ Professional'
        }
    }

    # Use detected emotion or default
    if emotion_scores[max_emotion] > 0:
        selected_emotion = max_emotion
    else:
        selected_emotion = 'conversational'  # Default tone

    settings = emotion_settings[selected_emotion]
    emotion_label = settings.pop('emotion_label')

    logger.info(f"🎭 Detected emotion: {emotion_label} (Score: {emotion_scores[selected_emotion]})")

    return selected_emotion, emotion_label, settings

# Tamil Prompt - STRICT Document-Only, MAX 2 paragraphs
TAMIL_PROMPT = """You are a helpful assistant from My Health School. Your ONLY job is to answer from the documents provided below.

IMPORTANT RULES:
1. ALWAYS use information from the documents below for your answer
2. If documents mention something about the question, use that information
3. Do NOT use general knowledge that's not in documents
4. If documents don't mention it, say "என்னிடம் இந்த தகவல் இல்லை" (I don't have this information)
5. Use simple Tamil + English mix like people speak
6. Answer in Tamil, not English
7. CRITICAL: Keep your answer to MAXIMUM 2 short paragraphs. Be concise. Give only the asked information within that limit.

Documents:
{documents_context}

Question: {question}

Search the documents carefully and answer ONLY what's in the documents. Maximum 2 paragraphs, concise:"""

# English Prompt - STRICT Document-Only, MAX 2 paragraphs
ENGLISH_PROMPT = """You are a helpful assistant from My Health School. Your ONLY job is to answer from the documents provided below.

IMPORTANT RULES:
1. ALWAYS search the documents for relevant information
2. If documents mention something about the question, use that information
3. Answer with information from the documents
4. If the documents don't have the answer, say "I don't have this information"
5. Do NOT add general knowledge not found in documents
6. CRITICAL: Keep your answer to MAXIMUM 2 short paragraphs. Be concise. Give only the asked information within that limit.

Documents:
{documents_context}

Question: {question}

Search the documents carefully and answer based ONLY on what's in the documents. Maximum 2 paragraphs, concise:"""

# Module-level singleton so AdminRepository (and its DB load) happens once per process
_admin_repo_instance = None

def _get_admin_repo():
    global _admin_repo_instance
    if _admin_repo_instance is None:
        from src.repository.admin_repo import AdminRepository
        _admin_repo_instance = AdminRepository()
        logger.info("AdminRepository singleton created")
    return _admin_repo_instance


class HealthChatService:
    """Ultra-fast Tamil health Q&A for My Health School."""

    def __init__(self):
        """Initialize with fastest configuration and document repository."""
        logger.info("HealthChatService initializing...")

        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY not set")

        self.llm = None  # Lazy init

        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs_voice_id = os.getenv("ELEVENLABS_VOICE_ID")
        self.elevenlabs_url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}/stream"

        logger.info("HealthChatService ready")

    def _init_llm(self):
        """Lazy initialize LLM on first use."""
        if self.llm is None:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                from langchain_core.messages import HumanMessage

                logger.info(f"Initializing LLM: {GEMINI_MODEL}")
                self.llm = ChatGoogleGenerativeAI(
                    model=GEMINI_MODEL,
                    temperature=0.7,
                    google_api_key=self.google_api_key,
                    timeout=30,
                    max_tokens=500,
                    top_p=0.95,
                )
                logger.info(f"LLM initialized: {GEMINI_MODEL}")
            except Exception as e:
                logger.error(f"LLM init failed: {str(e)}")
                raise

    def generate_tts_url(self, text: str, voice_settings: dict = None) -> dict:
        """
        Generate TTS audio via ElevenLabs with emotional voice settings.

        Args:
            text: The text to convert to speech
            voice_settings: Optional ElevenLabs voice settings dict with emotion-based parameters

        Returns:
            Dict with audio metadata and emotion information
        """
        if not self.elevenlabs_api_key or not text:
            return {'success': False, 'audio_url': None, 'emotion': None}

        try:
            # Use provided voice settings or detect emotion from text
            if voice_settings is None:
                _, emotion_label, voice_settings = detect_emotion_and_get_settings(text)
            else:
                emotion_label = voice_settings.get('emotion_label', 'Custom')

            payload = {
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {
                    "stability": voice_settings.get("stability", 0.45),
                    "similarity_boost": voice_settings.get("similarity_boost", 0.85),
                    "style": voice_settings.get("style", 0.95),
                    "use_speaker_boost": voice_settings.get("use_speaker_boost", True),
                },
            }

            headers = {
                "xi-api-key": self.elevenlabs_api_key,
                "Content-Type": "application/json",
            }

            logger.info(f"📢 {emotion_label} - Calling ElevenLabs TTS: {text[:40]}...")
            response = requests.post(
                self.elevenlabs_url,
                json=payload,
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                logger.info(f"✅ TTS audio generated successfully with {emotion_label} voice")
                return {
                    'success': True,
                    'audio_url': "audio_generated",
                    'emotion': emotion_label,
                    'voice_settings': payload['voice_settings']
                }
            else:
                logger.error(f"❌ ElevenLabs error {response.status_code}: {response.text[:100]}")
                return {'success': False, 'audio_url': None, 'emotion': None}

        except Exception as e:
            logger.error(f"❌ TTS error: {str(e)}")
            return {'success': False, 'audio_url': None, 'emotion': None}

    async def ask_question(self, question: str) -> dict:
        """Fast Tamil response - 1-2 seconds with uploaded document context."""
        if not question or not question.strip():
            return {
                "answer": "தயவுசெய்து ஒரு கேள்வி கேளுங்கள்.",
                "type": "error",
                "audio_url": None
            }

        # Detect language (tamil, tanglish, or english)
        language = detect_language(question)
        logger.info(f"🆕 Detected language: {language} - Q: {question[:50]}")

        # Check if this is an enrollment/program inquiry
        is_enrollment = detect_enrollment_query(question)
        if is_enrollment:
            logger.info("📝 Enrollment inquiry detected - will show form AND answer from documents")

        try:

            # Initialize LLM on first use
            self._init_llm()
            from langchain_core.messages import HumanMessage

            # 🔤 For Tamil questions, translate to English for better document matching
            search_question = question
            if language == 'tamil':
                search_question = translate_tamil_to_english(question, self.llm)
                logger.info(f"🔤 Using translated English question for document search: {search_question[:50]}")

            # 📄 Retrieve documents from admin repository (singleton — no DB call per request)
            documents_content = ""
            try:
                admin_repo = _get_admin_repo()
                logger.debug(f"📚 Documents in repository: {len(admin_repo.documents)}")
                documents_content = admin_repo.get_documents_content()

                if documents_content:
                    logger.info(f"📚 Retrieved documents from admin repository - {len(documents_content)} chars")
                else:
                    logger.warning("⚠️ No documents found in repository")
            except Exception as e:
                logger.warning(f"Error retrieving documents: {str(e)}")
                import traceback
                logger.warning(traceback.format_exc())
                documents_content = ""
            if documents_content and documents_content.strip():
                if language == 'tamil':
                    documents_context = f"\nUploaded Documents and Links (Katikai Katippu):\n{documents_content}"
                else:
                    documents_context = f"\nUploaded Documents and Links:\n{documents_content}"
            else:
                documents_context = ""

            # Select prompt based on language - but use translated question for search
            if language == 'tamil':
                prompt = TAMIL_PROMPT.format(
                    question=search_question,  # Use translated English question for better matching
                    documents_context=documents_context
                )
                logger.info(f"🔤 Using Tamil prompt with translated English question")
            else:
                prompt = ENGLISH_PROMPT.format(
                    question=search_question,
                    documents_context=documents_context
                )
                logger.info(f"🔤 Using English prompt")
            messages = [HumanMessage(content=prompt)]

            # Fast generation
            response = self.llm.invoke(messages)
            answer = response.content.strip() if response.content else ""

            if not answer:
                answer = "Unable to generate answer." if language == 'english' else "பதிலை உருவாக்க முடியவில்லை."

            logger.info(f"✅ Response ({language}): {answer[:60]}")

            # Detect emotion from answer for expressive TTS
            emotion, emotion_label, voice_settings = detect_emotion_and_get_settings(answer)
            logger.info(f"🎭 Response emotion detected: {emotion_label}")

            # Signal TTS endpoint — frontend will call /tts/generate separately
            audio_url = None
            emotion_tag = emotion_label
            if self.elevenlabs_api_key:
                audio_url = "/tts/generate"
                logger.info(f"✅ TTS endpoint ready with {emotion_tag}")

            # Determine response type - if enrollment query, show form + answer
            response_type = "enrollment_form" if is_enrollment else "normal"

            # If enrollment detected, always give a helpful enrollment message
            if is_enrollment:
                not_found_indicators = [
                    "i don't have this information",
                    "என்னிடம் இந்த தகவல் இல்லை",
                    "இந்த தகவல் கிடைக்கவில்லை",
                    "the requested information is not available",
                ]
                answer_lower = answer.lower().strip()
                is_not_found = any(ind in answer_lower for ind in not_found_indicators)

                if is_not_found or len(answer.strip()) < 30:
                    if language == 'tamil':
                        answer = "எங்கள் கோர்ஸ் பற்றி மேலும் தெரிந்துகொள்ள, கீழே உள்ள படிவத்தை நிரப்பவும். எங்கள் ஆலோசகர் விரைவில் உங்களை தொடர்பு கொள்வார்."
                    else:
                        answer = "To know more about our course, please fill in the form below. Our support team will contact you soon."
                    logger.info("📝 Replaced not-found with enrollment guidance message")

            return {
                "answer": answer,
                "type": response_type,
                "audio_url": audio_url,
                "emotion": emotion_tag,
                "voice_settings": voice_settings if emotion_tag else None
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error: {error_msg}")
            # Return the actual error message for debugging
            return {
                "answer": f"[NEW_CODE] Error: {error_msg[:100]}",
                "type": "error",
                "audio_url": None
            }
