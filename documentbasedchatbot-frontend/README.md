# Document-Based Q&A Voice Chatbot Frontend

This is the React frontend for the Document-Based Q&A Chatbot. It provides a clean, modern, and interactive interface allowing users to ask questions purely via text or voice, and receive textual as well as spoken responses from the backend AI (powered by Groq Llama 3).

## 🚀 Features
- **Voice Input (STT)**: Allows users to speak their questions using the browser's native `SpeechRecognition` API.
- **Voice Output (TTS)**: Automatically reads out the bot's responses using the `speechSynthesis` API. Replay buttons exist on past messages.
- **Real-time API Integration**: Connects dynamically to the Python FastAPI backend (`/ask` endpoint).
- **Graceful Error Handling**: Captures backend API limits and connection issues to present them smoothly to the user.
- **Beautiful UI**: Uses TailwindCSS for a sleek, responsive, and polished chat interface interface with fluid animations.

## 🛠️ Tech Stack
- **Framework**: React 18 + TypeScript
- **Bundler**: Vite
- **Styling**: Tailwind CSS
- **Voice Integration**: Native Browser Web Speech APIs

## ⚙️ Setup Instructions

### 1. Prerequisites
- Node.js (v18 or higher)
- Ensure the **FastAPI Backend** is running locally on `http://localhost:8000`.

### 2. Install Dependencies
Navigate into the frontend project directory and run:
```bash
npm install
```

### 3. Run the Development Server
Start the Vite development server:
```bash
npm run dev
```

### 4. Access the App
Open your browser and navigate to the URL provided by Vite (typically `http://localhost:5173`).

---

## 🏗️ Project Architecture

```
src/
├── components/
│   ├── ChatContainer.tsx   # Main orchestrator (handles state, API calls, and TTS)
│   ├── ChatMessage.tsx     # Renders individual chat bubbles (user/bot styling)
│   ├── TextInput.tsx       # Text input form
│   └── VoiceInput.tsx      # Microphone toggle for STT
├── services/
│   └── apiService.ts       # Centralized fetch logic connecting to backend
├── App.tsx                 # Root component layout and styling
└── main.tsx                # React DOM entry point
```

## ⚠️ Browser Compatibility Note
- **Voice Input / Output**: The Web Speech API is widely supported, but for the most native and accurate experience, **Google Chrome** or **Microsoft Edge** is recommended. Some features may not work as expected in Firefox or Safari due to aggressive audio-autoplay policies.
