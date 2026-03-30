import React, { createContext, useReducer, useCallback } from 'react';
import type { ReactNode } from 'react';

export interface Message {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  audioUrl?: string;
  timestamp: number;
  type?: 'normal' | 'enrollment_form' | 'error';
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
  /** Shared across Chat and Avatar pages - form visible state */
  showEnrollmentForm: boolean;
  setShowEnrollmentForm: (show: boolean) => void;
  /** True after user submits or cancels - prevents form from showing again */
  enrollmentSubmitted: boolean;
  setEnrollmentSubmitted: (submitted: boolean) => void;
  /** Number of questions answered so far (resets on new chat) */
  questionCount: number;
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
      return {
        ...state,
        messages: [...state.messages, action.payload],
      };
    case 'ADD_BOT_MESSAGE':
      return {
        ...state,
        messages: [...state.messages, action.payload],
      };
    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
      };
    case 'SET_LANGUAGE':
      return {
        ...state,
        language: action.payload,
      };
    case 'CLEAR_MESSAGES':
      return {
        ...state,
        messages: [],
        questionCount: 0,
      };
    case 'LOAD_FROM_STORAGE':
      return {
        ...state,
        messages: action.payload,
        // Count existing bot answers when resuming a conversation
        questionCount: action.payload.filter(m => m.sender === 'bot' && m.type !== 'error').length,
      };
    case 'INCREMENT_QUESTION_COUNT':
      return {
        ...state,
        questionCount: state.questionCount + 1,
      };
    default:
      return state;
  }
}

export const ConversationProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(conversationReducer, initialState);
  const [showResumePrompt, setShowResumePrompt] = React.useState(false);
  const pendingMessagesRef = React.useRef<Message[]>([]);
  // Cache for pre-recorded static audio (base64 mp3) — avoids ElevenLabs API calls for fixed messages
  const staticAudioRef = React.useRef<Record<string, string>>({});

  const [showEnrollmentForm, setShowEnrollmentForm] = React.useState(false);
  const [enrollmentSubmitted, setEnrollmentSubmitted] = React.useState(() => {
    try {
      return localStorage.getItem('enrollment_submitted') === 'true';
    } catch {
      return false;
    }
  });

  React.useEffect(() => {
    const stored = localStorage.getItem('conversation_messages');
    const storedLang = localStorage.getItem('conversation_language') as 'en' | 'ta' | null;

    if (stored) {
      try {
        const messages = JSON.parse(stored);
        if (messages.length > 0) {
          pendingMessagesRef.current = messages;
          setShowResumePrompt(true);
        }
      } catch (e) {
        console.error('Failed to load messages from storage:', e);
      }
    }

    if (storedLang) {
      dispatch({ type: 'SET_LANGUAGE', payload: storedLang });
    }
  }, []);

  const handleResume = React.useCallback(() => {
    dispatch({ type: 'LOAD_FROM_STORAGE', payload: pendingMessagesRef.current });
    pendingMessagesRef.current = [];
    setShowResumePrompt(false);
  }, []);

  const handleNewChat = React.useCallback(() => {
    localStorage.removeItem('conversation_messages');
    pendingMessagesRef.current = [];
    setShowResumePrompt(false);
  }, []);

  // Load pre-recorded static audio from localStorage cache, then refresh from backend
  React.useEffect(() => {
    try {
      const cached = localStorage.getItem('static_audio_cache');
      if (cached) staticAudioRef.current = JSON.parse(cached);
    } catch {}

    const backendUrl = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';
    fetch(`${backendUrl}/admin/static-audio`)
      .then(r => r.json())
      .then(data => {
        if (data?.audio && Object.keys(data.audio).length > 0) {
          staticAudioRef.current = data.audio;
          localStorage.setItem('static_audio_cache', JSON.stringify(data.audio));
        }
      })
      .catch(() => {});
  }, []);

  React.useEffect(() => {
    localStorage.setItem('enrollment_submitted', String(enrollmentSubmitted));
  }, [enrollmentSubmitted]);

  React.useEffect(() => {
    localStorage.setItem('conversation_messages', JSON.stringify(state.messages));
  }, [state.messages]);

  React.useEffect(() => {
    localStorage.setItem('conversation_language', state.language);
  }, [state.language]);

  const MAX_FREE_QUESTIONS = 3;

  // Helper: get a static audio data URL (or undefined if not cached yet)
  const getStaticAudioUrl = (key: string): string | undefined => {
    const b64 = staticAudioRef.current[key];
    return b64 ? `data:audio/mp3;base64,${b64}` : undefined;
  };

  const askQuestion = useCallback(async (question: string, mode: string = 'health') => {
    if (!question.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: question,
      timestamp: Date.now(),
    };
    dispatch({ type: 'ADD_USER_MESSAGE', payload: userMessage });

    // If user already filled the form, reply with a short static message — no AI call needed
    if (enrollmentSubmitted && state.questionCount >= MAX_FREE_QUESTIONS) {
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

    dispatch({ type: 'SET_LOADING', payload: true });

    try {
      const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json; charset=utf-8',
        },
        body: JSON.stringify({
          question: question,
          mode: mode,
          language: state.language,
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const result = await response.json();

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'bot',
        text: result.answer,
        audioUrl: result.audio_url,
        timestamp: Date.now(),
        type: result.type,
        isError: result.type === 'error',
        voice_settings: result.voice_settings,
        emotion: result.emotion,
      };
      dispatch({ type: 'ADD_BOT_MESSAGE', payload: botMessage });

      // Count this answer and check if we've hit the limit
      if (result.type !== 'error') {
        dispatch({ type: 'INCREMENT_QUESTION_COUNT' });
        const newCount = state.questionCount + 1;

        if (newCount >= MAX_FREE_QUESTIONS && !enrollmentSubmitted) {
          const promptText = state.language === 'ta'
            ? 'நம்ம course பத்தி more details தெரிஞ்சுக்கணும்னா, கீழே உள்ள form-ஐ fill பண்ணுங்க! எங்க team உங்களை விரைவில் contact பண்ணுவாங்க!'
            : 'For more details and personalized guidance, please fill in the form below — our team will contact you soon!';
          const audioKey = state.language === 'ta' ? 'enrollment_prompt_ta' : 'enrollment_prompt_en';

          setTimeout(() => {
            const enrollMsg: Message = {
              id: (Date.now() + 2).toString(),
              sender: 'bot',
              text: promptText,
              audioUrl: getStaticAudioUrl(audioKey) || '/tts/generate',
              timestamp: Date.now(),
              type: 'enrollment_form',
            };
            dispatch({ type: 'ADD_BOT_MESSAGE', payload: enrollMsg });
            setShowEnrollmentForm(true);
          }, 800);
        }
      }
    } catch (error) {
      console.error('Error asking question:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'bot',
        text: 'Sorry, there was an error processing your question. Please try again.',
        timestamp: Date.now(),
        type: 'error',
        isError: true,
      };
      dispatch({ type: 'ADD_BOT_MESSAGE', payload: errorMessage });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, [state.language, state.questionCount, enrollmentSubmitted]);

  const setLanguage = useCallback((lang: 'en' | 'ta') => {
    dispatch({ type: 'SET_LANGUAGE', payload: lang });
  }, []);

  const clearMessages = useCallback(() => {
    dispatch({ type: 'CLEAR_MESSAGES' });
  }, []);

  const value: ConversationContextType = {
    messages: state.messages,
    isLoading: state.isLoading,
    language: state.language,
    askQuestion,
    setLanguage,
    clearMessages,
    showEnrollmentForm,
    setShowEnrollmentForm,
    enrollmentSubmitted,
    setEnrollmentSubmitted,
    questionCount: state.questionCount,
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
