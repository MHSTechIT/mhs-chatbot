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

const BACKEND_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').trim();

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
    const [isTranscribing, setIsTranscribing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [transcript, setTranscript] = useState('');
    const [language, setLanguage] = useState<'en' | 'ta'>(parentLanguage || 'ta');
    useEffect(() => {
        if (parentLanguage) setLanguage(parentLanguage);
    }, [parentLanguage]);

    // iOS Safari's Web Speech API (webkitSpeechRecognition) is unreliable for both
    // Tamil and English — it silently fails, times out, or returns empty results.
    // On all iOS devices, use MediaRecorder → backend Gemini transcription instead.
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    const useMediaRecorder = isIOS;

    // ── Web Speech API refs ───────────────────────────────────────────────────
    const recognitionRef = useRef<SpeechRecognition | null>(null);
    const accumulatedTranscriptRef = useRef('');
    const silenceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const shouldListenRef = useRef(false);
    const SILENCE_DELAY_MS = 2000;

    // ── MediaRecorder refs (iOS Tamil) ────────────────────────────────────────
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);

    // ── Web Speech API initialisation ─────────────────────────────────────────
    useEffect(() => {
        type WebkitWindow = Window & { webkitSpeechRecognition?: typeof window.SpeechRecognition };
        const SpeechRecognition = window.SpeechRecognition ||
            (window as WebkitWindow).webkitSpeechRecognition;

        if (!SpeechRecognition) {
            setError(isIOS
                ? "Voice input not supported on this browser. Please type your question."
                : "Speech recognition not supported — use Chrome or Edge.");
            return;
        }

        // iOS Tamil uses MediaRecorder path — no need to init Web Speech API
        if (useMediaRecorder) return;

        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = language === 'ta' ? 'ta-IN' : 'en-IN';
        recognitionRef.current = recognition;

        recognition.onstart = () => {
            setIsListening(true);
            setError(null);
            setTranscript('');
            accumulatedTranscriptRef.current = '';
            if (silenceTimeoutRef.current) { clearTimeout(silenceTimeoutRef.current); silenceTimeoutRef.current = null; }
        };

        recognition.onresult = (event: SpeechRecognitionEvent) => {
            let interimTranscript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const speechResult = event.results[i][0].transcript;
                if (event.results[i].isFinal) { accumulatedTranscriptRef.current += speechResult; }
                else { interimTranscript += speechResult; }
            }
            const displayText = accumulatedTranscriptRef.current + interimTranscript;
            setTranscript(displayText);

            if (accumulatedTranscriptRef.current) {
                if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
                silenceTimeoutRef.current = setTimeout(() => {
                    try { recognition.stop(); } catch { /* ignore */ }
                    silenceTimeoutRef.current = null;
                }, SILENCE_DELAY_MS);
            }
        };

        recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
            console.error('[SimpleVoiceInput] Error:', event.error);
            if (event.error === 'no-speech' || event.error === 'aborted') {
                if (shouldListenRef.current) { try { recognition.start(); } catch { /* ignore */ } }
                return;
            }
            if (event.error === 'service-not-allowed') {
                setError("Voice recognition service unavailable — please type your question.");
            } else if (event.error === 'not-allowed') {
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
            const finalText = accumulatedTranscriptRef.current.trim();
            if (finalText) {
                setIsListening(false);
                shouldListenRef.current = false;
                onTranscription(finalText);
                accumulatedTranscriptRef.current = '';
                setTranscript('');
            } else if (shouldListenRef.current) {
                try { recognition.start(); } catch { /* ignore */ }
            } else {
                setIsListening(false);
                accumulatedTranscriptRef.current = '';
                setTranscript('');
            }
            if (silenceTimeoutRef.current) { clearTimeout(silenceTimeoutRef.current); silenceTimeoutRef.current = null; }
        };

        return () => {
            shouldListenRef.current = false;
            if (silenceTimeoutRef.current) { clearTimeout(silenceTimeoutRef.current); silenceTimeoutRef.current = null; }
            try { recognition.abort(); } catch { /* ignore */ }
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [onTranscription, language, useMediaRecorder]);

    // ── MediaRecorder helpers (iOS Tamil) ─────────────────────────────────────
    const startMediaRecording = useCallback(async () => {
        try {
            if (onRecordingStart) onRecordingStart();
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            // iOS Safari supports audio/mp4; Android/Chrome supports audio/webm
            const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                ? 'audio/webm;codecs=opus'
                : MediaRecorder.isTypeSupported('audio/mp4')
                    ? 'audio/mp4'
                    : 'audio/webm';

            const recorder = new MediaRecorder(stream, { mimeType });
            audioChunksRef.current = [];

            recorder.ondataavailable = (e) => {
                if (e.data.size > 0) audioChunksRef.current.push(e.data);
            };

            recorder.onstop = async () => {
                stream.getTracks().forEach(t => t.stop());
                const blob = new Blob(audioChunksRef.current, { type: mimeType });
                if (blob.size < 500) { setIsListening(false); return; }

                setIsTranscribing(true);
                setIsListening(false);
                try {
                    // Convert blob → base64
                    const arrayBuffer = await blob.arrayBuffer();
                    const bytes = new Uint8Array(arrayBuffer);
                    let binary = '';
                    bytes.forEach(b => { binary += String.fromCharCode(b); });
                    const base64 = btoa(binary);

                    const transcribeController = new AbortController();
                    const transcribeTimeout = setTimeout(() => transcribeController.abort(), 30000);
                    const resp = await fetch(`${BACKEND_URL}/transcribe`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ audio: base64, mime_type: mimeType }),
                        signal: transcribeController.signal,
                    });
                    clearTimeout(transcribeTimeout);
                    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                    const data = await resp.json();
                    if (data.text && data.text.trim()) {
                        onTranscription(data.text.trim());
                    } else {
                        setError("Couldn't hear anything — please try again.");
                    }
                } catch {
                    setError("Transcription failed. Please try again.");
                } finally {
                    setIsTranscribing(false);
                }
            };

            recorder.start();
            mediaRecorderRef.current = recorder;
            setIsListening(true);
            setError(null);
        } catch (err: unknown) {
            if (err instanceof Error && err.name === 'NotAllowedError') {
                setError("Microphone permission denied");
            } else {
                setError("Could not start recording");
            }
        }
    }, [onRecordingStart, onTranscription]);

    const stopMediaRecording = useCallback(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
            mediaRecorderRef.current.stop();
        }
    }, []);

    // ── Unified toggle ────────────────────────────────────────────────────────
    const toggleListening = useCallback(() => {
        if (disabled) return;

        if (useMediaRecorder) {
            if (isListening) { stopMediaRecording(); }
            else { startMediaRecording(); }
            return;
        }

        if (!recognitionRef.current) return;
        try {
            if (isListening) {
                shouldListenRef.current = false;
                recognitionRef.current.stop();
                setIsListening(false);
            } else {
                if (onRecordingStart) onRecordingStart();
                shouldListenRef.current = true;
                setTranscript('');
                setError(null);
                accumulatedTranscriptRef.current = '';
                recognitionRef.current.start();
            }
        } catch (err) {
            console.error('[SimpleVoiceInput] Toggle error:', err);
        }
    }, [isListening, disabled, onRecordingStart, useMediaRecorder, startMediaRecording, stopMediaRecording]);

    // ── Styles ────────────────────────────────────────────────────────────────
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
        : isDark
            ? 'bg-theme-card text-theme-muted border border-theme-cardBorder hover:bg-theme-cardBorder/50'
            : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-100 shadow-sm';
    const micBtnTranscribing = isOverlay
        ? 'bg-theme-accent/20 text-theme-accent border-2 border-theme-accent/40 animate-pulse backdrop-blur-sm'
        : 'bg-theme-accent/20 text-theme-accent border border-theme-accent/50 animate-pulse';

    return (
        <div className="flex flex-col items-center gap-3">
            {/* Language Selector - hidden when mic navigates to avatar */}
            {!navigateToAvatarOnMicClick && (
                <div className="flex gap-2 text-sm">
                    <button
                        type="button"
                        onClick={() => { setLanguage('en'); onLanguageChange?.('en'); }}
                        disabled={disabled || isListening || isTranscribing}
                        className={`${langBtnBase} ${language === 'en' ? langBtnActive : langBtnInactive} ${
                            disabled || isListening || isTranscribing ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                        }`}
                    >EN</button>
                    <button
                        type="button"
                        onClick={() => { setLanguage('ta'); onLanguageChange?.('ta'); }}
                        disabled={disabled || isListening || isTranscribing}
                        className={`${langBtnBase} ${language === 'ta' ? langBtnActive : langBtnInactive} ${
                            disabled || isListening || isTranscribing ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                        }`}
                    >TA</button>
                </div>
            )}

            {/* Microphone Button */}
            <button
                type="button"
                disabled={disabled || isTranscribing}
                onClick={navigateToAvatarOnMicClick ?? toggleListening}
                className={`rounded-full transition-all duration-300 flex items-center justify-center select-none
                    ${isOverlay ? 'p-5' : 'p-4'}
                    ${isTranscribing ? micBtnTranscribing : isListening ? micBtnListening : micBtnIdle}
                    ${disabled || isTranscribing ? 'opacity-40 cursor-not-allowed pointer-events-none' : 'cursor-pointer'}
                `}
                title={navigateToAvatarOnMicClick ? "Go to Avatar Mode" : isTranscribing ? "Transcribing..." : isListening ? "Tap to send" : "Start Voice Input"}
            >
                {isTranscribing ? (
                    <svg className={`animate-spin ${isOverlay ? 'w-7 h-7' : 'w-6 h-6'}`} fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                    </svg>
                ) : isListening ? (
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
                <div className="text-xs text-red-400 text-center px-2">{error}</div>
            )}
            {transcript && isListening && (
                <div className="text-xs text-theme-muted text-center px-2 bg-theme-card/50 rounded p-1 max-w-xs">
                    <span className="text-white">{transcript}</span>
                </div>
            )}
            {isTranscribing && (
                <div className="text-xs text-theme-accent text-center">Transcribing...</div>
            )}
            {isListening && !isTranscribing && !error && (
                <div className="text-xs text-theme-muted text-center">
                    {useMediaRecorder ? 'Recording — tap to send' : 'Listening...'}
                </div>
            )}
        </div>
    );
};
