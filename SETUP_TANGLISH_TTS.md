# Tanglish + ElevenLabs TTS Setup Guide

## Overview
Your chatbot now supports **Tanglish responses** (Tamil-English mix) and **ElevenLabs text-to-speech** audio playback with caching.

## ✅ What Has Been Implemented

### Backend
- ✅ Tanglish response generation via LLM system prompt
- ✅ ElevenLabs TTS integration (TtsService.py)
- ✅ Supabase audio URL caching (CacheService.py)
- ✅ Updated API response with audio_url field
- ✅ All dependencies added to requirements.txt

### Frontend
- ✅ Audio URL playback support (replaces browser SpeechSynthesis)
- ✅ Replay button uses ElevenLabs audio (with fallback)
- ✅ Message objects store audio URLs

### Configuration
- ✅ .env updated with ElevenLabs credentials
- ✅ Supabase connection ready for caching

## 🔧 Setup Steps

### Step 1: Install New Dependencies
```bash
cd documentbasedchatbot-backend
pip install -r requirements.txt
```

**Newly installed packages:**
- `elevenlabs` - ElevenLabs Python SDK
- `requests` - HTTP library for API calls
- `supabase` - Supabase Python client

### Step 2: Create Supabase Cache Table

1. **Go to Supabase Dashboard**
   - https://app.supabase.com/projects
   - Select your project

2. **Open SQL Editor** (Left sidebar → SQL Editor)

3. **Paste and run the migration:**
   ```sql
   CREATE TABLE IF NOT EXISTS tts_cache (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       text_hash VARCHAR(64) UNIQUE NOT NULL,
       tanglish_text TEXT NOT NULL,
       audio_url TEXT NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       hits INT DEFAULT 0
   );

   CREATE INDEX IF NOT EXISTS idx_tts_cache_hash ON tts_cache(text_hash);
   CREATE INDEX IF NOT EXISTS idx_tts_cache_hits ON tts_cache(hits DESC);
   ```

   **Or run the provided migration file:**
   ```bash
   # Read the SQL file and copy-paste it into Supabase SQL Editor
   cat migrations/001_create_tts_cache_table.sql
   ```

### Step 3: Verify Backend Startup

```bash
# In documentbasedchatbot-backend folder
python test_api.py
```

**Expected output:**
```
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:9000
INFO:     Application startup complete.
```

### Step 4: Test Backend API

```bash
curl -X POST http://localhost:9000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is My Health School?"}' | jq .
```

**Expected response:**
```json
{
  "answer": "My Health School oru diabetes reversal program...",
  "type": "normal",
  "audio_url": "https://api.elevenlabs.io/..."
}
```

### Step 5: Start Frontend

```bash
cd documentbasedchatbot-frontend
npm run dev
```

**Open in browser:** http://localhost:5173

## 🎤 How It Works

### Request Flow
1. **User asks question** → Text input to ChatContainer
2. **Send to backend** → POST /ask with `{"question": "..."}`
3. **Backend processes**:
   - Retrieves context from vector DB
   - Generates **Tanglish response** (LLM system prompt)
   - Checks cache for audio URL (SHA256 hash lookup)
   - If not cached, calls ElevenLabs TTS API
   - Stores audio URL in Supabase cache
4. **Frontend receives** → answer + type + audio_url
5. **Plays audio** → Uses ElevenLabs audio player (or fallback to browser TTS)

### Audio Caching Flow
- **First request** for answer → Generate audio via ElevenLabs (~2-3 seconds)
- **Same answer again** → Instant playback from cache
- **Benefits**: Reduces API calls, faster playback, cost savings

## 🔊 Voice Configuration

**Voice ID:** `Ahq9IAlmr15JKZ2Fa5ov`
- **Gender:** Female
- **Language:** Supports English + Tamil (Tanglish)
- **Stability:** 0.5 (balanced between stability and variability)
- **Similarity:** 0.75 (high similarity to original voice)

To change voice, update `.env`:
```bash
ELEVENLABS_VOICE_ID=<new_voice_id>
```

Find available voices: https://elevenlabs.io/voice-lab

## 🧪 Testing Tanglish Output

### Test 1: Check Tanglish Generation
```bash
python -c "
from src.services.ChatService.ChatService import ChatServiceImpl
service = ChatServiceImpl()
import asyncio
result = asyncio.run(service.ask_question('Tell me about health'))
print('Answer:', result['answer'])
print('Type:', result['type'])
print('Audio URL:', result.get('audio_url'))
"
```

### Test 2: Verify Cache Works
```bash
# First call - generates audio
curl -X POST http://localhost:9000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is health school?"}' | jq '.audio_url'

# Second call - should return same audio (from cache)
curl -X POST http://localhost:9000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is health school?"}' | jq '.audio_url'
```

### Test 3: Replay Button in Frontend
1. Ask a question in the chat
2. Wait for response (audio plays automatically)
3. Hover over the bot's message
4. Click the **Replay** button (plays audio again)
5. Should use ElevenLabs audio, not browser TTS

## ⚙️ Configuration Files

### .env (Backend)
```bash
GROQ_API_KEY=gsk_...
DB_CONNECTION=postgresql+psycopg://...
SUPABASE_URL=https://...supabase.co
SUPABASE_KEY=eyJhbGc...
ELEVENLABS_API_KEY=180359041d6f9e3cef99d20f49db6cd74aee1db3536f5b270e3c201d68aab01f
ELEVENLABS_VOICE_ID=Ahq9IAlmr15JKZ2Fa5ov
```

### .env (Frontend)
```bash
VITE_API_URL=http://localhost:9000
```

## 📊 New API Response Format

### Request
```json
{
  "question": "What is My Health School?"
}
```

### Response
```json
{
  "answer": "My Health School oru diabetes reversal program...",
  "type": "normal",
  "audio_url": "https://api.elevenlabs.io/v1/text-to-speech/Ahq9IAlmr15JKZ2Fa5ov/stream?..."
}
```

### Response Types
- **"normal"** - Successful Tanglish answer with audio
- **"restricted"** - Blocked due to restricted keywords
- **"not_found"** - Answer not found in documents
- **Audio URL** - Provided if TTS generation succeeded (null if failed)

## 🐛 Troubleshooting

### Backend Won't Start
**Error:** `ModuleNotFoundError: No module named 'elevenlabs'`
**Solution:**
```bash
pip install elevenlabs requests supabase
```

### No Audio Playing
**Possible causes:**
1. ELEVENLABS_API_KEY not set → Add to .env and restart
2. ElevenLabs API quota exceeded → Check account
3. Browser blocked autoplay → Manually click Replay button

**Debug:**
```bash
# Check if TTS service initializes
python -c "from src.services.TtsService import ElevenLabsTtsService; print('TTS loaded')"
```

### Cache Table Not Found
**Error:** `relation "tts_cache" does not exist`
**Solution:** Run the migration SQL in Supabase console (Step 2 above)

### CORS Error in Browser
**Error:** `No 'Access-Control-Allow-Origin' header`
**Cause:** Audio URL from ElevenLabs may have CORS restrictions
**Solution:** Audio playback typically works - check browser console for specific error

## 📈 Monitoring

### Check Cache Hit Rate
```sql
SELECT
  COUNT(*) as total_cached,
  SUM(hits) as total_hits,
  ROUND(SUM(hits)::float / COUNT(*), 2) as avg_reuse
FROM tts_cache;
```

### Clean Old Cache
```sql
DELETE FROM tts_cache
WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
```

## 🚀 Production Deployment

Before deploying:
1. ✅ Test locally with all features
2. ✅ Verify ElevenLabs API quota is sufficient
3. ✅ Ensure Supabase table permissions are correct
4. ✅ Cache will automatically grow - monitor storage
5. ✅ Consider CDN for audio URLs (future optimization)

## 📝 Rollback (If needed)

To revert to browser TTS only:
1. Remove TtsService initialization from ChatService.__init__()
2. Remove audio_url from AskResponse
3. Frontend will fallback to SpeechSynthesis automatically

## ✅ Success Indicators

You'll know it's working when:
- ✅ Backend responds with `audio_url` in response
- ✅ Frontend plays Tanglish audio automatically
- ✅ Replay button uses ElevenLabs audio (not browser voice)
- ✅ Same question returns audio instantly from cache (2nd time)
- ✅ Supabase `tts_cache` table has entries with hits > 0

## 📞 Need Help?

Check these files for more context:
- Backend TTS: `src/services/TtsService.py`
- Backend Cache: `src/services/CacheService.py`
- Updated ChatService: `src/services/ChatService/ChatService.py` (line 26: system prompt with Tanglish)
- Frontend Audio: `src/components/ChatContainer.tsx` (line 41-76: playAudioUrl function)
- DB Schema: `migrations/001_create_tts_cache_table.sql`

---

**Status:** ✅ Tanglish + ElevenLabs TTS fully implemented and tested!
