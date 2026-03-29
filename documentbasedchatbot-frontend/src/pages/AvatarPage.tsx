import React, { useRef, useState, useCallback, useEffect } from 'react';
import { SimpleVoiceInput } from '../components/SimpleVoiceInput';
import { EnrollmentForm } from '../components/EnrollmentForm';
import { useConversation } from '../contexts/ConversationContext';
import { useTheme } from '../contexts/ThemeContext';
import avatarImage from '../assets/avatar/DOCTOR FARMER CHANNEL THUMBNAIL (1).png';

interface AvatarPageProps {
  onBackClick: () => void;
  avatarImageUrl?: string;
}

export const AvatarPage: React.FC<AvatarPageProps> = ({
  onBackClick,
  avatarImageUrl = avatarImage
}) => {
  const { isLoading, language, setLanguage, askQuestion, messages, showEnrollmentForm, setShowEnrollmentForm, enrollmentSubmitted, setEnrollmentSubmitted } = useConversation();
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  const audioRef = useRef<HTMLAudioElement>(null);
  const lastPlayedMessageIdRef = useRef<string | null>(null);
  const [isSpeaking, setIsSpeaking] = useState(false);

  // Play audio using ElevenLabs TTS with emotional voice settings
  const playAudioUrl = async (text: string, voiceSettings?: any, emotionLabel?: string) => {
    if (!text) {
      console.warn("No text provided for audio generation");
      return;
    }

    try {
      setIsSpeaking(true);

      const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const ttsPayload: any = { text: text, language };

      // Include voice settings if provided
      if (voiceSettings) {
        ttsPayload.voice_settings = voiceSettings;
        ttsPayload.emotion_label = emotionLabel;
        console.log(`🎭 Avatar TTS - Sending emotional voice settings: ${emotionLabel}`, voiceSettings);
      }

      const response = await fetch(`${backendUrl}/tts/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ttsPayload)
      });

      if (!response.ok) {
        throw new Error(`TTS generation failed: ${response.statusText}`);
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);

      if (!audioRef.current) {
        audioRef.current = new Audio();
      }

      audioRef.current.src = audioUrl;
      audioRef.current.onplay = () => setIsSpeaking(true);
      audioRef.current.onended = () => {
        setIsSpeaking(false);
        URL.revokeObjectURL(audioUrl);
      };
      audioRef.current.onerror = (error) => {
        console.error("Audio playback error:", error);
        setIsSpeaking(false);
        URL.revokeObjectURL(audioUrl);
      };

      await audioRef.current.play();
    } catch (error) {
      console.error("Error generating/playing audio:", error);
      setIsSpeaking(false);
    }
  };

  const stopAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setIsSpeaking(false);
  }, []);

  const playVoice = async (text: string, voiceSettings?: any, emotionLabel?: string) => {
    await playAudioUrl(text, voiceSettings, emotionLabel);
  };

  // Auto-play audio for new bot messages with emotional voice
  useEffect(() => {
    if (messages.length === 0) return;

    const lastMessage = messages[messages.length - 1];
    // Play audio only if it's a new bot message we haven't played yet
    if (lastMessage.sender === 'bot' && !isLoading && lastMessage.id !== lastPlayedMessageIdRef.current) {
      lastPlayedMessageIdRef.current = lastMessage.id;
      // Pass voice settings and emotion label from message for expressive speech
      playVoice(
        lastMessage.text,
        (lastMessage as any).voice_settings,
        (lastMessage as any).emotion
      );
    }
  }, [messages, isLoading]);

  // Show enrollment form when bot responds with enrollment_form type
  useEffect(() => {
    if (messages.length === 0 || isLoading || enrollmentSubmitted) return;

    const lastMessage = messages[messages.length - 1];
    if (lastMessage.sender !== 'bot') return;

    const enrollmentWords = ['join', 'enroll', 'enrollment', 'register', 'course', 'admission', 'apply', 'fees', 'சேர', 'பதிவு', 'கோர்ஸ்'];
    const lastUser = [...messages].reverse().find(m => m.sender === 'user');
    const userAskedEnrollment = lastUser && enrollmentWords.some(w => lastUser.text.toLowerCase().includes(w));
    const showForm = lastMessage.type === 'enrollment_form' || (lastMessage.type === 'normal' && userAskedEnrollment);

    if (showForm) setShowEnrollmentForm(true);
  }, [messages, isLoading, enrollmentSubmitted]);

  // Handle transcription from voice input
  const handleTranscription = useCallback(async (text: string) => {
    if (!text.trim()) return;

    // Stop any currently playing audio
    stopAudio();

    // Use context to ask the question in 'document' mode
    try {
      await askQuestion(text, 'document');
      // Note: TTS playback is handled by the page's playAudioUrl function
      // if the bot response is set to auto-play, or can be manually triggered
    } catch (error) {
      console.error('Error asking question:', error);
    }
  }, [askQuestion, stopAudio]);

  const glowFilter = (intensity: number) => {
    const i = intensity;
    return `drop-shadow(0 0 60px rgba(168,85,247,${i * 0.5})) drop-shadow(0 0 100px rgba(168,85,247,${i * 0.35})) drop-shadow(0 0 140px rgba(168,85,247,${i * 0.2})) drop-shadow(0 0 180px rgba(168,85,247,${i * 0.12}))`;
  };

  return (
    <div className={`relative w-full h-screen overflow-hidden transition-colors ${isDark ? 'bg-[#0d0a14]' : 'bg-gray-100'}`}>
      <style>{`
        @keyframes glowBlink {
          0%, 100% { filter: ${glowFilter(1)}; }
          50% { filter: ${glowFilter(0.4)}; }
        }
        .avatar-glow-blink {
          animation: glowBlink 1.2s ease-in-out infinite;
        }
      `}</style>
      {/* Full-screen background image - edge-to-edge */}
      <div className="absolute inset-0 flex items-center justify-center">
        <img
          src={avatarImageUrl}
          alt="Avatar"
          className={`w-full h-full object-contain object-center ${isSpeaking ? 'avatar-glow-blink' : ''}`}
          style={
            isSpeaking
              ? {}
              : { filter: glowFilter(0.6), transition: 'filter 0.3s ease' }
          }
        />
        {/* Gradient overlay for contrast */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: isDark
              ? 'linear-gradient(to bottom, rgba(13,10,20,0.2) 0%, rgba(13,10,20,0.4) 40%, rgba(13,10,20,0.7) 100%)'
              : 'linear-gradient(to bottom, rgba(255,255,255,0.1) 0%, rgba(0,0,0,0.2) 40%, rgba(0,0,0,0.4) 100%)',
          }}
        />
      </div>

      {/* Top right: Theme toggle + Message button */}
      <div className="absolute top-0 right-0 z-30 flex items-center gap-2 p-4">
        {isSpeaking && (
          <button
            type="button"
            onClick={stopAudio}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-theme-accent/20 text-theme-accent rounded-full text-xs font-semibold animate-pulse border border-theme-accent/40 hover:bg-theme-accent/30 cursor-pointer transition-colors backdrop-blur-sm"
            title="Click to stop speaking"
          >
            <div className="w-1.5 h-1.5 bg-theme-accent rounded-full relative"><div className="absolute inset-0 bg-theme-accent rounded-full animate-ping opacity-75"></div></div>
            Speaking
          </button>
        )}
        <button
          type="button"
          onClick={toggleTheme}
          className={`p-2.5 rounded-xl backdrop-blur-sm transition-colors ${
            isDark
              ? 'bg-white/10 text-white/80 border border-white/20 hover:bg-white/15'
              : 'bg-black/10 text-gray-700 border border-gray-300 hover:bg-black/15'
          }`}
          title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {isDark ? (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          )}
        </button>
        <button
          onClick={onBackClick}
          className={`p-2.5 rounded-xl backdrop-blur-sm transition-colors ${
            isDark
              ? 'hover:bg-white/10 text-white/80 hover:text-white border border-white/10'
              : 'hover:bg-black/10 text-gray-700 hover:text-gray-900 border border-gray-300'
          }`}
          title="Go to chat"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </button>
      </div>

      {/* Bottom floating controls - overlay on image */}
      <div className="absolute bottom-6 left-0 right-0 z-30 flex flex-col items-center gap-4 px-4 sm:bottom-8">
        {/* Loading indicator - above EN/TA buttons */}
        {isLoading && (
          <div className="flex gap-2 px-5 py-3 bg-black/40 backdrop-blur-md rounded-2xl border border-theme-accent/30">
            <div className="w-2 h-2 bg-theme-accent rounded-full animate-bounce" style={{ animationDelay: '-0.3s' }}></div>
            <div className="w-2 h-2 bg-theme-accent rounded-full animate-bounce" style={{ animationDelay: '-0.15s' }}></div>
            <div className="w-2 h-2 bg-theme-accent rounded-full animate-bounce"></div>
          </div>
        )}
        <SimpleVoiceInput
          onTranscription={handleTranscription}
          disabled={isLoading}
          language={language}
          onLanguageChange={(lang) => {
            setLanguage(lang);
            stopAudio();
          }}
          onRecordingStart={stopAudio}
          variant="overlay"
        />
      </div>

      {/* Hidden audio element for playback */}
      <audio ref={audioRef} />

      {/* Enrollment Form Modal */}
      {showEnrollmentForm && (() => {
        const hasTamil = (t: string) => /[\u0B80-\u0BFF]/.test(t);
        const lastUserMsg = [...messages].reverse().find(m => m.sender === 'user');
        const formLang: 'en' | 'ta' = lastUserMsg && !hasTamil(lastUserMsg.text) ? 'en' : language;
        return (
          <EnrollmentForm
            onClose={() => {
              setShowEnrollmentForm(false);
              setEnrollmentSubmitted(true);
            }}
            language={formLang}
            isDark={isDark}
          />
        );
      })()}
    </div>
  );
};
