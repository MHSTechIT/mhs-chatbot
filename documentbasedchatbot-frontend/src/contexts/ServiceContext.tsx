import React, { createContext, useContext, type ReactNode } from 'react';
import type { IChatService } from '../services/ChatService/IChatService';
import { ChatService } from '../services/ChatService/ChatService';

interface ServiceContextType {
    chatService: IChatService;
}

const ServiceContext = createContext<ServiceContextType | undefined>(undefined);

export const ServiceProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    // Instantiate services here. In a more complex app, this might involve more setup.
    const chatService = new ChatService();

    return (
        <ServiceContext.Provider value={{ chatService }}>
            {children}
        </ServiceContext.Provider>
    );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useServices = (): ServiceContextType => {
    const context = useContext(ServiceContext);
    if (!context) {
        throw new Error("useServices must be used within a ServiceProvider");
    }
    return context;
};
