"""
One-time script: generate all static audio via ElevenLabs and save to Supabase.
Run once after deploy:  python generate_welcome_audio.py
"""
import os, base64, uuid
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

try:
    import requests
except ImportError:
    print("requests not installed — run: pip install requests"); raise

STATIC_AUDIO_TEXTS = {
    "welcome_ta": "சக்கரை நோய் பற்றி உங்களுக்கு ஏதாவது கேள்விகள் இருந்தால், தயங்காம கேளுங்கள்.",
    "enrollment_prompt_en": "For more details and personalized guidance, please fill in the form below — our team will contact you soon!",
    "enrollment_prompt_ta": "நம்ம course பத்தி more details தெரிஞ்சுக்கணும்னா, கீழே உள்ள form-ஐ fill பண்ணுங்க! எங்க team உங்களை விரைவில் contact பண்ணுவாங்க!",
    "post_enrollment_en": "Thank you! Our team will contact you soon and answer all your questions!",
    "post_enrollment_ta": "நன்றி! எங்க team விரைவில் உங்களை contact பண்ணி உங்க கேள்விகளுக்கு பதில் சொல்வாங்க!",
}

api_key   = os.getenv("ELEVENLABS_API_KEY")
voice_id  = os.getenv("ELEVENLABS_VOICE_ID")
db_url    = os.getenv("DB_CONNECTION")

if not api_key or not voice_id:
    raise SystemExit("❌  ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID not set in .env")
if not db_url:
    raise SystemExit("❌  DB_CONNECTION not set in .env")

# ── DB setup ──────────────────────────────────────────────────────────────────
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine(db_url, pool_pre_ping=True)
Session = sessionmaker(bind=engine)

def get_existing(session, key: str):
    row = session.execute(
        text("SELECT id, content FROM documents WHERE title = :t"),
        {"t": f"static_audio:{key}"}
    ).fetchone()
    return row

def upsert_audio(session, key: str, audio_b64: str):
    existing = get_existing(session, key)
    if existing:
        session.execute(
            text("UPDATE documents SET content = :c WHERE title = :t"),
            {"c": audio_b64, "t": f"static_audio:{key}"}
        )
        print(f"  [UPD] Updated  {key}")
    else:
        new_id = str(uuid.uuid4())
        session.execute(
            text("""INSERT INTO documents (id, title, type, file_name, content)
                    VALUES (:id, :title, 'static_audio', :fn, :content)"""),
            {"id": new_id, "title": f"static_audio:{key}",
             "fn": f"{key}.mp3", "content": audio_b64}
        )
        print(f"  [INS] Inserted {key}")
    session.commit()

# ── ElevenLabs TTS ────────────────────────────────────────────────────────────
def generate_audio_b64(text: str) -> str:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.7,
            "use_speaker_boost": True,
        },
    }
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"ElevenLabs {resp.status_code}: {resp.text[:200]}")
    return base64.b64encode(resp.content).decode("utf-8")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    session = Session()
    try:
        for key, text_val in STATIC_AUDIO_TEXTS.items():
            existing = get_existing(session, key)
            if existing and existing.content:
                print(f"  [SKIP] {key} (already exists)")
                continue
            print(f"  [GEN]  {key}...")
            b64 = generate_audio_b64(text_val)
            upsert_audio(session, key, b64)
        print("\n[DONE] All static audio ready in Supabase.")
    except Exception as e:
        print(f"\n[ERR]  {e}")
        raise
    finally:
        session.close()
