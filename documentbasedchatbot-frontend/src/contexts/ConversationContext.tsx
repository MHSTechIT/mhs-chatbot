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
  /** true when audio is queued but blocked by autoplay policy — show "Tap to hear" hint */
  hasPendingAudio: boolean;
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
        // Count only real AI answers (type='normal') — exclude enrollment prompts and errors
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

// The fixed Tamil greeting played at the start of every fresh chat
const WELCOME_TEXT = 'சக்கரை நோய் பற்றி உங்களுக்கு ஏதாவது கேள்விகள் இருந்தால், தயங்காம கேளுங்கள்.';

// Helper: clear all enrollment-related localStorage keys
function clearEnrollmentStorage() {
  try {
    localStorage.removeItem('enrollment_submitted');
  } catch {}
}

// Load static audio cache from localStorage synchronously (module-level, called once per mount)
function loadStaticAudioCache(): Record<string, string> {
  try {
    const cached = localStorage.getItem('static_audio_cache');
    return cached ? JSON.parse(cached) : {};
  } catch { return {}; }
}

export const ConversationProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(conversationReducer, initialState);
  const [showResumePrompt, setShowResumePrompt] = React.useState(false);
  const pendingMessagesRef = React.useRef<Message[]>([]);
  // Cache for pre-recorded static audio (base64 mp3) — avoids ElevenLabs API calls for fixed messages
  // Loaded from localStorage SYNCHRONOUSLY so welcome audio is available before any effect fires
  const staticAudioRef = React.useRef<Record<string, string>>(loadStaticAudioCache());

  // Shared set of already-played message IDs — prevents replay when switching Chat ↔ Avatar pages
  const playedMessageIdsRef = React.useRef<Set<string>>(new Set());
  const hasPlayed = React.useCallback((id: string) => playedMessageIdsRef.current.has(id), []);
  const markPlayed = React.useCallback((id: string) => { playedMessageIdsRef.current.add(id); }, []);

  // Dispatch the Tamil welcome message as the first bot message on fresh/new chats.
  // Uses the base64 from localStorage cache if warm, else the static MP3 bundled with
  // the Vercel deploy (/audio/welcome_ta.mp3). Either way: zero ElevenLabs credits.
  const dispatchWelcome = React.useCallback(() => {
    const b64 = staticAudioRef.current['welcome_ta'];
    // b64 cache hit = instant playback; fallback = bundled static MP3 (fetched from Vercel)
    const audioUrl = b64 ? `data:audio/mp3;base64,${b64}` : '/audio/welcome_ta.mp3';
    dispatch({
      type: 'ADD_BOT_MESSAGE', payload: {
        id: Date.now().toString(),
        sender: 'bot',
        text: WELCOME_TEXT,
        audioUrl,
        timestamp: Date.now(),
        type: 'welcome',
      }
    });
  }, []);

  // ─── Shared Audio — single Audio element that survives page navigation ───────
  const audioRef = React.useRef<HTMLAudioElement | null>(null);
  const [isSpeaking, setIsSpeaking] = React.useState(false);
  // true when audio is queued but waiting for first user gesture (autoplay blocked)
  const [hasPendingAudio, setHasPendingAudio] = React.useState(false);
  // iOS: stores the blob/data URL of audio that was blocked before user interaction
  const iosBlockedSrcRef = React.useRef<string | null>(null);

  React.useEffect(() => {
    audioRef.current = new Audio();
    return () => { audioRef.current?.pause(); };
  }, []);

  // Browsers block audio.play() without a prior user gesture.
  // When play() is blocked, we store the src in iosBlockedSrcRef and keep
  // click/touchstart listeners alive. On the next user gesture we directly
  // call audio.play() — no silent-WAV intermediary that can be interrupted
  // by other click handlers (e.g. mic button calling stopAudio()).
  React.useEffect(() => {
    const unlock = () => {
      if (!audioRef.current) return;
      const pendingSrc = iosBlockedSrcRef.current;
      if (!pendingSrc) return; // Nothing queued yet — keep listener alive

      const audio = audioRef.current;
      iosBlockedSrcRef.current = null;

      // Re-set src (audio.src may have changed if another message arrived)
      audio.pause();
      audio.onplay = null;
      audio.onended = null;
      audio.onerror = null;
      audio.src = pendingSrc;
      audio.onplay = () => { setIsSpeaking(true); setHasPendingAudio(false); };
      audio.onended = () => { setIsSpeaking(false); if (pendingSrc.startsWith('blob:')) URL.revokeObjectURL(pendingSrc); };
      audio.onerror = () => { setIsSpeaking(false); setHasPendingAudio(false); if (pendingSrc.startsWith('blob:')) URL.revokeObjectURL(pendingSrc); };
      // Called directly in event handler — user gesture context allows play()
      audio.play().catch(() => { setIsSpeaking(false); setHasPendingAudio(false); });

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

    // Always stop and clean up previous audio before starting a new one.
    // This prevents overlapping playback and stale onended handlers firing on the wrong clip.
    audio.pause();
    audio.currentTime = 0;
    audio.onended = null;
    audio.onerror = null;
    audio.onplay = null;

    // Static pre-recorded audio — play without ElevenLabs:
    //   • data:audio/... base64 URLs
    //   • direct audio file paths like /audio/welcome_ta.mp3 (served by Vercel public/)
    const isStaticAudio = audioUrl.startsWith('data:audio') || /\.(mp3|wav|ogg|aac)(\?|$)/i.test(audioUrl);
    if (isStaticAudio) {
      // Set src directly — browser preloads the file immediately.
      // No async fetch needed; avoids the timing gap where a user tap
      // could arrive before the blob URL is ready.
      audio.src = audioUrl;
      audio.onplay = () => setIsSpeaking(true);
      audio.onended = () => setIsSpeaking(false);
      audio.onerror = () => setIsSpeaking(false);
      audio.play().catch((err) => {
        if (err?.name === 'NotAllowedError') {
          // Autoplay blocked — queue for replay on next user gesture
          iosBlockedSrcRef.current = audioUrl;
          setHasPendingAudio(true);
        } else {
          setIsSpeaking(false);
        }
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
      // Check if a newer playVoice call started while we were fetching — if so, abort
      if (!audioRef.current || audioRef.current !== audio) return;
      audio.src = blobUrl;
      audio.onplay = () => setIsSpeaking(true);
      audio.onended = () => { setIsSpeaking(false); URL.revokeObjectURL(blobUrl); };
      audio.onerror = () => { setIsSpeaking(false); URL.revokeObjectURL(blobUrl); };
      audio.play().catch((err) => {
        if (err?.name === 'NotAllowedError') {
          iosBlockedSrcRef.current = blobUrl;
          setHasPendingAudio(true);
        } else {
          setIsSpeaking(false);
          URL.revokeObjectURL(blobUrl);
        }
      });
    } catch (err) {
      console.error('Error generating/playing audio:', err);
      setIsSpeaking(false);
    }
  }, [state.language]);

  const [enrollmentFormCount, setEnrollmentFormCount] = React.useState(0);
  // enrollmentSubmitted is NOT loaded from localStorage on init —
  // it is only restored when we explicitly resume a previous chat session.
  const [enrollmentSubmitted, setEnrollmentSubmitted] = React.useState(false);
  // enrollmentCancelled prevents the effect from re-showing the form after explicit dismissal
  const [enrollmentCancelled, setEnrollmentCancelled] = React.useState(false);

  // On mount: check for saved messages and decide resume vs fresh start
  React.useEffect(() => {
    const stored = localStorage.getItem('conversation_messages');
    const storedLang = localStorage.getItem('conversation_language') as 'en' | 'ta' | null;

    if (stored) {
      try {
        const messages: Message[] = JSON.parse(stored);
        // Count only real conversational messages (exclude welcome banners)
        const realMessages = messages.filter(m => m.type !== 'welcome');
        if (realMessages.length > 0) {
          // Has a real previous session — show resume prompt
          pendingMessagesRef.current = messages;
          setShowResumePrompt(true);
        } else {
          // Only welcome message stored (or empty) — treat as fresh start
          clearEnrollmentStorage();
          dispatchWelcome();
        }
      } catch {
        clearEnrollmentStorage();
        dispatchWelcome();
      }
    } else {
      // No stored session at all — fresh start
      clearEnrollmentStorage();
      dispatchWelcome();
    }

    if (storedLang) {
      dispatch({ type: 'SET_LANGUAGE', payload: storedLang });
    }
  }, [dispatchWelcome]);

  // When user chooses "Continue" previous chat — restore enrollment state too
  const handleResume = React.useCallback(() => {
    const wasEnrolled = localStorage.getItem('enrollment_submitted') === 'true';
    setEnrollmentSubmitted(wasEnrolled);
    const msgs = pendingMessagesRef.current;
    // Mark any stored welcome messages as played so auto-play doesn't replay them
    msgs.filter(m => m.type === 'welcome').forEach(m => markPlayed(m.id));
    dispatch({ type: 'LOAD_FROM_STORAGE', payload: msgs });
    pendingMessagesRef.current = [];
    setShowResumePrompt(false);
  }, [markPlayed]);

  // When user chooses "New Chat" — clear everything including enrollment, then show fresh welcome
  const handleNewChat = React.useCallback(() => {
    localStorage.removeItem('conversation_messages');
    clearEnrollmentStorage();
    setEnrollmentSubmitted(false);
    setEnrollmentCancelled(false);
    pendingMessagesRef.current = [];
    setShowResumePrompt(false);
    dispatchWelcome();
  }, [dispatchWelcome]);

  // Refresh pre-recorded static audio from backend (localStorage already loaded synchronously above)
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

  // Persist enrollment state whenever it changes
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


  // Called after the enrollment form is successfully submitted.
  // Dispatches a thank-you bot message that auto-plays the static recorded voice.
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
          audioUrl: getStaticAudioUrl(audioKey) || '/tts/generate',
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

    // If user already successfully submitted the form → static "thank you" reply, no AI call
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
            audioUrl: getStaticAudioUrl(audioKey) || '/tts/generate',
            timestamp: Date.now(),
            type: 'normal',
          }
        });
      }, 300);
      return;
    }

    // After 4 free questions — show the enrollment form directly with the prompt audio.
    // No yes/no gate. First hit plays the enrollment audio; subsequent hits (after cancel)
    // re-open the form silently so the user is not spammed with repeated audio.
    if (state.questionCount >= MAX_FREE_QUESTIONS) {
      if (!enrollmentCancelled) {
        // First time (or after form reset): play enrollment prompt audio + show form
        const promptText = state.language === 'ta'
          ? 'உங்களுக்கு மேலும் உதவ எங்கள் team ஆர்வமாக இருக்கிறது. கீழே உள்ள form-ஐ fill பண்ணுங்க!'
          : 'Our team would love to help you further. Please fill in the form below!';
        const audioKey = state.language === 'ta' ? 'enrollment_prompt_ta' : 'enrollment_prompt_en';
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
      } else {
        // User previously cancelled — reset and show form WITH audio again
        const promptText = state.language === 'ta'
          ? 'உங்களுக்கு மேலும் உதவ எங்கள் team ஆர்வமாக இருக்கிறது. கீழே உள்ள form-ஐ fill பண்ணுங்க!'
          : 'Our team would love to help you further. Please fill in the form below!';
        const audioKey = state.language === 'ta' ? 'enrollment_prompt_ta' : 'enrollment_prompt_en';
        setEnrollmentCancelled(false);
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
      }
      return;
    }

    dispatch({ type: 'SET_LOADING', payload: true });

    // iOS Safari: use AbortController to enforce a 45-second timeout.
    // Without this, fetch hangs indefinitely on slow/unstable iPhone networks.
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000);

    try {
      const response = await fetch(`${BACKEND_URL}/ask`, {
        method: 'POST',
        // Note: do NOT append charset=utf-8 — iOS Safari can reject the non-standard suffix
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

      // Until the user has had MAX_FREE_QUESTIONS answered turns, do not surface enrollment_form
      // (avoids modal on Q1 when the model or keywords mention "course" / program join).
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

      // Count this answer — form gate kicks in on the NEXT question (Q4+)
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

  // clearMessages also resets enrollment so a fresh chat always starts at 0
  const clearMessages = useCallback(() => {
    dispatch({ type: 'CLEAR_MESSAGES' });
    setEnrollmentSubmitted(false);
    setEnrollmentCancelled(false);
    clearEnrollmentStorage();
    localStorage.removeItem('conversation_messages');
    dispatchWelcome();
  }, [dispatchWelcome]);

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
    hasPendingAudio,
    stopAudio,
    playVoice,
  };

  return (
    <ConversationContext.Provider value={value}>
      {showResumePrompt && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
        }}>
          <div style={{
            background: '#1e293b', borderRadius: 16, padding: '28px 32px',
            border: '1px solid rgba(139,92,246,0.3)', maxWidth: 360, textAlign: 'center',
            boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
          }}>
            <p style={{ color: '#fff', fontSize: 16, marginBottom: 20 }}>
              Do you want to continue the previous chat?
            </p>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
              <button onClick={handleNewChat} style={{
                padding: '10px 24px', borderRadius: 8, border: '1px solid #475569',
                background: '#334155', color: '#fff', cursor: 'pointer', fontSize: 14,
              }}>New Chat</button>
              <button onClick={handleResume} style={{
                padding: '10px 24px', borderRadius: 8, border: 'none',
                background: '#7c3aed', color: '#fff', cursor: 'pointer', fontSize: 14,
              }}>Continue</button>
            </div>
          </div>
        </div>
      )}
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
