import os
import re
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from src.services.TtsService import ElevenLabsTtsService

logger = logging.getLogger(__name__)

# Gemini models with fallback - use faster models
# Updated to use latest available models (gemini-2.0-flash deprecated for new users)
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]

# Tamil script character ranges
TAMIL_CHAR_RANGES = [(0x0B80, 0x0C00)]

# Common Tamil words in Latin script (Tanglish)
TAMIL_WORDS_LATIN = {
    'enakku', 'ennakku', 'neenga', 'ninga', 'pathi', 'sollu', 'enna',
    'adi', 'illai', 'irukku', 'pannu', 'oru', 'ava', 'avar', 'paathu',
    'vandhu', 'seiyanum', 'sollrenu', 'neeya', 'avarukkana', 'pannuvai',
    'pannuvan', 'pannungal', 'pannanum', 'pannirukke', 'ungaluku', 'unkalai',
}

def is_tamil_text(text: str) -> bool:
    """Check if text contains Tamil characters or Tamil words in Latin script (Tanglish)."""
    # Check for Tamil Unicode characters
    for char in text:
        code_point = ord(char)
        for start, end in TAMIL_CHAR_RANGES:
            if start <= code_point < end:
                return True

    # Check for Tamil words in Latin script
    text_lower = text.lower()
    words = re.findall(r'\b[a-z]+\b', text_lower)
    tamil_word_count = sum(1 for word in words if word in TAMIL_WORDS_LATIN)

    return tamil_word_count >= 1

# English prompt - optimized for speed, max 2 paragraphs
ENGLISH_PROMPT = """You are a helpful AI assistant answering questions.

Answer in MAXIMUM 2 short paragraphs. Be concise - give only the asked information.
Plain text only, NO markdown, NO emojis.
If you don't know, say: "I couldn't find information about that."

Question: {question}

Answer:"""

# Tamil prompt - optimized for speed, max 2 paragraphs
TAMIL_PROMPT = """நீ ஒரு உதவிகரமான AI உதவி.

அதிகபட்சம் 2 சிறிய பத்திகள் மட்டுமே விடை கொடுக்க வேண்டும். சுருக்கமாக - கேட்ட தகவலை மட்டும் சொல்லுங்கள்.
சுத்தமான தமிழ் மட்டுமே. எந்த markdown, emojis இல்லை.
தகவல் இல்லாவிட்டால்: "இந்த விஷயத்தைப் பற்றி தகவல் கிடைக்கவில்லை."

கேள்வி: {question}

விடை:"""

class WebSearchChatService:
    """
    Web-based Q&A service using Gemini with web search capabilities.
    Generates answers and converts them to speech using ElevenLabs.
    """

    def __init__(self):
        """Initialize Gemini models and TTS service."""
        google_api_key = os.getenv("GOOGLE_API_KEY")

        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set.")

        self.google_api_key = google_api_key

        # Initialize Gemini model (use gemini-2.5-flash - latest available for new users)
        model_name = "gemini-2.5-flash"
        logger.info(f"Initializing WebSearchChatService with model: {model_name}")
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.7,
            google_api_key=google_api_key
        )
        logger.info(f"Successfully initialized Gemini model: {model_name}")
        self.model_name = model_name

        # Initialize TTS Service
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

    def _invoke_with_fallback(self, messages: list) -> str:
        """
        Invoke Gemini.

        Args:
            messages: List of LangChain message objects

        Returns:
            str: The LLM response text
        """
        try:
            response = self.llm.invoke(messages)
            logger.info(f"Successfully used Gemini model: {self.model_name}")
            return response.content
        except Exception as e:
            logger.error(f"Error calling model '{self.model_name}': {str(e)}")
            raise

    async def ask_question(self, question: str) -> dict:
        """
        Answer a question using Gemini web search and TTS.
        Automatically detects Tamil/Tanglish and responds in the same language.

        Args:
            question: The user's question

        Returns:
            dict with 'answer', 'type', and optional 'audio_url'
        """
        try:
            if not question or not question.strip():
                return {
                    "answer": "Please ask a valid question.",
                    "type": "error",
                    "audio_url": None
                }

            logger.info(f"Web search question: {question}")

            # Detect language and select appropriate prompt
            is_tamil = is_tamil_text(question)
            prompt_template = TAMIL_PROMPT if is_tamil else ENGLISH_PROMPT
            logger.info(f"Detected language: {'Tamil/Tanglish' if is_tamil else 'English'}")

            # Generate answer using Gemini
            prompt = prompt_template.format(question=question)
            messages = [HumanMessage(content=prompt)]

            answer = self._invoke_with_fallback(messages)

            if not answer or not answer.strip():
                answer = "I could not generate an answer to your question." if not is_tamil else "உனது கேள்விக்கு பதிலை உருவாக்க முடியவில்லை."

            logger.info(f"Generated answer length: {len(answer)}")

            # Generate TTS audio if service is available
            audio_url = None
            if self.tts_service:
                try:
                    # Clean text for TTS
                    clean_text = answer.strip()
                    audio_url = self.tts_service.generate_audio(clean_text)
                    logger.info(f"TTS audio generated successfully")
                except Exception as e:
                    logger.warning(f"TTS generation failed: {e}")
                    audio_url = None

            return {
                "answer": answer,
                "type": "normal",
                "audio_url": audio_url
            }

        except Exception as e:
            logger.error(f"Web search error: {str(e)}")
            return {
                "answer": f"An error occurred: {str(e)}",
                "type": "error",
                "audio_url": None
            }
