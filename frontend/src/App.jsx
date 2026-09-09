import React, { useState } from 'react';
import LandingPage from './components/LandingPage';
import ChatScreen from './components/ChatScreen';

export default function App() {
  const [currentView, setCurrentView] = useState('landing');

  if (currentView === 'landing') {
    return <LandingPage onGetStarted={() => setCurrentView('chat')} />;
  }

  return <ChatScreen onBackToLanding={() => setCurrentView('landing')} />;
}
