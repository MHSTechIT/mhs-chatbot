import React, { useState } from 'react';

/**
 * Props for the TextInput component.
 */
interface TextInputProps {
    /** Callback triggered when the user submits a text message */
    onSend: (text: string) => void;
    /** Disables the input field when the app is processing a request */
    disabled?: boolean;
    /** Dark mode styling */
    isDark?: boolean;
}

/**
 * A controlled input component allowing users to type and submit questions manually.
 * 
 * @component
 */
export const TextInput: React.FC<TextInputProps> = ({ onSend, disabled, isDark = true }) => {
    const [input, setInput] = useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (input.trim() && !disabled) {
            onSend(input.trim());
            setInput('');
        }
    };

    return (
        <form onSubmit={handleSubmit} className={`flex-1 flex items-center rounded-full border shadow-sm px-2 overflow-hidden focus-within:border-theme-accent focus-within:ring-1 focus-within:ring-theme-accent transition-all ${
            isDark ? 'bg-theme-card border-theme-cardBorder' : 'bg-white border-gray-200'
        }`}>
            <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your question..."
                className={`flex-1 py-3 px-4 outline-none bg-transparent text-[15px] ${
                    isDark ? 'text-white placeholder-theme-muted' : 'text-gray-900 placeholder-gray-400'
                }`}
                disabled={disabled}
            />
            <button
                type="submit"
                disabled={!input.trim() || disabled}
                className={`p-2 m-1 rounded-full transition-colors ${
                    isDark
                        ? 'bg-theme-accent text-white hover:bg-theme-accentDim disabled:bg-theme-cardBorder disabled:text-theme-muted'
                        : 'bg-violet-600 text-white hover:bg-violet-700 disabled:bg-gray-200 disabled:text-gray-400'
                }`}
                title="Send Message"
            >
                <svg className="w-5 h-5 ml-[2px]" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
            </button>
        </form>
    );
};
