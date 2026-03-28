# Emotional Voice Generation System

## Overview

The chatbot now includes an **Emotional Voice Generation System** that analyzes response content and applies emotion-specific voice settings to ElevenLabs text-to-speech generation. This creates more expressive, natural-sounding responses that match the tone and context of the answer.

## Architecture

### System Flow

```
Backend Response
    ↓
Emotion Detection
    ↓
Voice Settings Mapping
    ↓
Frontend Receives (emotion_label, voice_settings)
    ↓
TTS Endpoint with Emotional Parameters
    ↓
Expressive Audio Output
```

## Components

### 1. Backend: Emotion Detection (`HealthChatService.py`)

#### Emotion Keywords Dictionary
Maps five emotion types to trigger keywords:

```python
EMOTION_KEYWORDS = {
    'empathetic': ['understand', 'sorry', 'concerned', 'care', 'help you', 'pain', 'suffer', 'difficult', 'challenge'],
    'encouraging': ['great', 'excellent', 'wonderful', 'success', 'improve', 'healthy', 'strong', 'confident', 'achieve'],
    'informative': ['research shows', 'studies', 'evidence', 'according', 'findings', 'clinical', 'data', 'proven'],
    'conversational': ['let me', 'think about', 'consider', 'perhaps', 'likely', 'you might', 'could be'],
    'professional': ['treatment', 'medication', 'consult', 'doctor', 'medical', 'condition', 'diagnosis', 'therapy']
}
```

#### Function: `detect_emotion_and_get_settings(text)`

Analyzes response text and returns:
1. **emotion_type**: Key for emotion dictionary
2. **emotion_label**: Display label with emoji (e.g., "🤝 Empathetic")
3. **voice_settings**: ElevenLabs-compatible settings dict

**Algorithm:**
1. Count keyword occurrences in response (case-insensitive)
2. Select emotion with highest score
3. Default to 'conversational' if no keywords found
4. Map emotion to voice parameters

### 2. Voice Settings Mapping

Each emotion type maps to optimized ElevenLabs parameters:

#### 🤝 **Empathetic** (Warm, Understanding)
```python
{
    'stability': 0.35,        # Lower = more emotion variation
    'similarity_boost': 0.80,  # Natural but warm
    'style': 0.85,             # High emotional expression
    'use_speaker_boost': True
}
```
**Use case**: Responses about pain, suffering, challenges, or care

---

#### ✨ **Encouraging** (Uplifting, Confident)
```python
{
    'stability': 0.50,        # Balanced emotion
    'similarity_boost': 0.90,  # Confident delivery
    'style': 0.95,             # Maximum enthusiasm
    'use_speaker_boost': True
}
```
**Use case**: Positive health outcomes, improvements, success stories

---

#### 📊 **Informative** (Clear, Technical)
```python
{
    'stability': 0.65,        # Higher = clear, less emotional
    'similarity_boost': 0.85,  # Natural clarity
    'style': 0.75,             # Moderate expression
    'use_speaker_boost': True
}
```
**Use case**: Research, clinical data, evidence-based information

---

#### 💬 **Conversational** (Natural, Friendly) [DEFAULT]
```python
{
    'stability': 0.45,        # Natural flow
    'similarity_boost': 0.80,  # Natural quality
    'style': 0.80,             # Good engagement
    'use_speaker_boost': True
}
```
**Use case**: General advice, explanations, casual responses

---

#### 👨‍⚕️ **Professional** (Authoritative, Formal)
```python
{
    'stability': 0.70,        # High clarity
    'similarity_boost': 0.90,  # Confident authority
    'style': 0.70,             # Formal tone
    'use_speaker_boost': True
}
```
**Use case**: Medical advice, diagnosis, professional recommendations

### 3. Backend Changes

#### `ask_question()` Method
- Detects emotion from generated answer
- Logs emotion with score
- Returns response with:
  - `emotion`: Emotion label (e.g., "🤝 Empathetic")
  - `voice_settings`: Dict of TTS parameters
  - `answer`: The response text
  - `type`: Response type (normal, enrollment_form, error)

#### `/tts/generate` Endpoint
- Accepts optional `voice_settings` parameter
- Accepts optional `emotion_label` parameter
- Logs emotion information: `"📢 TTS generation (Empathetic): Stability=0.35, Style=0.85, Similarity=0.80"`
- Uses provided settings or defaults

### 4. Frontend Integration

#### `ConversationContext.tsx` Updates
Message interface now includes:
```typescript
interface Message {
  // ... existing fields
  voice_settings?: {
    stability: number;
    similarity_boost: number;
    style: number;
    use_speaker_boost: boolean;
  };
  emotion?: string;
}
```

#### `ChatContainer.tsx` Updates
- `playAudioUrl(text, voiceSettings?, emotionLabel?)` now accepts emotional parameters
- `playVoice(text, audioUrl?, voiceSettings?, emotionLabel?)` passes settings through
- Auto-play effect extracts and uses voice_settings from message

#### `AvatarPage.tsx` Updates
- Same updates as ChatContainer
- Emotion-aware voice parameters passed during auto-play
- Logs: `"🎭 Avatar TTS - Sending emotional voice settings: Encouraging"`

#### TTS Request Enhancement
```typescript
const ttsPayload = {
  text: answerText,
  voice_settings: {
    stability: 0.85,
    similarity_boost: 0.90,
    style: 0.95,
    use_speaker_boost: true
  },
  emotion_label: "✨ Encouraging"
};
```

## Data Flow Example

### User asks: "How can I improve my diabetes control?"

**Backend Processing:**
1. Generates answer with positive keywords: "excellent", "improve", "healthy"
2. Emotion detection scores:
   - encouraging: 3 ✅ (highest)
   - conversational: 1
   - others: 0
3. Returns response:
   ```json
   {
     "answer": "You can achieve excellent results by...",
     "emotion": "✨ Encouraging",
     "voice_settings": {
       "stability": 0.50,
       "similarity_boost": 0.90,
       "style": 0.95,
       "use_speaker_boost": true
     },
     "type": "normal"
   }
   ```

**Frontend Processing:**
1. Stores emotion & voice_settings in message
2. Triggers auto-play with: `playVoice(answer, 'audio_enabled', voice_settings, emotion)`
3. Sends to TTS endpoint:
   ```json
   {
     "text": "You can achieve excellent results by...",
     "voice_settings": { ... },
     "emotion_label": "✨ Encouraging"
   }
   ```

**Voice Output:**
- High enthusiasm (style: 0.95)
- Confident delivery (similarity_boost: 0.90)
- Natural flow (stability: 0.50)
- Result: Uplifting, encouraging tone ✨

## Logging

### Backend Logs
```
🎭 Detected emotion: ✨ Encouraging (Score: 3)
📢 🤝 Empathetic - Calling ElevenLabs TTS: Your concerns are important...
✅ TTS audio generated successfully with 🤝 Empathetic voice
```

### Frontend Logs
```
🎭 Sending emotional voice settings: ✨ Encouraging {stability: 0.50, ...}
🎭 Avatar TTS - Sending emotional voice settings: 📊 Informative {...}
```

## Benefits

✅ **More Natural Speech**: Voice tone matches content meaning
✅ **Better User Experience**: Emotional connection improves engagement
✅ **Context-Aware**: Same voice settings for similar content types
✅ **Flexible Fallback**: Defaults to conversational if no keywords match
✅ **Easy to Extend**: Add new emotions by adding keywords + settings

## Customization

### Adding New Emotion

1. Add keywords to `EMOTION_KEYWORDS`:
   ```python
   EMOTION_KEYWORDS['grateful'] = ['thank you', 'grateful', 'appreciation', ...]
   ```

2. Add voice settings in `detect_emotion_and_get_settings()`:
   ```python
   'grateful': {
       'stability': 0.40,
       'similarity_boost': 0.85,
       'style': 0.90,
       'use_speaker_boost': True,
       'emotion_label': '🙏 Grateful'
   }
   ```

### Adjusting Voice Parameters

Fine-tune parameters for your voice preference:
- **stability**: 0.0-1.0 (lower = more emotion, higher = clarity)
- **similarity_boost**: 0.0-1.0 (higher = closer to original voice)
- **style**: 0.0-1.0 (higher = more style/emotion expression)
- **use_speaker_boost**: True/False (adds speaker characteristics)

## Testing

### Manual Test Cases

1. **Test Empathetic Tone**
   - Ask: "I'm struggling with my health"
   - Expect: Warm, caring voice 🤝

2. **Test Encouraging Tone**
   - Ask: "Can I improve my health?"
   - Expect: Uplifting, confident voice ✨

3. **Test Informative Tone**
   - Ask: "What does research show?"
   - Expect: Clear, professional voice 📊

4. **Test Default (Conversational)**
   - Ask: "Hello"
   - Expect: Friendly, natural voice 💬

## Performance Notes

- Emotion detection: <5ms (keyword matching only)
- No additional API calls required
- Voice parameter adjustment: Zero latency
- Compatible with existing TTS infrastructure

## Future Enhancements

🔮 **Sentiment Analysis**: Use ML/NLP for more accurate emotion detection
🔮 **User Preferences**: Allow users to select preferred emotion/voice
🔮 **Context Memory**: Track conversation tone across multiple messages
🔮 **Language-Specific**: Different keywords for Tamil/English responses
🔮 **A/B Testing**: Measure engagement with different voice settings

---

**Implementation Date**: March 2026
**Author**: Claude Code AI Assistant
**Status**: ✅ Complete and Integrated
