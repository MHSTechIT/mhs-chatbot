import type { IChatService } from "./IChatService";
import { ServiceStatusCode, type ServiceResult, type ServiceStatusCodeType } from "../../models/ServiceResult";
import type { AskRequest } from "../../BOs/AskRequest/AskRequest";
import type { AskResponse } from "../../BOs/AskResponse/AskResponse";

// Helper function to clean markdown and emojis for TTS compatibility
function cleanTextForTTS(text: string): string {
    if (!text) return text;

    // Remove markdown headers
    text = text.replace(/#+\s*/g, '');
    // Remove bold/italic markers
    text = text.replace(/\*\*(.+?)\*\*/g, '$1');
    text = text.replace(/__(.+?)__/g, '$1');
    text = text.replace(/[*_]/g, '');
    // Remove brackets and links
    text = text.replace(/\[(.+?)\]/g, '$1');
    text = text.replace(/\(.+?\)/g, '');
    // Remove emojis (comprehensive emoji patterns)
    text = text.replace(/[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]|[\u{2500}-\u{2BEF}]|[\u{1F900}-\u{1F9FF}]|[\u{1F018}-\u{1F270}]/gu, '');
    // Remove extra spaces
    text = text.replace(/\s+/g, ' ').trim();

    return text;
}

export class ChatService implements IChatService {
    async ask(request: AskRequest): Promise<ServiceResult<AskResponse>> {
        try {

            // Get API URL from environment variables
            const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const apiUrl = `${baseUrl}/ask`;

            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(request),
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`Backend returned status ${response.status}: ${errorText}`);

                let statusCode: ServiceStatusCodeType = ServiceStatusCode.ServiceException;
                if (response.status === 400) statusCode = ServiceStatusCode.BadRequest;
                if (response.status === 401) statusCode = ServiceStatusCode.Unauthorized;
                if (response.status === 403) statusCode = ServiceStatusCode.Forbidden;
                if (response.status === 404) statusCode = ServiceStatusCode.NotFound;
                if (response.status === 500) statusCode = ServiceStatusCode.InternalServerError;

                let errorMessage = `API request failed with status ${response.status}`;
                try {
                    const errorObj = JSON.parse(errorText);
                    if (errorObj && errorObj.detail) {
                        errorMessage = typeof errorObj.detail === 'string' ? errorObj.detail : JSON.stringify(errorObj.detail);
                    }
                } catch (e) {
                    // Ignore JSON parse errors, fallback to generic message plus some text
                    if (errorText.length > 0 && errorText.length < 200) {
                        errorMessage += `: ${errorText}`;
                    }
                }

                return {
                    statusCode: statusCode,
                    message: errorMessage,
                    content: null
                };
            }

            const data: AskResponse = await response.json();
            // Clean markdown and emojis from answer for TTS compatibility
            if (data.answer) {
                data.answer = cleanTextForTTS(data.answer);
            }
            return {
                statusCode: ServiceStatusCode.OK,
                message: "Success",
                content: data
            };
        } catch (error: unknown) {
            console.error('Error connecting to the backend API over network:', error);
            return {
                statusCode: ServiceStatusCode.NetworkFailure,
                message: (error as Error).message || "Network failure",
                content: null
            };
        }
    }
}
