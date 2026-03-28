# ElevenLabs Emotional Tags Guide - Natural Voice Implementation

## 📋 Your Setup
- **Voice ID**: `LRD0hRe2gcPcdv3SjlOn` ✅ (Updated)
- **Model**: `eleven_turbo_v2_5` (Latest - recommended for natural speech)
- **Voice Settings**:
  - **Stability**: 0.65 (Natural but stable)
  - **Similarity Boost**: 0.80 (High consistency with your voice)
  - **Style**: 0.45 (Slight expressiveness)
  - **Speaker Boost**: Enabled (Clarity enhancement)

---

## 🎭 Emotional Tags for Natural Speech

### 1. **Emotion Tags**
Add emotional context to specific words or phrases:

```xml
<emotion name="friendly">Hi there, how can I help you today?</emotion>
<emotion name="professional">According to our analysis, here are the findings.</emotion>
<emotion name="warm">Thank you so much for your question!</emotion>
<emotion name="conversational">So, what you're really asking is...</emotion>
```

**Available emotions**:
- `friendly` - Warm, approachable
- `professional` - Formal, business-like
- `warm` - Kind, caring, gentle
- `conversational` - Casual, natural dialogue
- `confident` - Assured, strong

### 2. **Emphasis Tags**
Emphasize important words:

```xml
<emphasis level="high">This is very important</emphasis>
<emphasis level="medium">This matters too</emphasis>
<emphasis level="low">This is supplementary</emphasis>
```

### 3. **Break Tags**
Add pauses for better pacing:

```xml
This is important.<break time="500ms"/> Now let's continue.
First point:<break time="300ms"/> Second point.
```

**Timing guidelines**:
- `300ms` - Short pause (comma-like)
- `500ms` - Medium pause (period-like)
- `800ms` - Long pause (topic transition)

### 4. **Phoneme Tags**
Control pronunciation:

```xml
<phoneme alphabet="ipa" ph="təˈmɑːtoʊ">tomato</phoneme>
```

---

## 🎯 Example Scripts with Emotional Tags

### Example 1: Friendly Greeting
```xml
<emotion name="warm">Hello there!</emotion>
<emotion name="friendly">I'm your AI assistant.</emotion>
<break time="300ms"/>
<emphasis level="medium">How can I help you today?</emphasis>
```

### Example 2: Professional Answer
```xml
<emotion name="professional">Based on your question,</emotion>
<break time="300ms"/>
<emphasis level="high">here's what I found:</emphasis>
<break time="500ms"/>
[Your answer content]
```

### Example 3: Conversational Response
```xml
<emotion name="conversational">So you're asking about</emotion>
<emphasis level="medium">this topic</emphasis>,
<break time="300ms"/>
<emotion name="friendly">let me explain it simply.</emotion>
```

### Example 4: Error/Apologetic
```xml
<emotion name="warm">I apologize,</emotion>
<break time="300ms"/>
<emotion name="friendly">but I couldn't find information about that.</emotion>
<break time="500ms"/>
<emotion name="conversational">Would you like to try a different question?</emotion>
```

---

## 🔧 Implementation in Your Chatbot

The system automatically adds emotional tags to responses:

### Current Auto-Tags Applied:
1. **Questions** (`?`) - Added emphasis
2. **Commas** (`, `) - Added 500ms pauses
3. **Colons** (`: `) - Added 300ms pauses
4. **Help phrases** - Added friendly emotion

### Example Output:
**Input**: `Hello, how can I help you today?`
**Output with tags**:
```xml
<emotion name="friendly">Hello</emotion>,
<break time="500ms"/>
<emotion name="friendly">how can I help</emotion>
you today? <emphasis level="high">
```

---

## 📊 Voice Setting Recommendations

### For Different Scenarios:

**Calm & Professional**
```json
{
  "stability": 0.75,
  "similarity_boost": 0.85,
  "style": 0.30
}
```

**Natural & Conversational**
```json
{
  "stability": 0.65,
  "similarity_boost": 0.80,
  "style": 0.45
}
```

**Energetic & Expressive**
```json
{
  "stability": 0.55,
  "similarity_boost": 0.75,
  "style": 0.60
}
```

**Clear & Articulate**
```json
{
  "stability": 0.70,
  "similarity_boost": 0.90,
  "style": 0.40,
  "use_speaker_boost": true
}
```

---

## 🎬 Testing Your Voice

### Test Script 1 (Friendly):
```
Hi! I'm here to help answer your questions about any topic. Feel free to ask me anything, and I'll do my best to provide you with accurate and helpful information.
```

### Test Script 2 (Professional):
```
Thank you for your inquiry. Based on my analysis, I can provide you with comprehensive information on this subject. Please allow me to explain the key points.
```

### Test Script 3 (Conversational):
```
So you want to know about this? Great question! Let me break it down for you in a way that's easy to understand. Here's what you need to know.
```

---

## 🚀 Using in Your Chatbot

Your chatbot now automatically:
1. ✅ Detects response type
2. ✅ Adds emotional tags for warmth
3. ✅ Inserts pauses for natural pacing
4. ✅ Emphasizes important information
5. ✅ Uses optimal voice settings for your voice ID

**No manual intervention needed!** The backend processes all responses automatically.

---

## 📝 Custom Prompt Enhancement

If you want to add specific emotional tags to chatbot responses, update the prompt in `WebSearchChatService.py`:

```python
prompt = """
You are a helpful AI assistant that searches the web and answers questions.

[Your instructions]

When responding:
- Be warm and friendly
- Use clear, natural language
- Emphasize key points
- Break complex information into digestible parts
"""
```

---

## 🎵 Advanced: Custom Emotional Phrases

Add these to responses for maximum naturalness:

- `"<emotion name=\"warm\">Of course!</emotion>"` - For confirmations
- `"<break time=\"500ms\"/>"` - After important statements
- `"<emphasis level=\"high\">this is crucial</emphasis>"` - For emphasis
- `"<emotion name=\"friendly\">Hope that helps!</emotion>"` - For closings

---

## ⚙️ Current Configuration

Your system is configured in:
- **Backend**: `src/services/TtsService.py`
- **Controller**: `src/controller/chat_controller.py`
- **.env**: Voice ID `LRD0hRe2gcPcdv3SjlOn`

All emotional tags and voice settings are applied automatically to every bot response!

---

## 🎯 Results You'll Get

✅ More natural-sounding responses
✅ Better emotional connection with users
✅ Clearer speech with proper pacing
✅ Professional yet friendly tone
✅ Consistent voice quality

Try asking your chatbot a question now to hear the emotional tags in action! 🎤
