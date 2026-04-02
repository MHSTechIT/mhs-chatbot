import React, { useEffect, useRef, useCallback } from 'react';
import { ChatMessage, type MessageProps } from './ChatMessage';
import { TextInput } from './TextInput';
import { SimpleVoiceInput } from './SimpleVoiceInput';
import { EnrollmentForm } from './EnrollmentForm';
import { useConversation } from '../contexts/ConversationContext';
import { useTheme } from '../contexts/ThemeContext';

const logoUrl = new URL('../assets/logo/logo.png', import.meta.url).href;

interface ChatContainerProps {
    onAvatarClick?: () => void;
}

export const ChatContainer: React.FC<ChatContainerProps> = ({ onAvatarClick }) => {
    const {
        messages: contextMessages, isLoading, language, askQuestion, setLanguage,
        showEnrollmentForm, setShowEnrollmentForm, enrollmentSubmitted, setEnrollmentSubmitted,
        hasPlayed, markPlayed,
        isSpeaking, stopAudio, playVoice,
    } = useConversation();
    const { theme, toggleTheme } = useTheme();
    const isDark = theme === 'dark';

    const messagesEndRef = useRef<HTMLDivElement>(null);

    const messages: MessageProps[] = contextMessages.length === 0
        ? [{ id: '1', sender: 'bot', text: 'Hi, I am your My Health School assistant how can i help you' }]
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

    // Auto-scroll — fires on messages change AND when loading starts (shows typing indicator)
    useEffect(() => {
        setTimeout(() => {
            messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }, 60);
    }, [messages, isLoading]);

    // Auto-play audio for new bot messages (shared audio — won't replay on page switch)
    useEffect(() => {
        if (messages.length === 0) return;
        const lastMessage = messages[messages.length - 1];
        if (lastMessage.sender === 'bot' && !isLoading && !hasPlayed(lastMessage.id)) {
            markPlayed(lastMessage.id);
            setTimeout(() => {
                playVoice(lastMessage.text, lastMessage.audioUrl || 'audio_enabled', lastMessage.voice_settings, lastMessage.emotion);
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
        if (lastMessage.type === 'enrollment_form' || (lastMessage.type === 'normal' && userAskedEnrollment)) {
            setShowEnrollmentForm(true);
        }
    }, [messages, isLoading, enrollmentSubmitted]);

    const handleSendMessage = useCallback(async (text: string) => {
        if (!text.trim()) return;
        stopAudio();
        if ('speechSynthesis' in window) window.speechSynthesis.cancel();
        await askQuestion(text, 'health');
    }, [stopAudio, askQuestion]);

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
                    <div>
                        <h2 className={`font-semibold text-base leading-tight ${isDark ? 'text-white' : 'text-gray-900'}`}>MHS AI Assistant</h2>
                        <p className={`text-xs font-medium ${isDark ? 'text-theme-muted' : 'text-gray-500'}`}>My Health School Assistant</p>
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
                            <div className="w-1.5 h-1.5 bg-theme-accent rounded-full relative">
                                <div className="absolute inset-0 bg-theme-accent rounded-full animate-ping opacity-75"></div>
                            </div>
                            Speaking
                        </button>
                    )}
                    <button
                        type="button"
                        onClick={toggleTheme}
                        className={`p-2 rounded-lg transition-colors ${
                            isDark ? 'hover:bg-theme-accent/20 text-theme-muted hover:text-theme-accent' : 'hover:bg-violet-100 text-gray-500 hover:text-violet-600'
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

            <div className="flex flex-col flex-1 overflow-y-auto overflow-x-hidden p-4 sm:p-6 space-y-3 min-h-0 pb-56 scroll-smooth">
                {messages.map((msg) => (
                    <ChatMessage key={msg.id} message={msg} onReplay={playVoice} isDark={isDark} />
                ))}
                {isLoading && (
                    <div className="flex w-full mb-4 justify-start">
                        <div className="flex max-w-[80%] md:max-w-[70%]">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center mr-2 flex-shrink-0 mt-auto border ${
                                isDark ? 'bg-theme-accent/20 border-theme-cardBorder' : 'bg-violet-100 border-violet-200'
                            }`}>
                                <svg className="w-5 h-5 text-theme-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
                <div className="flex items-end gap-3">
                    <SimpleVoiceInput
                        onTranscription={handleSendMessage}
                        disabled={isLoading}
                        language={language}
                        onLanguageChange={(lang) => { setLanguage(lang); stopAudio(); }}
                        onRecordingStart={stopAudio}
                        navigateToAvatarOnMicClick={onAvatarClick}
                        isDark={isDark}
                    />
                    <div className="flex-1">
                        <TextInput onSend={handleSendMessage} disabled={isLoading} isDark={isDark} />
                    </div>
                </div>
            </div>

            {showEnrollmentForm && (() => {
                const hasTamil = (t: string) => /[\u0B80-\u0BFF]/.test(t);
                const lastUserMsg = [...messages].reverse().find(m => m.sender === 'user');
                const formLang: 'en' | 'ta' = lastUserMsg && !hasTamil(lastUserMsg.text) ? 'en' : language;
                return (
                    <EnrollmentForm
                        onClose={() => setShowEnrollmentForm(false)}
                        onSubmit={() => setEnrollmentSubmitted(true)}
                        language={formLang}
                        isDark={isDark}
                    />
                );
            })()}
        </div>
    );
};
