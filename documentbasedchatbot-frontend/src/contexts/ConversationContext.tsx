import React, { createContext, useReducer, useCallback } from 'react';
import type { ReactNode } from 'react';

export interface Message {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  audioUrl?: string;
  timestamp: number;
  type?: 'normal' | 'enrollment_form' | 'error' | 'welcome';
  isError?: boolean;
  voice_settings?: {
    stability: number;
    similarity_boost: number;
    style: number;
    use_speaker_boost: boolean;
  };
  emotion?: string;
}

export interface ConversationContextType {
  messages: Message[];
  isLoading: boolean;
  language: 'en' | 'ta';
  askQuestion: (question: string, mode?: string) => Promise<void>;
  setLanguage: (lang: 'en' | 'ta') => void;
  clearMessages: () => void;
  /** Increments each time the enrollment form should be shown — pages respond locally */
  enrollmentFormCount: number;
  /** True after user submits or cancels - prevents form from showing again */
  enrollmentSubmitted: boolean;
  setEnrollmentSubmitted: (submitted: boolean) => void;
  /** True after user explicitly dismisses form — prevents effect re-triggering on page switch */
  enrollmentCancelled: boolean;
  setEnrollmentCancelled: (cancelled: boolean) => void;
  /** Called after form is successfully submitted — dispatches thank-you bot message with static audio */
  handleEnrollmentSubmitted: () => void;
  /** Number of questions answered so far (resets on new chat) */
  questionCount: number;
  /** Track which message IDs have already been played — shared across Chat and Avatar pages */
  hasPlayed: (id: string) => boolean;
  markPlayed: (id: string) => void;
  /** Shared audio — persists across page navigation so audio keeps playing when switching pages */
  isSpeaking: boolean;
  stopAudio: () => void;
  playVoice: (text: string, audioUrl?: string, voiceSettings?: any, emotionLabel?: string) => Promise<void>;
}

const ConversationContext = createContext<ConversationContextType | undefined>(undefined);

type ConversationAction =
  | { type: 'ADD_USER_MESSAGE'; payload: Message }
  | { type: 'ADD_BOT_MESSAGE'; payload: Message }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_LANGUAGE'; payload: 'en' | 'ta' }
  | { type: 'CLEAR_MESSAGES' }
  | { type: 'LOAD_FROM_STORAGE'; payload: Message[] }
  | { type: 'INCREMENT_QUESTION_COUNT' };

interface ConversationState {
  messages: Message[];
  isLoading: boolean;
  language: 'en' | 'ta';
  questionCount: number;
}

const initialState: ConversationState = {
  messages: [],
  isLoading: false,
  language: 'ta',
  questionCount: 0,
};

function conversationReducer(state: ConversationState, action: ConversationAction): ConversationState {
  switch (action.type) {
    case 'ADD_USER_MESSAGE':
      return { ...state, messages: [...state.messages, action.payload] };
    case 'ADD_BOT_MESSAGE':
      return { ...state, messages: [...state.messages, action.payload] };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_LANGUAGE':
      return { ...state, language: action.payload };
    case 'CLEAR_MESSAGES':
      return { ...state, messages: [], questionCount: 0 };
    case 'LOAD_FROM_STORAGE':
      return {
        ...state,
        messages: action.payload,
        questionCount: action.payload.filter(m => m.sender === 'bot' && m.type === 'normal').length,
      };
    case 'INCREMENT_QUESTION_COUNT':
      return { ...state, questionCount: state.questionCount + 1 };
    default:
      return state;
  }
}

// Backend URL — trim() removes the trailing newline that Render/Vercel sometimes injects into env vars
const BACKEND_URL = ((import.meta as any).env?.VITE_API_URL || 'http://localhost:8000').trim();

// Helper: clear all enrollment-related localStorage keys
function clearEnrollmentStorage() {
  try {
    localStorage.removeItem('enrollment_submitted');
  } catch {}
}

// Load static audio cache from localStorage synchronously (used for enrollment audio)
function loadStaticAudioCache(): Record<string, string> {
  try {
    const cached = localStorage.getItem('static_audio_cache');
    return cached ? JSON.parse(cached) : {};
  } catch { return {}; }
}

export const ConversationProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(conversationReducer, initialState);

  // Cache for pre-recorded static audio (base64 mp3) — used for enrollment messages
  const staticAudioRef = React.useRef<Record<string, string>>(loadStaticAudioCache());

  // Shared set of already-played message IDs — prevents replay when switching Chat ↔ Avatar pages
  const playedMessageIdsRef = React.useRef<Set<string>>(new Set());
  const hasPlayed = React.useCallback((id: string) => playedMessageIdsRef.current.has(id), []);
  const markPlayed = React.useCallback((id: string) => { playedMessageIdsRef.current.add(id); }, []);

  // ─── Shared Audio — single Audio element that survives page navigation ───────
  const audioRef = React.useRef<HTMLAudioElement | null>(null);
  const [isSpeaking, setIsSpeaking] = React.useState(false);
  // Stores the src URL of audio blocked by autoplay policy — replayed on first user gesture
  const iosBlockedSrcRef = React.useRef<string | null>(null);

  React.useEffect(() => {
    audioRef.current = new Audio();
    return () => { audioRef.current?.pause(); };
  }, []);

  // On first user tap/click, play any audio that was blocked by autoplay policy
  React.useEffect(() => {
    const unlock = () => {
      if (!audioRef.current) return;
      const pendingSrc = iosBlockedSrcRef.current;
      if (!pendingSrc) return;

      const audio = audioRef.current;
      iosBlockedSrcRef.current = null;

      audio.pause();
      audio.onplay = null;
      audio.onended = null;
      audio.onerror = null;
      audio.src = pendingSrc;
      audio.onplay = () => setIsSpeaking(true);
      audio.onended = () => { setIsSpeaking(false); if (pendingSrc.startsWith('blob:')) URL.revokeObjectURL(pendingSrc); };
      audio.onerror = () => { setIsSpeaking(false); if (pendingSrc.startsWith('blob:')) URL.revokeObjectURL(pendingSrc); };
      audio.play().catch(() => setIsSpeaking(false));

      document.removeEventListener('touchstart', unlock, true);
      document.removeEventListener('click', unlock, true);
    };

    document.addEventListener('touchstart', unlock, { capture: true, passive: true });
    document.addEventListener('click', unlock, { capture: true, passive: true });
    return () => {
      document.removeEventListener('touchstart', unlock, true);
      document.removeEventListener('click', unlock, true);
    };
  }, []);

  const stopAudio = React.useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setIsSpeaking(false);
  }, []);

  const playVoice = React.useCallback(async (
    text: string,
    audioUrl?: string,
    voiceSettings?: any,
    emotionLabel?: string
  ) => {
    if (!audioUrl || !audioRef.current) return;
    const audio = audioRef.current;

    audio.pause();
    audio.currentTime = 0;
    audio.onended = null;
    audio.onerror = null;
    audio.onplay = null;

    const isStaticAudio = audioUrl.startsWith('data:audio') || /\.(mp3|wav|ogg|aac)(\?|$)/i.test(audioUrl);
    if (isStaticAudio) {
      audio.src = audioUrl;
      audio.muted = false;
      audio.onplay = () => setIsSpeaking(true);
      audio.onended = () => setIsSpeaking(false);
      audio.onerror = () => setIsSpeaking(false);

      // Strategy 1: normal play (works after any prior user gesture)
      audio.play().catch(() => {
        // Strategy 2: muted autoplay then immediately unmute
        audio.muted = true;
        audio.play().then(() => {
          audio.muted = false;
        }).catch(() => {
          // Strategy 3: queue for first user gesture (iOS Safari strict mode)
          audio.muted = false;
          iosBlockedSrcRef.current = audioUrl;
        });
      });
      return;
    }

    // Dynamic TTS via ElevenLabs backend
    try {
      const payload: any = { text, language: state.language };
      if (voiceSettings) { payload.voice_settings = voiceSettings; payload.emotion_label = emotionLabel; }

      const ttsController = new AbortController();
      const ttsTimeout = setTimeout(() => ttsController.abort(), 30000);
      const response = await fetch(`${BACKEND_URL}/tts/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: ttsController.signal,
      });
      clearTimeout(ttsTimeout);
      if (!response.ok) throw new Error(`TTS failed: ${response.statusText}`);

      const blobUrl = URL.createObjectURL(await response.blob());
      if (!audioRef.current || audioRef.current !== audio) return;
      audio.src = blobUrl;
      audio.onplay = () => setIsSpeaking(true);
      audio.onended = () => { setIsSpeaking(false); URL.revokeObjectURL(blobUrl); };
      audio.onerror = () => { setIsSpeaking(false); URL.revokeObjectURL(blobUrl); };

      // Strategy 1: normal play
      audio.play().catch(() => {
        // Strategy 2: muted play then immediately unmute
        audio.muted = true;
        audio.play().then(() => {
          audio.muted = false;
        }).catch(() => {
          // Strategy 3: queue for first user gesture
          audio.muted = false;
          iosBlockedSrcRef.current = blobUrl;
        });
      });
    } catch (err) {
      console.error('Error generating/playing audio:', err);
      setIsSpeaking(false);
    }
  }, [state.language]);

  const [enrollmentFormCount, setEnrollmentFormCount] = React.useState(0);
  const [enrollmentSubmitted, setEnrollmentSubmitted] = React.useState(false);
  const [enrollmentCancelled, setEnrollmentCancelled] = React.useState(false);

  // On mount: restore previous session silently (no welcome message, no prompt)
  React.useEffect(() => {
    const stored = localStorage.getItem('conversation_messages');
    const storedLang = localStorage.getItem('conversation_language') as 'en' | 'ta' | null;
    const wasEnrolled = localStorage.getItem('enrollment_submitted') === 'true';

    if (stored) {
      try {
        const messages: Message[] = JSON.parse(stored);
        // Filter out any old welcome messages — we no longer show them
        const realMessages = messages.filter(m => m.type !== 'welcome');
        if (realMessages.length > 0) {
          setEnrollmentSubmitted(wasEnrolled);
          dispatch({ type: 'LOAD_FROM_STORAGE', payload: realMessages });
        }
      } catch {
        clearEnrollmentStorage();
      }
    }

    if (storedLang) {
      dispatch({ type: 'SET_LANGUAGE', payload: storedLang });
    }
  }, []);

  // Refresh pre-recorded static audio from backend (used for enrollment messages)
  React.useEffect(() => {
    fetch(`${BACKEND_URL}/admin/static-audio`)
      .then(r => r.json())
      .then(data => {
        if (data?.audio && Object.keys(data.audio).length > 0) {
          staticAudioRef.current = data.audio;
          localStorage.setItem('static_audio_cache', JSON.stringify(data.audio));
        }
      })
      .catch(() => {});
  }, []);

  // Persist state to localStorage
  React.useEffect(() => {
    try {
      localStorage.setItem('enrollment_submitted', String(enrollmentSubmitted));
    } catch {}
  }, [enrollmentSubmitted]);

  React.useEffect(() => {
    try {
      localStorage.setItem('conversation_messages', JSON.stringify(state.messages));
    } catch {}
  }, [state.messages]);

  React.useEffect(() => {
    try {
      localStorage.setItem('conversation_language', state.language);
    } catch {}
  }, [state.language]);

  const MAX_FREE_QUESTIONS = 4;

  // Helper: get a static audio data URL (or undefined if not cached yet)
  const getStaticAudioUrl = (key: string): string | undefined => {
    const b64 = staticAudioRef.current[key];
    return b64 ? `data:audio/mp3;base64,${b64}` : undefined;
  };

  // Called after enrollment form is successfully submitted
  const handleEnrollmentSubmitted = useCallback(() => {
    setEnrollmentSubmitted(true);
    const thankText = state.language === 'ta'
      ? 'நன்றி! எங்க team விரைவில் உங்களை contact பண்ணி, உங்க health journey-ஐ guide பண்ணுவாங்க!'
      : 'Thank you for registering! Our team will contact you soon to guide your health journey!';
    const audioKey = state.language === 'ta' ? 'post_enrollment_ta' : 'post_enrollment_en';
    setTimeout(() => {
      dispatch({
        type: 'ADD_BOT_MESSAGE', payload: {
          id: Date.now().toString(),
          sender: 'bot',
          text: thankText,
          audioUrl: getStaticAudioUrl(audioKey),
          timestamp: Date.now(),
          type: 'normal',
        }
      });
    }, 300);
  }, [state.language]);

  const askQuestion = useCallback(async (question: string, mode: string = 'health') => {
    if (!question.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: question,
      timestamp: Date.now(),
    };
    dispatch({ type: 'ADD_USER_MESSAGE', payload: userMessage });

    // If user already submitted the form → static "thank you" reply
    if (enrollmentSubmitted) {
      const postText = state.language === 'ta'
        ? 'நன்றி! எங்க team விரைவில் உங்களை contact பண்ணி உங்க கேள்விகளுக்கு பதில் சொல்வாங்க!'
        : 'Thank you! Our team will contact you soon and answer all your questions!';
      const audioKey = state.language === 'ta' ? 'post_enrollment_ta' : 'post_enrollment_en';
      setTimeout(() => {
        dispatch({
          type: 'ADD_BOT_MESSAGE', payload: {
            id: (Date.now() + 1).toString(),
            sender: 'bot',
            text: postText,
            audioUrl: getStaticAudioUrl(audioKey),
            timestamp: Date.now(),
            type: 'normal',
          }
        });
      }, 300);
      return;
    }

    // After 4 free questions — show enrollment form
    if (state.questionCount >= MAX_FREE_QUESTIONS) {
      const promptText = state.language === 'ta'
        ? 'உங்களுக்கு மேலும் உதவ எங்கள் team ஆர்வமாக இருக்கிறது. கீழே உள்ள form-ஐ fill பண்ணுங்க!'
        : 'Our team would love to help you further. Please fill in the form below!';
      const audioKey = state.language === 'ta' ? 'enrollment_prompt_ta' : 'enrollment_prompt_en';
      if (enrollmentCancelled) setEnrollmentCancelled(false);
      setTimeout(() => {
        dispatch({
          type: 'ADD_BOT_MESSAGE', payload: {
            id: (Date.now() + 1).toString(),
            sender: 'bot',
            text: promptText,
            audioUrl: getStaticAudioUrl(audioKey) || 'audio_enabled',
            timestamp: Date.now(),
            type: 'normal',
          }
        });
        setEnrollmentFormCount(c => c + 1);
      }, 300);
      return;
    }

    dispatch({ type: 'SET_LOADING', payload: true });

    // iOS Safari: AbortController enforces a 45-second timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000);

    try {
      const response = await fetch(`${BACKEND_URL}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          mode,
          language: state.language,
        }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const result = await response.json();

      let resolvedType: Message['type'] =
        result.type === 'error' ? 'error' : (result.type as Message['type']) || 'normal';
      if (result.type === 'enrollment_form' && state.questionCount < MAX_FREE_QUESTIONS) {
        resolvedType = 'normal';
      }

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'bot',
        text: result.answer,
        audioUrl: result.audio_url,
        timestamp: Date.now(),
        type: resolvedType,
        isError: result.type === 'error',
        voice_settings: result.voice_settings,
        emotion: result.emotion,
      };
      dispatch({ type: 'ADD_BOT_MESSAGE', payload: botMessage });

      if (result.type !== 'error') {
        dispatch({ type: 'INCREMENT_QUESTION_COUNT' });
      }
    } catch (error: any) {
      clearTimeout(timeoutId);
      console.error('Error asking question:', error);
      const isTimeout = error?.name === 'AbortError';
      const isNetworkError = error?.message === 'Failed to fetch' || error?.message === 'Network request failed';
      const errorText = isTimeout
        ? 'The request took too long. Please check your internet connection and try again.'
        : isNetworkError
          ? 'Cannot reach the server. Please check your internet connection and try again.'
          : 'Sorry, there was an error processing your question. Please try again.';
      dispatch({
        type: 'ADD_BOT_MESSAGE', payload: {
          id: (Date.now() + 1).toString(),
          sender: 'bot',
          text: errorText,
          timestamp: Date.now(),
          type: 'error',
          isError: true,
        }
      });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, [state.language, state.questionCount, enrollmentSubmitted, enrollmentCancelled]);

  const setLanguage = useCallback((lang: 'en' | 'ta') => {
    dispatch({ type: 'SET_LANGUAGE', payload: lang });
  }, []);

  // clearMessages resets everything and starts a completely blank chat
  const clearMessages = useCallback(() => {
    dispatch({ type: 'CLEAR_MESSAGES' });
    setEnrollmentSubmitted(false);
    setEnrollmentCancelled(false);
    clearEnrollmentStorage();
    localStorage.removeItem('conversation_messages');
  }, []);

  const value: ConversationContextType = {
    messages: state.messages,
    isLoading: state.isLoading,
    language: state.language,
    askQuestion,
    setLanguage,
    clearMessages,
    enrollmentFormCount,
    enrollmentSubmitted,
    setEnrollmentSubmitted,
    enrollmentCancelled,
    setEnrollmentCancelled,
    handleEnrollmentSubmitted,
    questionCount: state.questionCount,
    hasPlayed,
    markPlayed,
    isSpeaking,
    stopAudio,
    playVoice,
  };

  return (
    <ConversationContext.Provider value={value}>
      {children}
    </ConversationContext.Provider>
  );
};

export const useConversation = () => {
  const context = React.useContext(ConversationContext);
  if (!context) {
    throw new Error('useConversation must be used within ConversationProvider');
  }
  return context;
};
