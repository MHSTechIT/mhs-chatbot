import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ChatMessage, type MessageProps } from './ChatMessage';
import { TextInput } from './TextInput';
import { SimpleVoiceInput } from './SimpleVoiceInput';
import { EnrollmentForm } from './EnrollmentForm';
import { useConversation } from '../contexts/ConversationContext';
import { useTheme } from '../contexts/ThemeContext';

const logoUrl = new URL('../assets/logo/logo.png', import.meta.url).href;

/**
 * ChatContainer serves as the main chat interface orchestrator.
 * It now uses ConversationContext for shared message history across Chat and Avatar pages.
 * Manages message display, audio playback, and enrollment form logic.
 *
 * @component
 */
interface ChatContainerProps {
    onAvatarClick?: () => void;
}

export const ChatContainer: React.FC<ChatContainerProps> = ({ onAvatarClick }) => {
    const { messages: contextMessages, isLoading, language, askQuestion, setLanguage, showEnrollmentForm, setShowEnrollmentForm, enrollmentSubmitted, setEnrollmentSubmitted, questionCount } = useConversation();
    const inputBlocked = questionCount >= 3 && !enrollmentSubmitted;
    const { theme, toggleTheme } = useTheme();
    const isDark = theme === 'dark';

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const [isSpeaking, setIsSpeaking] = useState(false);
    const audioRef = useRef<HTMLAudioElement>(null);
    const lastPlayedMessageIdRef = useRef<string | null>(null);
    // Ensure we always have the initial greeting message if chat is empty
    const messages: MessageProps[] = contextMessages.length === 0
        ? [
            {
                id: '1',
                sender: 'bot',
                text: 'Hi, I am your My Health School assistant how can i help you'
            }
        ]
        : contextMessages.map(msg => ({
            id: msg.id,
            sender: msg.sender as 'user' | 'bot',
            text: msg.text,
            audioUrl: msg.audioUrl,
            type: msg.type,
            isError: msg.sender === 'bot' && msg.text.includes('error'),
            voice_settings: msg.voice_settings,
            emotion: msg.emotion,
        }));

    // Auto-scroll to latest message
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Auto-play audio for new bot messages (with user interaction trigger)
    useEffect(() => {
        if (messages.length === 0) return;

        const lastMessage = messages[messages.length - 1];
        // Play audio only if it's a new bot message we haven't played yet
        if (lastMessage.sender === 'bot' && !isLoading && lastMessage.id !== lastPlayedMessageIdRef.current) {
            lastPlayedMessageIdRef.current = lastMessage.id;
            // Delay slightly to ensure DOM is ready for audio playback
            setTimeout(() => {
                // Pass voice settings and emotion label from message
                // Use actual audioUrl (may be a static data: URL or '/tts/generate' flag)
                playVoice(
                    lastMessage.text,
                    lastMessage.audioUrl || 'audio_enabled',
                    lastMessage.voice_settings,
                    lastMessage.emotion
                );
            }, 500);
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

    /**
     * Plays audio from ElevenLabs TTS using the backend /tts/generate endpoint.
     * Fetches audio as a blob and plays it using an object URL.
     *
     * @param {string} text - The text to generate audio for.
     */
    const playAudioUrl = async (text: string, voiceSettings?: any, emotionLabel?: string) => {
        if (!text) {
            console.warn("No text provided for audio generation");
            return;
        }

        try {
            setIsSpeaking(true);

            // Make POST request to backend /tts/generate endpoint with emotional voice settings
            const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const ttsPayload: any = { text: text, language };

            // Include voice settings if provided from backend emotion detection
            if (voiceSettings) {
                ttsPayload.voice_settings = voiceSettings;
                ttsPayload.emotion_label = emotionLabel;
                console.log(`🎭 Sending emotional voice settings: ${emotionLabel}`, voiceSettings);
            }

            const response = await fetch(`${backendUrl}/tts/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(ttsPayload)
            });

            if (!response.ok) {
                throw new Error(`TTS generation failed: ${response.statusText}`);
            }

            // Get audio blob from response
            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);

            if (!audioRef.current) {
                audioRef.current = new Audio();
            }

            audioRef.current.src = audioUrl;
            audioRef.current.onplay = () => setIsSpeaking(true);
            audioRef.current.onended = () => {
                setIsSpeaking(false);
                URL.revokeObjectURL(audioUrl); // Clean up object URL
            };
            audioRef.current.onerror = (error) => {
                console.error("Audio playback error:", error);
                setIsSpeaking(false);
                URL.revokeObjectURL(audioUrl);
            };

            // Use user interaction promise to ensure browser allows playback
            const playPromise = audioRef.current.play();
            if (playPromise !== undefined) {
                playPromise.catch((error) => {
                    console.warn("Autoplay prevented. Audio will not play automatically. Error:", error);
                    setIsSpeaking(false);
                    // Don't throw - just silently skip audio if autoplay is blocked
                });
            }
        } catch (error) {
            console.error("Error generating/playing audio:", error);
            setIsSpeaking(false);
        }
    };

    /**
     * Plays audio using ElevenLabs TTS.
     * Always uses ElevenLabs API - no browser speech synthesis fallback.
     *
     * @param {string} text - The text string that the bot should "speak".
     * @param {string} audioUrl - Flag indicating ElevenLabs TTS should be used.
     */
    /**
     * Stops audio playback and resets speaking state
     */
    const stopAudio = useCallback(() => {
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current.currentTime = 0;
        }
        setIsSpeaking(false);
    }, []);

    const playVoice = async (text: string, audioUrl?: string, voiceSettings?: any, emotionLabel?: string) => {
        if (!audioUrl) {
            console.info("TTS skipped — no audio URL");
            return;
        }
        // Pre-recorded static audio (data URL) — play directly, no API call needed
        if (audioUrl.startsWith('data:audio')) {
            try {
                setIsSpeaking(true);
                if (!audioRef.current) audioRef.current = new Audio();
                audioRef.current.src = audioUrl;
                audioRef.current.onended = () => setIsSpeaking(false);
                audioRef.current.onerror = () => setIsSpeaking(false);
                await audioRef.current.play().catch(() => setIsSpeaking(false));
            } catch {
                setIsSpeaking(false);
            }
            return;
        }
        // Dynamic TTS via ElevenLabs
        await playAudioUrl(text, voiceSettings, emotionLabel);
    };

    /**
     * Handles sending a message using the shared ConversationContext.
     * Asks the question in 'health' mode and plays TTS audio when response arrives.
     *
     * @param {string} text - The question submitted by the user.
     */
    const handleSendMessage = useCallback(async (text: string) => {
        if (!text.trim()) return;

        // Stop any currently playing audio
        stopAudio();

        // Cancel any browser speech synthesis that might be running
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }

        // Use context to ask the question in 'health' mode
        await askQuestion(text, 'health');

        // Handle enrollment form if needed
        // Note: For now, we're keeping the enrollment form logic simple
        // This can be enhanced later to handle specific response types
        if (!enrollmentSubmitted) {
            // Optional: You can add logic here to detect enrollment_form type from context
            // setShowEnrollmentForm(true);
            // setEnrollmentSubmitted(true);
        }
    }, [stopAudio, askQuestion, enrollmentSubmitted]);

    return (
        <div className={`flex flex-col w-full h-screen transition-colors ${isDark ? 'bg-theme-base' : 'bg-white'}`}>
            <div className={`px-6 py-3 border-b flex items-center justify-between z-20 shrink-0 sticky top-0 transition-colors ${
                isDark ? 'bg-theme-card border-theme-cardBorder' : 'bg-gray-50 border-gray-200'
            }`}>
                <div className="flex items-center gap-3">
                        <div className="relative">
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center border ${
                                isDark ? 'bg-theme-accent/15 border-theme-cardBorder' : 'bg-violet-100 border-violet-200'
                            }`}>
                                <img src={logoUrl} className="w-7 h-7" alt="Logo" />
                            </div>
                            <div className={`absolute bottom-0 right-0 w-3 h-3 bg-emerald-500 rounded-full border-2 ${
                                isDark ? 'border-theme-card' : 'border-gray-50'
            }`}></div>
                        </div>
                        <div className="flex items-center gap-2">
                            <div>
                                <h2 className={`font-semibold text-base leading-tight ${isDark ? 'text-white' : 'text-gray-900'}`}>MHS AI Assistant</h2>
                                <p className={`text-xs font-medium ${isDark ? 'text-theme-muted' : 'text-gray-500'}`}>My Health School Assistant</p>
                            </div>
                        </div>
                </div>
                <div className="flex items-center gap-2 -mt-1">
                    {isSpeaking && (
                        <button
                            type="button"
                            onClick={stopAudio}
                            className="flex items-center gap-1.5 px-3 py-1 bg-theme-accent/20 text-theme-accent rounded-full text-xs font-semibold animate-pulse border border-theme-accent/40 hover:bg-theme-accent/30 cursor-pointer transition-colors"
                            title="Click to stop speaking"
                        >
                            <div className="w-1.5 h-1.5 bg-theme-accent rounded-full relative"><div className="absolute inset-0 bg-theme-accent rounded-full animate-ping opacity-75"></div></div>
                            Speaking
                        </button>
                    )}
                    <button
                        type="button"
                        onClick={toggleTheme}
                        className={`p-2 rounded-lg transition-colors ${
                            isDark
                                ? 'hover:bg-theme-accent/20 text-theme-muted hover:text-theme-accent'
                                : 'hover:bg-violet-100 text-gray-500 hover:text-violet-600'
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
                </div>
            </div>

            <div className="flex flex-col flex-1 overflow-y-auto overflow-x-hidden p-4 sm:p-6 space-y-3 min-h-0 pb-48 scroll-smooth">
                {messages.map((msg) => (
                    <ChatMessage key={msg.id} message={msg} onReplay={playVoice} isDark={isDark} />
                ))}

                {isLoading && (
                    <div className="flex w-full mb-4 justify-start">
                        <div className="flex max-w-[80%] md:max-w-[70%]">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center mr-2 flex-shrink-0 mt-auto border ${
                                isDark ? 'bg-theme-accent/20 border-theme-cardBorder' : 'bg-violet-100 border-violet-200'
                            }`}>
                                <svg className="w-5 h-5 text-theme-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                                </svg>
                            </div>
                            <div className={`px-5 py-4 border rounded-2xl rounded-bl-sm shadow-sm flex items-center gap-1.5 ${
                                isDark ? 'bg-theme-card border-theme-cardBorder' : 'bg-violet-100 border-violet-200'
                            }`}>
                                <div className="w-1.5 h-1.5 bg-theme-muted rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                <div className="w-1.5 h-1.5 bg-theme-muted rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                <div className="w-1.5 h-1.5 bg-theme-muted rounded-full animate-bounce"></div>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className={`fixed bottom-0 left-0 right-0 px-4 py-4 border-t z-20 space-y-3 transition-colors ${
                isDark ? 'bg-theme-card border-theme-cardBorder' : 'bg-gray-50 border-gray-200'
            }`}>
                {/* Voice Input and Text Input Side by Side */}
                <div className="flex items-end gap-3">
                    <SimpleVoiceInput
                        onTranscription={handleSendMessage}
                        disabled={isLoading || inputBlocked}
                        language={language}
                        onLanguageChange={(lang) => {
                            setLanguage(lang);
                            stopAudio();
                        }}
                        onRecordingStart={stopAudio}
                        navigateToAvatarOnMicClick={onAvatarClick}
                        isDark={isDark}
                    />
                    <div className="flex-1">
                        <TextInput
                            onSend={handleSendMessage}
                            disabled={isLoading || inputBlocked}
                            isDark={isDark}
                        />
                    </div>
                </div>
            </div>

            {/* Hidden audio element for ElevenLabs TTS playback */}
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
