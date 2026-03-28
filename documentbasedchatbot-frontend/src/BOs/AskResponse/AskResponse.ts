export type AnswerType = "normal" | "restricted" | "not_found";

export interface AskResponse {
    answer: string;
    type: AnswerType;
    audio_url?: string;  // ElevenLabs TTS audio URL (optional)
}
