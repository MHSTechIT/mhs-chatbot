import React, { useState, useEffect, useCallback, useRef } from 'react';

const SILENCE_DELAY_MS = 2000;

interface VoiceAgentProps {
    onTranscription: (text: string) => void;
    disabled?: boolean;
}

export const VoiceAgent: React.FC<VoiceAgentProps> = ({ onTranscription, disabled }) => {
    const [isListening, setIsListening] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [audioLevel, setAudioLevel] = useState(0);
    const [transcript, setTranscript] = useState('');
    const [micOk, setMicOk] = useState<boolean | null>(null);

    const recognitionRef = useRef<any>(null);
    const accumulatedTranscriptRef = useRef('');
    const silenceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const shouldListenRef = useRef(false);
    const restartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Audio level monitoring refs
    const animFrameRef = useRef<number | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const audioCtxRef = useRef<AudioContext | null>(null);
    const streamRef = useRef<MediaStream | null>(null);

    const stopAudioMonitor = () => {
        if (animFrameRef.current) { cancelAnimationFrame(animFrameRef.current); animFrameRef.current = null; }
        if (streamRef.current) { streamRef.current.getTracks().forEach(t => t.stop()); streamRef.current = null; }
        if (audioCtxRef.current) { audioCtxRef.current.close().catch(() => {}); audioCtxRef.current = null; }
        analyserRef.current = null;
        setAudioLevel(0);
    };

    const startAudioMonitor = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            streamRef.current = stream;
            // If getUserMedia succeeded, mic is working
            setMicOk(true);

            const ctx = new AudioContext();
            audioCtxRef.current = ctx;
            const src = ctx.createMediaStreamSource(stream);
            const analyser = ctx.createAnalyser();
            analyser.fftSize = 512;
            src.connect(analyser);
            analyserRef.current = analyser;

            const tick = () => {
                if (!analyserRef.current) return;
                const data = new Uint8Array(analyserRef.current.frequencyBinCount);
                analyserRef.current.getByteFrequencyData(data);
                const avg = data.reduce((a, b) => a + b, 0) / data.length;
                const level = Math.min(100, avg * 2.5);
                setAudioLevel(level);
                animFrameRef.current = requestAnimationFrame(tick);
            };
            animFrameRef.current = requestAnimationFrame(tick);
        } catch (e) {
            setMicOk(false);
            setError("Cannot access microphone");
            console.error("Microphone access error:", e);
        }
    };

    const scheduleRestart = (recognition: any) => {
        if (restartTimerRef.current) return;
        restartTimerRef.current = setTimeout(() => {
            restartTimerRef.current = null;
            if (shouldListenRef.current) {
                try { recognition.start(); } catch (_) {}
            }
        }, 300);
    };

    useEffect(() => {
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (!SpeechRecognition) {
            setError("Speech recognition not supported - use Chrome browser");
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'en-US';
        recognition.maxAlternatives = 1;
        recognitionRef.current = recognition;

        recognition.onstart = () => {
            console.log('[VoiceAgent] Recognition started');
            setIsListening(true);
            setError(null);
            setTranscript('');
            accumulatedTranscriptRef.current = '';
            if (silenceTimeoutRef.current) { clearTimeout(silenceTimeoutRef.current); silenceTimeoutRef.current = null; }
        };

        recognition.onresult = (event: any) => {
            let interimTranscript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0]?.transcript || '';
                if (event.results[i].isFinal) {
                    accumulatedTranscriptRef.current += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }

            const displayText = accumulatedTranscriptRef.current + interimTranscript;
            setTranscript(displayText);

            if (accumulatedTranscriptRef.current) {
                console.log('[VoiceAgent] Speech detected:', accumulatedTranscriptRef.current);
                setMicOk(true);
                if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
                silenceTimeoutRef.current = setTimeout(() => {
                    try { recognition.stop(); } catch (_) {}
                    silenceTimeoutRef.current = null;
                }, SILENCE_DELAY_MS);
            }
        };

        recognition.onerror = (event: any) => {
            console.log('[VoiceAgent] Error:', event.error);
            if (event.error === 'no-speech') {
                scheduleRestart(recognition);
                return;
            }
            let msg = "Voice error - try again";
            if (event.error === 'not-allowed') msg = "Allow microphone in browser settings";
            else if (event.error === 'audio-capture') msg = "No microphone found";
            else if (event.error === 'network') msg = "Network error - check internet";
            setError(msg);
            setIsListening(false);
            shouldListenRef.current = false;
            stopAudioMonitor();
            setTimeout(() => setError(null), 4000);
        };

        recognition.onend = () => {
            console.log('[VoiceAgent] Recognition ended');
            const finalText = accumulatedTranscriptRef.current.trim();
            if (finalText) {
                console.log('[VoiceAgent] Final transcript:', finalText);
                setIsListening(false);
                shouldListenRef.current = false;
                stopAudioMonitor();
                onTranscription(finalText);
                accumulatedTranscriptRef.current = '';
                setTranscript('');
                if (silenceTimeoutRef.current) { clearTimeout(silenceTimeoutRef.current); silenceTimeoutRef.current = null; }
            } else if (shouldListenRef.current) {
                console.log('[VoiceAgent] No speech detected, restarting...');
                scheduleRestart(recognition);
            } else {
                console.log('[VoiceAgent] Stopped listening');
                setIsListening(false);
                stopAudioMonitor();
                accumulatedTranscriptRef.current = '';
                setTranscript('');
            }
        };

        return () => {
            shouldListenRef.current = false;
            if (restartTimerRef.current) { clearTimeout(restartTimerRef.current); restartTimerRef.current = null; }
            if (silenceTimeoutRef.current) { clearTimeout(silenceTimeoutRef.current); silenceTimeoutRef.current = null; }
            stopAudioMonitor();
            try { recognition.abort(); } catch (_) {}
        };
    }, [onTranscription]);

    const toggleListening = useCallback(() => {
        if (disabled || !recognitionRef.current) return;

        if (isListening) {
            console.log('[VoiceAgent] Stopping listening');
            shouldListenRef.current = false;
            if (restartTimerRef.current) { clearTimeout(restartTimerRef.current); restartTimerRef.current = null; }
            stopAudioMonitor();
            try { recognitionRef.current.stop(); } catch (_) {}
        } else {
            console.log('[VoiceAgent] Starting listening');
            shouldListenRef.current = true;
            setMicOk(null);
            accumulatedTranscriptRef.current = '';
            setTranscript('');
            startAudioMonitor();
            try {
                recognitionRef.current.start();
            } catch (err) {
                console.error("[VoiceAgent] Could not start recognition", err);
                shouldListenRef.current = false;
                stopAudioMonitor();
            }
        }
    }, [isListening, disabled]);

    const bar1 = Math.max(15, Math.min(100, audioLevel * 0.7));
    const bar2 = Math.max(25, Math.min(100, audioLevel * 1.1));
    const bar3 = Math.max(15, Math.min(100, audioLevel * 0.85));

    const tooltipMsg = (() => {
        if (error) return error;
        if (!isListening) return null;
        if (audioLevel > 15) return "Voice detected ✓";
        if (micOk === false) return "⚠ Mic not picking up audio";
        return "Listening... speak now";
    })();

    return (
        <div className="w-full space-y-2">
            <div className="relative flex items-center justify-center">
                <button
                    type="button"
                    disabled={disabled}
                    onClick={toggleListening}
                    className={`p-3 rounded-full transition-all duration-300 shadow-sm
              ${isListening
                            ? audioLevel > 15
                                ? 'bg-green-500/20 text-green-400 border border-green-500/50'
                                : 'bg-red-500/20 text-red-400 border border-red-500/50'
                            : 'bg-theme-card text-theme-muted border border-theme-cardBorder hover:bg-theme-cardBorder/50'
                        }
              ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                    title={isListening ? "Stop Listening" : "Start Voice Input"}
                >
                    {isListening ? (
                        <div className="flex items-end justify-center gap-0.5 w-6 h-6">
                            <div className={`w-1.5 rounded-full transition-all duration-75 ${audioLevel > 10 ? 'bg-green-400' : 'bg-red-400'}`}
                                style={{ height: `${bar1}%` }} />
                            <div className={`w-1.5 rounded-full transition-all duration-75 ${audioLevel > 10 ? 'bg-green-400' : 'bg-red-400'}`}
                                style={{ height: `${bar2}%` }} />
                            <div className={`w-1.5 rounded-full transition-all duration-75 ${audioLevel > 10 ? 'bg-green-400' : 'bg-red-400'}`}
                                style={{ height: `${bar3}%` }} />
                        </div>
                    ) : (
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                        </svg>
                    )}
                </button>

                {tooltipMsg && (
                    <div className={`absolute -top-10 whitespace-nowrap px-3 py-1 rounded-md text-xs font-medium shadow-sm
              ${error || micOk === false ? 'bg-red-500/90 text-white' : audioLevel > 15 ? 'bg-green-600/90 text-white' : 'bg-theme-card border border-theme-cardBorder text-white'}`}>
                        {tooltipMsg}
                        <div className={`absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 rotate-45
                ${error || micOk === false ? 'bg-red-500/90' : audioLevel > 15 ? 'bg-green-600/90' : 'bg-theme-card'}`} />
                    </div>
                )}
            </div>

            {/* Show live transcript */}
            {transcript && isListening && (
                <div className="px-3 py-2 rounded-md bg-theme-card border border-theme-cardBorder text-sm text-theme-muted">
                    <p className="text-white">{transcript}</p>
                </div>
            )}
        </div>
    );
};
