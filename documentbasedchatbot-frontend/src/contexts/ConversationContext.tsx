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
}

const ConversationContext = createContext<ConversationContextType | undefined>(undefined);

type ConversationAction =
  | { type: 'ADD_USER_MESSAGE'; payload: Message }
  | { type: 'ADD_BOT_MESSAGE'; payload: Message }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_LANGUAGE'; payload: 'en' | 'ta' }
  | { type: 'CLEAR_MESSAGES' }
  | { type: 'LOAD_FROM_STORAGE'; payload: Message[] };

interface ConversationState {
  messages: Message[];
  isLoading: boolean;
  language: 'en' | 'ta';
}

const initialState: ConversationState = {
  messages: [],
  isLoading: false,
  language: 'ta',
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
      };
    case 'LOAD_FROM_STORAGE':
      return {
        ...state,
        messages: action.payload,
      };
    default:
      return state;
  }
}

export const ConversationProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(conversationReducer, initialState);

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
        dispatch({ type: 'LOAD_FROM_STORAGE', payload: messages });
      } catch (e) {
        console.error('Failed to load messages from storage:', e);
      }
    }

    if (storedLang) {
      dispatch({ type: 'SET_LANGUAGE', payload: storedLang });
    }
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

  const askQuestion = useCallback(async (question: string, mode: string = 'health') => {
    if (!question.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: question,
      timestamp: Date.now(),
    };
    dispatch({ type: 'ADD_USER_MESSAGE', payload: userMessage });

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
  }, [state.language]);

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
