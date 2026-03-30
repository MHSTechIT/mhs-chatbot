import React from 'react';

/**
 * Represents a single message entity in the chat history.
 */
export interface MessageProps {
    id: string;
    sender: 'user' | 'bot';
    text: string;
    isError?: boolean;
    audioUrl?: string;
    type?: string;
    emotion?: string;
    voice_settings?: {
        stability: number;
        similarity_boost: number;
        style: number;
        use_speaker_boost: boolean;
    };
}

/**
 * Props for the ChatMessage component.
 */
interface ChatMessageProps {
    message: MessageProps;
    /** Optional callback triggered to replay the bot's voice message */
    onReplay?: (text: string, audioUrl?: string, voiceSettings?: MessageProps['voice_settings'], emotion?: string) => void;
    /** Dark mode styling (default: true) */
    isDark?: boolean;
}

/**
 * A functional component that renders an individual chat bubble.
 * Differentiates visual styles between 'user' and 'bot' messages.
 * 
 * @component
 */

export const ChatMessage: React.FC<ChatMessageProps> = ({ message, onReplay, isDark = true }) => {
    const isBot = message.sender === 'bot';

    return (
        <div className={`flex w-full mb-4 ${isBot ? 'justify-start' : 'justify-end'}`}>
            <div className={`flex max-w-[80%] md:max-w-[70%] group`}>
                {isBot && (
                    <div className={`w-8 h-8 rounded-full border flex items-center justify-center mr-2 flex-shrink-0 mt-auto shadow-sm ${
                        isDark ? 'bg-theme-accent/20 border-theme-cardBorder' : 'bg-violet-100 border-violet-200'
                    }`}>
                        <svg className="w-5 h-5 text-theme-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                        </svg>
                    </div>
                )}

                <div className={`relative px-4 py-3 shadow-sm ${
                    message.isError
                        ? 'bg-red-900/30 text-red-300 border-red-500/50 rounded-2xl rounded-bl-sm border'
                        : isBot
                            ? isDark
                                ? 'bg-theme-card text-white rounded-2xl rounded-bl-sm border border-theme-cardBorder'
                                : 'bg-violet-500 text-white rounded-2xl rounded-bl-sm border border-violet-400'
                            : isDark
                                ? 'bg-gradient-to-r from-theme-accent to-theme-accentDim text-white rounded-2xl rounded-br-sm border border-theme-accent/50'
                                : 'bg-violet-500 text-white rounded-2xl rounded-br-sm border border-violet-400'
                }`}>
                    <div className="text-[15px] leading-relaxed whitespace-pre-wrap">{message.text}</div>

                    {isBot && message.emotion && !message.isError && (
                        <div className="mt-1.5 text-[11px] opacity-50 select-none">{message.emotion}</div>
                    )}

                    {isBot && onReplay && !message.isError && (
                        <button
                            onClick={() => {
                                if ('speechSynthesis' in window) {
                                    window.speechSynthesis.cancel();
                                }
                                onReplay(message.text, message.audioUrl, message.voice_settings, message.emotion);
                            }}
                            className={`absolute -right-10 top-1/2 -translate-y-1/2 p-2 text-theme-muted hover:text-theme-accent opacity-0 group-hover:opacity-100 transition-opacity rounded-full shadow-sm border ${
                                isDark ? 'bg-theme-card border-theme-cardBorder' : 'bg-violet-100 border-violet-200'
                            }`}
                            title="Replay Voice"
                        >
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                            </svg>
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};
