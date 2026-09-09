import React, { useState, useRef, useEffect } from 'react';
import ChatHeader from './ChatHeader';
import ChatHistorySidebar from './ChatHistorySidebar';
import UserMessage from './UserMessage';
import AssistantMessage from './AssistantMessage';
import RefusalMessage from './RefusalMessage';
import LoadingMessage from './LoadingMessage';
import QuestionInput from './QuestionInput';
import SuggestedQuestion from './SuggestedQuestion';
import SafetyDisclaimer from './SafetyDisclaimer';
import PdfViewerPanel from './PdfViewerPanel';
import { sendQuestion, getAvailableDrugs } from '../services/apiService';

const STORAGE_KEY = 'medcite_chat_sessions_v1';

export default function ChatScreen({ onBackToLanding, initialDrug = 'rinvoq' }) {
  const [sessions, setSessions] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      console.warn('Failed to load chat history from localStorage:', e);
      return [];
    }
  });

  const [activeSessionId, setActiveSessionId] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.length > 0) return parsed[0].id;
      }
    } catch (e) {}
    return null;
  });

  const [messages, setMessages] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.length > 0) return parsed[0].messages || [];
      }
    } catch (e) {}
    return [];
  });

  const [isLoading, setIsLoading] = useState(false);
  const [selectedDrug, setSelectedDrug] = useState(initialDrug);
  const [useLiveApi, setUseLiveApi] = useState(false);

  // History Sidebar visible default on wide screens
  const [showHistorySidebar, setShowHistorySidebar] = useState(window.innerWidth >= 1200);
  // Default PDF viewer to open beside chat on desktop screens (width >= 1024px)
  const [showPdfPanel, setShowPdfPanel] = useState(window.innerWidth >= 1024);
  const [activeCitation, setActiveCitation] = useState(null);

  const chatScrollRef = useRef(null);
  const drugs = getAvailableDrugs();
  const currentDrugObj = drugs.find(d => d.id === selectedDrug) || drugs[0];

  // Helper to persist sessions to localStorage & update state
  const persistSessions = (updatedSessions) => {
    setSessions(updatedSessions);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedSessions));
    } catch (e) {
      console.warn('Failed to save chat sessions to localStorage:', e);
    }
  };

  // Auto-scroll chat window to bottom on new messages
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTo({
        top: chatScrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, isLoading]);

  // Handle starting a + New Chat (Top Header Button)
  const handleNewChat = () => {
    setActiveSessionId(null);
    setMessages([]);
    setSelectedDrug('rinvoq');
    setActiveCitation(null);
  };

  // Handle selecting a chat session from history sidebar
  const handleSelectSession = (sessionId) => {
    const targetSession = sessions.find(s => s.id === sessionId);
    if (targetSession) {
      setActiveSessionId(sessionId);
      setMessages(targetSession.messages || []);
      if (targetSession.selectedDrug) {
        setSelectedDrug(targetSession.selectedDrug);
      }
      setActiveCitation(null);
    }
  };

  // Handle deleting an individual chat session
  const handleDeleteSession = (sessionId) => {
    const updated = sessions.filter(s => s.id !== sessionId);
    persistSessions(updated);

    if (activeSessionId === sessionId) {
      if (updated.length > 0) {
        setActiveSessionId(updated[0].id);
        setMessages(updated[0].messages || []);
        if (updated[0].selectedDrug) setSelectedDrug(updated[0].selectedDrug);
      } else {
        handleNewChat();
      }
    }
  };

  // Handle clearing all chat sessions
  const handleClearAllSessions = () => {
    persistSessions([]);
    handleNewChat();
  };

  // Clear current active conversation stream
  const handleClearCurrentChat = () => {
    if (activeSessionId) {
      handleDeleteSession(activeSessionId);
    } else {
      setMessages([]);
    }
  };

  const handleSendQuestion = async (questionText) => {
    const userMsg = {
      id: Date.now(),
      role: 'user',
      text: questionText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const newMessagesList = [...messages, userMsg];
    setMessages(newMessagesList);

    // Immediately create or update session in sidebar on first user message
    let currentSessionId = activeSessionId;
    let updatedSessions = [...sessions];

    if (!currentSessionId) {
      currentSessionId = 'sess_' + Date.now();
      setActiveSessionId(currentSessionId);

      const newSessionObj = {
        id: currentSessionId,
        title: questionText.length > 50 ? questionText.substring(0, 50) + '...' : questionText,
        selectedDrug,
        createdAt: new Date().toISOString(),
        formattedDate: new Date().toLocaleDateString([], { month: 'short', day: 'numeric' }),
        messages: newMessagesList
      };

      updatedSessions = [newSessionObj, ...updatedSessions];
    } else {
      updatedSessions = updatedSessions.map(s => {
        if (s.id === currentSessionId) {
          return {
            ...s,
            messages: newMessagesList,
            selectedDrug
          };
        }
        return s;
      });
    }

    persistSessions(updatedSessions);
    setIsLoading(true);

    try {
      const history = messages.map(m => ({ role: m.role, text: m.text }));

      const response = await sendQuestion({
        question: questionText,
        conversationHistory: history,
        selectedDrug,
        useLiveApi
      });

      const assistantMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        text: response.answer,
        citations: response.citations || [],
        section: response.section,
        is_advice: response.is_advice || false,
        is_refusal: response.is_refusal || false,
        refusal_reason: response.refusal_reason,
        drug_name: response.drug_name || currentDrugObj.name,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      const finalMessagesList = [...newMessagesList, assistantMsg];
      setMessages(finalMessagesList);

      // Persist assistant message response into current session
      const sessionsWithAnswer = updatedSessions.map(s => {
        if (s.id === currentSessionId) {
          return {
            ...s,
            messages: finalMessagesList
          };
        }
        return s;
      });

      persistSessions(sessionsWithAnswer);

    } catch (err) {
      const errorMsgObj = {
        id: Date.now() + 1,
        role: 'assistant',
        is_refusal: true,
        refusal_reason: 'Network error or backend API unavailable.',
        text: "I don't know based on the available documents. An error occurred while retrieving document evidence.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorMsgObj]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCitationClick = (citationObj) => {
    setActiveCitation(citationObj);
    setShowPdfPanel(true);
  };

  return (
    <div className="app-container">
      {/* Header Bar */}
      <ChatHeader
        selectedDrug={selectedDrug}
        onSelectDrug={setSelectedDrug}
        useLiveApi={useLiveApi}
        onToggleLiveApi={() => setUseLiveApi(!useLiveApi)}
        showPdfPanel={showPdfPanel}
        onTogglePdfPanel={() => setShowPdfPanel(!showPdfPanel)}
        showHistorySidebar={showHistorySidebar}
        onToggleHistorySidebar={() => setShowHistorySidebar(!showHistorySidebar)}
        onNewChat={handleNewChat}
        onClearChat={handleClearCurrentChat}
        isChatEmpty={messages.length === 0}
        onBackToLanding={onBackToLanding}
      />

      {/* Main Content Body */}
      <div className="main-content">
        {/* Left Chat History Sidebar */}
        <ChatHistorySidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={handleSelectSession}
          onDeleteSession={handleDeleteSession}
          onClearAllSessions={handleClearAllSessions}
          isOpen={showHistorySidebar}
          onClose={() => setShowHistorySidebar(false)}
        />

        {/* Center Chat Conversation Stream */}
        <div className={`chat-panel ${showPdfPanel ? 'with-sidebar' : ''}`}>
          <div
            ref={chatScrollRef}
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '24px 20px 40px 20px'
            }}
          >
            {messages.length === 0 ? (
              <SuggestedQuestion
                onSelectQuestion={handleSendQuestion}
                selectedDrugName={currentDrugObj.name}
              />
            ) : (
              <div style={{ maxWidth: '820px', margin: '0 auto' }}>
                {messages.map(msg => {
                  if (msg.role === 'user') {
                    return <UserMessage key={msg.id} message={msg} timestamp={msg.timestamp} />;
                  }
                  if (msg.is_refusal) {
                    return <RefusalMessage key={msg.id} message={msg} />;
                  }
                  return (
                    <AssistantMessage
                      key={msg.id}
                      message={msg}
                      onCitationClick={handleCitationClick}
                    />
                  );
                })}

                {isLoading && <LoadingMessage />}
              </div>
            )}
          </div>

          {/* Bottom Question Input Bar */}
          <div style={{
            padding: '16px 20px',
            backgroundColor: 'var(--bg-canvas)',
            borderTop: '1px solid var(--border-subtle)'
          }}>
            <QuestionInput
              onSend={handleSendQuestion}
              isLoading={isLoading}
            />
          </div>

          {/* Responsible AI Footer Disclaimer */}
          <SafetyDisclaimer />
        </div>

        {/* Right PDF Reader Side Panel */}
        {showPdfPanel && (
          <PdfViewerPanel
            activeCitation={activeCitation}
            selectedDrug={selectedDrug}
            onClose={() => setShowPdfPanel(false)}
          />
        )}
      </div>
    </div>
  );
}
