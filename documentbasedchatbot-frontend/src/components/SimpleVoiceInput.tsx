import React, { useState, useEffect, useRef, useCallback } from 'react';

interface SimpleVoiceInputProps {
    onTranscription: (text: string) => void;
    disabled?: boolean;
    language?: 'en' | 'ta';
    onLanguageChange?: (lang: 'en' | 'ta') => void;
    onRecordingStart?: () => void;
    /** When set, mic button navigates to avatar page instead of recording. EN/TA buttons are hidden. */
    navigateToAvatarOnMicClick?: () => void;
    /** Overlay variant: dark translucent buttons for use on top of images */
    variant?: 'default' | 'overlay';
    /** Dark/light mode for button styling (default variant on chat page) */
    isDark?: boolean;
}

export const SimpleVoiceInput: React.FC<SimpleVoiceInputProps> = ({
    onTranscription,
    disabled,
    language: parentLanguage,
    onLanguageChange,
    onRecordingStart,
    navigateToAvatarOnMicClick,
    variant = 'default',
    isDark = true
}) => {
    const [isListening, setIsListening] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [transcript, setTranscript] = useState('');
    const [language, setLanguage] = useState<'en' | 'ta'>(parentLanguage || 'ta');
    useEffect(() => {
        if (parentLanguage) setLanguage(parentLanguage);
    }, [parentLanguage]);
    const recognitionRef = useRef<any>(null);
    const accumulatedTranscriptRef = useRef('');
    const silenceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const shouldListenRef = useRef(false);

    const SILENCE_DELAY_MS = 2000;

    useEffect(() => {
        // Initialize Web Speech API
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

        if (!SpeechRecognition) {
            setError("Speech recognition not supported - use Chrome/Edge");
            console.error('[SimpleVoiceInput] Speech Recognition not available');
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.continuous = false;  // Listen for single utterance
        recognition.interimResults = true;  // Show results as user speaks
        recognition.lang = language === 'ta' ? 'ta-IN' : 'en-IN';  // Support both Tamil and English
        recognitionRef.current = recognition;

        recognition.onstart = () => {
            console.log('[SimpleVoiceInput] Started listening');
            setIsListening(true);
            setError(null);
            setTranscript('');
            accumulatedTranscriptRef.current = '';
            if (silenceTimeoutRef.current) {
                clearTimeout(silenceTimeoutRef.current);
                silenceTimeoutRef.current = null;
            }
        };

        recognition.onresult = (event: any) => {
            let interimTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const speechResult = event.results[i][0].transcript;

                if (event.results[i].isFinal) {
                    accumulatedTranscriptRef.current += speechResult;
                } else {
                    interimTranscript += speechResult;
                }
            }

            const displayText = accumulatedTranscriptRef.current + interimTranscript;
            setTranscript(displayText);
            console.log('[SimpleVoiceInput] Transcript:', displayText);

            // Start silence timer after detecting speech
            if (accumulatedTranscriptRef.current) {
                console.log('[SimpleVoiceInput] Speech detected, setting silence timeout');
                if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
                silenceTimeoutRef.current = setTimeout(() => {
                    console.log('[SimpleVoiceInput] Silence detected, stopping');
                    try { recognition.stop(); } catch (_) {}
                    silenceTimeoutRef.current = null;
                }, SILENCE_DELAY_MS);
            }
        };

        recognition.onerror = (event: any) => {
            console.error('[SimpleVoiceInput] Error:', event.error);

            // On no-speech error, silently restart if user is still holding the button
            if (event.error === 'no-speech') {
                console.log('[SimpleVoiceInput] No speech detected, restarting...');
                if (shouldListenRef.current) {
                    try { recognition.start(); } catch (_) {}
                }
                return;
            }

            // Handle other errors
            if (event.error === 'not-allowed') {
                setError("Microphone permission denied");
            } else if (event.error === 'audio-capture') {
                setError("No microphone found");
            } else {
                setError(`Error: ${event.error}`);
            }
            setIsListening(false);
            shouldListenRef.current = false;
        };

        recognition.onend = () => {
            console.log('[SimpleVoiceInput] Recognition ended');
            const finalText = accumulatedTranscriptRef.current.trim();

            if (finalText) {
                console.log('[SimpleVoiceInput] Sending transcript:', finalText);
                setIsListening(false);
                shouldListenRef.current = false;
                onTranscription(finalText);
                accumulatedTranscriptRef.current = '';
                setTranscript('');
            } else if (shouldListenRef.current) {
                console.log('[SimpleVoiceInput] No text collected, restarting...');
                try { recognition.start(); } catch (_) {}
            } else {
                console.log('[SimpleVoiceInput] Stopped listening');
                setIsListening(false);
                accumulatedTranscriptRef.current = '';
                setTranscript('');
            }

            if (silenceTimeoutRef.current) {
                clearTimeout(silenceTimeoutRef.current);
                silenceTimeoutRef.current = null;
            }
        };

        return () => {
            shouldListenRef.current = false;
            if (silenceTimeoutRef.current) {
                clearTimeout(silenceTimeoutRef.current);
                silenceTimeoutRef.current = null;
            }
            try { recognition.abort(); } catch (_) {}
        };
    }, [onTranscription, language]);

    const toggleListening = useCallback(() => {
        if (!recognitionRef.current) return;
        if (disabled) return;

        try {
            if (isListening) {
                console.log('[SimpleVoiceInput] Stopping...');
                shouldListenRef.current = false;
                recognitionRef.current.stop();
                setIsListening(false);
            } else {
                console.log('[SimpleVoiceInput] Starting...');
                // Stop any currently playing audio
                if (onRecordingStart) {
                    onRecordingStart();
                }
                shouldListenRef.current = true;
                setTranscript('');
                setError(null);
                accumulatedTranscriptRef.current = '';
                recognitionRef.current.start();
            }
        } catch (err) {
            console.error('[SimpleVoiceInput] Toggle error:', err);
        }
    }, [isListening, disabled, onRecordingStart]);

    const isOverlay = variant === 'overlay';
    const langBtnBase = isOverlay
        ? 'px-4 py-2 rounded-xl text-sm font-medium transition-all'
        : 'px-4 py-2 rounded-lg transition-all';
    const langBtnActive = isOverlay
        ? 'bg-gradient-to-r from-theme-accent to-theme-accentDim text-white shadow-lg shadow-theme-accent/30'
        : 'bg-theme-accent text-white';
    const langBtnInactive = isOverlay
        ? 'bg-white/10 text-white/70 border border-white/20 hover:bg-white/15 backdrop-blur-sm'
        : isDark
            ? 'bg-theme-card text-theme-muted border border-theme-cardBorder'
            : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-50';
    const micBtnListening = isOverlay
        ? 'bg-red-500/30 text-red-400 border-2 border-red-500/60 shadow-[0_0_30px_rgba(239,68,68,0.4)] animate-pulse'
        : 'bg-red-500/20 text-red-400 border border-red-500/50 animate-pulse';
    const micBtnIdle = isOverlay
        ? 'bg-white/10 text-white border-2 border-white/30 hover:bg-white/20 shadow-[0_0_25px_rgba(168,85,247,0.3)] hover:shadow-[0_0_35px_rgba(168,85,247,0.4)] backdrop-blur-sm'
        : navigateToAvatarOnMicClick
            ? isDark
                ? 'bg-theme-card text-theme-muted border border-theme-cardBorder hover:bg-theme-cardBorder/50'
                : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-100 shadow-sm'
            : isDark
                ? 'bg-theme-card text-theme-muted border border-theme-cardBorder hover:bg-theme-cardBorder/50'
                : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-100 shadow-sm';

    return (
        <div className="flex flex-col items-center gap-3">
            {/* Language Selector - hidden when mic navigates to avatar */}
            {!navigateToAvatarOnMicClick && (
                <div className="flex gap-2 text-sm">
                    <button
                        type="button"
                        onClick={() => {
                            setLanguage('en');
                            onLanguageChange?.('en');
                        }}
                        disabled={disabled || isListening}
                        className={`${langBtnBase} ${
                            language === 'en' ? langBtnActive : langBtnInactive
                        } ${disabled || isListening ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                    >
                        EN
                    </button>
                    <button
                        type="button"
                        onClick={() => {
                            setLanguage('ta');
                            onLanguageChange?.('ta');
                        }}
                        disabled={disabled || isListening}
                        className={`${langBtnBase} ${
                            language === 'ta' ? langBtnActive : langBtnInactive
                        } ${disabled || isListening ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                    >
                        TA
                    </button>
                </div>
            )}

            {/* Microphone Button - navigates to avatar or toggles recording */}
            <button
                type="button"
                disabled={disabled}
                onClick={navigateToAvatarOnMicClick ?? toggleListening}
                className={`rounded-full transition-all duration-300 flex items-center justify-center select-none
                    ${isOverlay ? 'p-5' : 'p-4'}
                    ${isListening ? micBtnListening : micBtnIdle}
                    ${disabled ? 'opacity-40 cursor-not-allowed pointer-events-none' : 'cursor-pointer'}
                `}
                title={navigateToAvatarOnMicClick ? "Go to Avatar Mode" : (isListening ? "Stop Listening" : "Start Voice Input")}
            >
                {isListening ? (
                    <svg className={`animate-bounce ${isOverlay ? 'w-7 h-7' : 'w-6 h-6'}`} fill="currentColor" viewBox="0 0 24 24">
                        <circle cx="12" cy="8" r="1.5" />
                        <circle cx="12" cy="16" r="1.5" />
                        <circle cx="12" cy="12" r="1.5" />
                    </svg>
                ) : (
                    <svg className={isOverlay ? 'w-7 h-7' : 'w-6 h-6'} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                )}
            </button>

            {/* Status Messages */}
            {error && (
                <div className="text-xs text-red-400 text-center px-2">
                    {error}
                </div>
            )}

            {transcript && isListening && (
                <div className="text-xs text-theme-muted text-center px-2 bg-theme-card/50 rounded p-1 max-w-xs">
                    <span className="text-white">{transcript}</span>
                </div>
            )}

            {isListening && !error && (
                <div className="text-xs text-theme-muted text-center">
                    Listening...
                </div>
            )}
        </div>
    );
};
