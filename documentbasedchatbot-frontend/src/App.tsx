import React, { useState } from 'react';
import { ChatContainer } from './components/ChatContainer';
import { AvatarPage } from './pages/AvatarPage';
import { ConversationProvider } from './contexts/ConversationContext';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';

const AppContent: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<'chat' | 'avatar'>('avatar');
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <div className={`min-h-screen h-screen flex flex-col selection:bg-theme-accent/30 selection:text-white font-sans overflow-hidden transition-colors ${
      isDark ? 'bg-theme-base text-white' : 'bg-white text-gray-900'
    }`}>
        {/* Page Content */}
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          {currentPage === 'chat' ? (
            <ChatContainer onAvatarClick={() => setCurrentPage('avatar')} />
          ) : (
            <AvatarPage onBackClick={() => setCurrentPage('chat')} />
          )}
        </div>
      </div>
  );
};

const App: React.FC = () => (
  <ThemeProvider>
    <ConversationProvider>
      <AppContent />
    </ConversationProvider>
  </ThemeProvider>
);

export default App;
