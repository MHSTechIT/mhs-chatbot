import os
import logging
import requests
import re

logger = logging.getLogger(__name__)


def _clean_text_for_tts(text: str) -> str:
    """Remove markdown noise for plain UI + TTS."""
    if not text:
        return text
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"[*_]", "", text)
    text = re.sub(r"\[(.+?)\]", r"\1", text)
    text = re.sub(r"\(https?://[^\)]+\)", "", text)
    text = re.sub(r"^[\s\-*•]+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


GEMINI_MODEL = "gemini-2.5-flash-lite"

SYSTEM_ROLE_PREAMBLE = (
    "You are the AI assistant for My Health School (MHS). "
    "You MUST follow every rule in the policy below. "
    "Do not contradict it. Do not give medical prescriptions or emergency treatment plans."
)


def _rules_file_path() -> str:
    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    env_path = os.getenv("MHS_RULES_PATH")
    if env_path:
        return env_path
    return os.path.join(backend_root, "config", "mhs_assistant_rules.md")


def load_mhs_rules() -> str:
    path = _rules_file_path()
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read().strip()
            if text:
                logger.info(f"MHS rules loaded from {path} ({len(text)} chars)")
            return text
    except OSError as e:
        logger.error(f"MHS rules file missing or unreadable: {path} — {e}")
        return ""


def detect_language(text: str) -> str:
    if re.search(r"[\u0B80-\u0BFF]", text):
        return "tamil"
    return "english"


def detect_enrollment_query(text: str) -> bool:
    if not text or not text.strip():
        return False

    enrollment_keywords_en = [
        "join", "enroll", "enrollment", "register", "sign up", "how to join",
        "subscribe", "admission", "application", "apply",
        "i want to", "i would like to", "can i join", "how do i join",
        "want to enroll", "want to register", "want to participate",
        "course", "fees", "fee", "program", "how can i join", "interested in joining",
    ]
    enrollment_keywords_ta = [
        "சேர", "சேர்", "சேரண", "சேரணும்", "சேர்ந்து", "சேர்க்க", "சேர்க",
        "பதிவு", "விண்ணப்பம்", "கட்ணம்", "செலவு", "பணம்",
        "ஜாயின்", "எனரோல்", "ரெஜிஸ்டர்", "கோர்ஸ்",
    ]

    text_lower = text.lower()
    for kw in enrollment_keywords_en:
        if kw in text_lower:
            logger.info(f"📝 Enrollment detected (EN): '{kw}' in '{text[:50]}'")
            return True
    for kw in enrollment_keywords_ta:
        if kw in text:
            logger.info(f"📝 Enrollment detected (TA): '{kw}' in '{text[:50]}'")
            return True

    if re.search(r"[\u0B80-\u0BFF]", text):
        critical = ["சேர", "பதிவு", "சேர்", "சேரணும்", "விண்ணப்பம்",
                    "ஜாயின்", "எனரோல்", "ரெஜிஸ்டர்", "கோர்ஸ்"]
        matched = [kw for kw in critical if kw in text]
        if matched:
            logger.info(f"📝 Enrollment detected (TA pattern): {matched} in '{text[:50]}'")
            return True
    return False


_RED_FLAG_SUBSTRINGS_EN = [
    "chest pain", "crushing chest", "heart attack",
    "shortness of breath", "cannot breathe", "can't breathe", "breathlessness",
    "blood in stool", "bloody stool",
    "severe abdominal pain", "severe stomach pain",
    "passed out", "lost consciousness", "fainting spell",
    "repeated vomiting", "nonstop vomiting", "can't stop vomiting",
    "kidney failure", "on dialysis", "dialysis",
    "severe dehydration",
    "severe hypoglycemia", "severe low blood sugar",
    "emergency room", "call 911", "call 108",
    "blood sugar 350", "blood sugar 400", "blood sugar 500",
    "sugar 350", "sugar 400", "glucose 350", "glucose 400",
    "reading 350", "reading 400", "sugar above 300", "sugar over 300",
    "glucose above 300", "more than 300 mg", "above 300 mg",
]
_RED_FLAG_TAMIL = [
    "மார்பு வலி", "மூச்சு விட முடியவில்லை", "மயக்கம்",
]


def detect_red_flag_question(text: str) -> bool:
    if not text or len(text.strip()) < 3:
        return False
    t = text.lower()
    for s in _RED_FLAG_SUBSTRINGS_EN:
        if s in t:
            logger.warning(f"Red-flag substring matched: {s!r}")
            return True
    for s in _RED_FLAG_TAMIL:
        if s in text:
            logger.warning(f"Red-flag Tamil phrase matched: {s!r}")
            return True
    sugar_ctx = re.search(
        r"(blood\s*sugar|sugar\s*level|glucose|\brbs\b|\bfbs\b|\bppbs\b|random\s*sugar)", t
    )
    if sugar_ctx:
        m = re.search(r"\b(3[0-9]{2}|[4-9][0-9]{2})\b", t)
        if m and int(m.group(1)) >= 300:
            logger.warning("Red-flag: glucose reading >= 300 with sugar context")
            return True
    preg = "pregnant" in t or "pregnancy" in t
    if preg and any(
        x in t for x in ("uncontrolled", "ketone", "ketoacidosis",
                          "very high sugar", "sugar very high", "emergency")
    ):
        logger.warning("Red-flag: pregnancy with acute glucose crisis wording")
        return True
    return False


RED_FLAG_ANSWER_TA = (
    "இது மிகவும் தீவிரமான நிலை. உடனே மருத்துவரை அல்லது மருத்துவமனையை நாடுங்கள். "
    "நிலைமை சரியான பிறகு lifestyle பற்றி பேசலாம்."
)
RED_FLAG_ANSWER_EN = (
    "This sounds serious. Please seek urgent in-person medical care or the emergency department first. "
    "Once you are stable, we can discuss lifestyle guidance safely."
)

EMOTION_KEYWORDS = {
    "empathetic": ["understand", "sorry", "concerned", "care", "help you", "pain", "suffer", "difficult", "challenge"],
    "encouraging": ["great", "excellent", "wonderful", "success", "improve", "healthy", "strong", "confident", "achieve"],
    "informative": ["research shows", "studies", "evidence", "according", "findings", "clinical", "data", "proven"],
    "conversational": ["let me", "think about", "consider", "perhaps", "likely", "you might", "could be"],
    "professional": ["treatment", "medication", "consult", "doctor", "medical", "condition", "diagnosis", "therapy"],
}

EMOTION_SETTINGS = {
    "empathetic":    {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15, "use_speaker_boost": True, "_label": "🤝 Empathetic"},
    "encouraging":   {"stability": 0.55, "similarity_boost": 0.80, "style": 0.20, "use_speaker_boost": True, "_label": "✨ Encouraging"},
    "informative":   {"stability": 0.60, "similarity_boost": 0.78, "style": 0.10, "use_speaker_boost": True, "_label": "📊 Informative"},
    "conversational":{"stability": 0.55, "similarity_boost": 0.80, "style": 0.15, "use_speaker_boost": True, "_label": "💬 Conversational"},
    "professional":  {"stability": 0.60, "similarity_boost": 0.80, "style": 0.10, "use_speaker_boost": True, "_label": "👨‍⚕️ Professional"},
}


def detect_emotion_and_get_settings(text: str):
    text_lower = text.lower()
    scores = {e: sum(text_lower.count(kw) for kw in kws) for e, kws in EMOTION_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    selected = best if scores[best] > 0 else "conversational"
    cfg = EMOTION_SETTINGS[selected].copy()
    label = cfg.pop("_label")
    logger.info(f"🎭 Detected emotion: {label} (score={scores[selected]})")
    return selected, label, cfg


def _resolve_output_language(req_language: str, question: str) -> str:
    rl = (req_language or "").lower().strip()
    if rl in ("ta", "tamil", "tanglish"):
        return "tamil"
    if rl in ("en", "english"):
        return "english"
    return detect_language(question)


def _finalize_answer_for_client(raw: str) -> str:
    t = _clean_text_for_tts(raw)
    t = t.replace("👉", " ").replace("👍", " ")
    return re.sub(r"\s+", " ", t).strip()


def _get_admin_repo():
    from src.repository.admin_repo import get_admin_repository
    return get_admin_repository()


def _configure_genai():
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    return genai


class HealthChatService:
    """MHS lifestyle assistant: policy-grounded Gemini answers + ElevenLabs TTS hook."""

    def __init__(self):
        logger.info("HealthChatService initializing...")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY not set")

        self._model = None
        self._mhs_rules = load_mhs_rules()

        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs_voice_id = os.getenv("ELEVENLABS_VOICE_ID")
        self.elevenlabs_url = (
            f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}/stream"
            if self.elevenlabs_voice_id else ""
        )
        logger.info("HealthChatService ready")

    def _init_llm(self):
        """Lazily create the Gemini GenerativeModel."""
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=self.google_api_key)
            logger.info(f"Initializing LLM: {GEMINI_MODEL}")
            self._model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.55,
                    max_output_tokens=420,
                    top_p=0.92,
                ),
            )
            logger.info(f"LLM initialized: {GEMINI_MODEL}")

    def generate_tts_url(self, text: str, voice_settings: dict = None) -> dict:
        if not self.elevenlabs_api_key or not text:
            return {"success": False, "audio_url": None, "emotion": None}
        try:
            if voice_settings is None:
                _, emotion_label, voice_settings = detect_emotion_and_get_settings(text)
            else:
                emotion_label = voice_settings.get("emotion_label", "Custom")

            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": voice_settings.get("stability", 0.45),
                    "similarity_boost": voice_settings.get("similarity_boost", 0.85),
                    "style": voice_settings.get("style", 0.95),
                    "use_speaker_boost": voice_settings.get("use_speaker_boost", True),
                },
            }
            headers = {"xi-api-key": self.elevenlabs_api_key, "Content-Type": "application/json"}
            logger.info(f"📢 {emotion_label} — Calling ElevenLabs TTS: {text[:40]}...")
            response = requests.post(self.elevenlabs_url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                logger.info(f"✅ TTS audio generated with {emotion_label} voice")
                return {"success": True, "audio_url": "audio_generated",
                        "emotion": emotion_label, "voice_settings": payload["voice_settings"]}
            logger.error(f"❌ ElevenLabs error {response.status_code}: {response.text[:100]}")
            return {"success": False, "audio_url": None, "emotion": None}
        except Exception as e:
            logger.error(f"❌ TTS error: {e}")
            return {"success": False, "audio_url": None, "emotion": None}

    def _build_system_instruction(self, supplemental_docs: str, output_language: str) -> str:
        policy = self._mhs_rules.strip() if self._mhs_rules else (
            "Fallback: You are MHS lifestyle/metabolic health assistant only. "
            "No prescriptions. Urgent symptoms → direct to emergency care. "
            "Casual Tamil script for Tamil UI; simple English for English UI."
        )
        if output_language == "tamil":
            ui_lock = (
                "## CRITICAL — TA chat style (this request)\n"
                "The user selected **TA**. Write in **casual spoken Tamil** — like a Tamil health advisor speaking to a patient naturally.\n"
                "- Sentences must be in Tamil script. Most words must be Tamil.\n"
                "- English is allowed ONLY for key medical/technical terms: diabetes, insulin, sugar level, HbA1c, PCOS, BP, cholesterol, calories, millets. Write these inline, no parentheses.\n"
                "- Do NOT write Latin-letter Tamil words (like \"namma\", \"panrom\", \"sollunga\", \"approach-la\") — use Tamil script for Tamil words.\n"
                "- Do NOT end the reply with English sentences or an English paragraph.\n"
                "- Warm and simple — not formal or literary Tamil. Short sentences. 3–4 sentences maximum.\n"
            )
        else:
            ui_lock = (
                "## CRITICAL — Active UI language (this request only)\n"
                "The user selected **EN** in the app. Write the **entire** reply in simple, warm English.\n"
            )
        parts = [SYSTEM_ROLE_PREAMBLE, "", ui_lock, "## Policy", policy]
        if supplemental_docs and supplemental_docs.strip():
            parts += [
                "",
                "## Optional internal facts (schedules, fees, links)",
                "Use only when relevant. Never contradict the policy above.",
                supplemental_docs.strip(),
            ]
        return "\n".join(parts)

    def _build_user_prompt(self, question: str, language: str) -> str:
        if language == "tamil":
            lang_instr = (
                "App language: **TA** (locked). Write in **casual spoken Tamil script**.\n"
                "- Sentences must be in Tamil script. English only for key medical terms (diabetes, insulin, sugar level, HbA1c, PCOS, BP) — inline, no parentheses.\n"
                "- Do NOT write Latin-letter Tamil words. Use Tamil script for Tamil words.\n"
                "- Do NOT end with English sentences or an English paragraph.\n"
                "- **Length: 3–4 sentences. Cover the core point and stop. No lists.**\n"
                "Follow policy. Never promise to stop medicines or guaranteed cure."
            )
        else:
            lang_instr = (
                "App language: **EN** (locked). Respond in simple, warm English only. "
                "Plain text only — no markdown headings, no bullet points. "
                "**Length: 3–4 sentences maximum. Cover the key point clearly and stop. Do not give long lists.**\n"
                "Follow policy. Never promise to stop medicines or guaranteed cure."
            )
        return f"User question:\n{question}\n\n{lang_instr}"

    async def ask_question(self, question: str, req_language: str = "") -> dict:
        if not question or not question.strip():
            return {"answer": "தயவுசெய்து ஒரு கேள்வி கேளுங்கள்.", "type": "error", "audio_url": None}

        language = _resolve_output_language(req_language, question)
        logger.info(f"🆕 Output language: {language} (req={req_language!r}) — Q: {question[:50]}")

        if detect_red_flag_question(question):
            ans = RED_FLAG_ANSWER_TA if language == "tamil" else RED_FLAG_ANSWER_EN
            ans = _finalize_answer_for_client(ans)
            _, emotion_label, voice_settings = detect_emotion_and_get_settings(ans)
            return {
                "answer": ans, "type": "normal",
                "audio_url": "/tts/generate" if self.elevenlabs_api_key else None,
                "emotion": emotion_label,
                "voice_settings": voice_settings if emotion_label else None,
            }

        is_enrollment = detect_enrollment_query(question)
        if is_enrollment:
            logger.info("📝 Enrollment inquiry detected")

        try:
            self._init_llm()

            supplemental = ""
            try:
                admin_repo = _get_admin_repo()
                doc_content = admin_repo.get_documents_content()
                if doc_content and doc_content.strip():
                    supplemental = doc_content
                    logger.info(f"📚 Supplemental admin documents: {len(supplemental)} chars")
            except Exception as e:
                logger.warning(f"Supplemental documents unavailable: {e}")

            system_instruction = self._build_system_instruction(supplemental, language)
            user_prompt = self._build_user_prompt(question.strip(), language)

            # Generate via direct Gemini API (system_instruction injected into model config)
            import google.generativeai as genai
            genai.configure(api_key=self.google_api_key)
            model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                system_instruction=system_instruction,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.55,
                    max_output_tokens=420,
                    top_p=0.92,
                ),
            )
            response = model.generate_content(user_prompt)
            answer = (response.text or "").strip()

            if not answer:
                answer = "Unable to generate answer." if language == "english" else "பதிலை உருவாக்க முடியவில்லை."

            answer = _finalize_answer_for_client(answer)
            logger.info(f"✅ Response ({language}): {answer[:80]}")

            _, emotion_label, voice_settings = detect_emotion_and_get_settings(answer)
            audio_url = "/tts/generate" if self.elevenlabs_api_key else None
            response_type = "enrollment_form" if is_enrollment else "normal"

            if is_enrollment:
                not_found_indicators = [
                    "i don't have", "என்னிடம் இந்த தகவல் இல்லை",
                    "இந்த தகவல் கிடைக்கவில்லை", "not available",
                    "outside my scope", "cannot answer",
                ]
                if any(ind in answer.lower() for ind in not_found_indicators) or len(answer.strip()) < 30:
                    if language == "tamil":
                        answer = _finalize_answer_for_client(
                            "எங்கள் program பத்தி மேலும் தெரிஞ்சுக்கணும்னா, கீழே உள்ள form-ஐ fill பண்ணுங்க. "
                            "எங்கள் team விரைவில் உங்களை contact பண்ணுவாங்க."
                        )
                    else:
                        answer = _finalize_answer_for_client(
                            "To know more about our course, please fill in the form below. "
                            "Our support team will contact you soon."
                        )
                    _, emotion_label, voice_settings = detect_emotion_and_get_settings(answer)

            return {
                "answer": answer, "type": response_type, "audio_url": audio_url,
                "emotion": emotion_label,
                "voice_settings": voice_settings if emotion_label else None,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error: {error_msg}")
            return {"answer": f"Error: {error_msg[:100]}", "type": "error", "audio_url": None}
