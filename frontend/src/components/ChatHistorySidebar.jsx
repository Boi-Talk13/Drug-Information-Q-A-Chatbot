import React from 'react';
import { MessageSquare, Trash2, Clock, FileText, ChevronLeft, RefreshCw } from 'lucide-react';

export default function ChatHistorySidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onDeleteSession,
  onClearAllSessions,
  isOpen,
  onClose
}) {
  if (!isOpen) return null;

  return (
    <aside style={{
      width: '270px',
      height: '100%',
      backgroundColor: 'var(--bg-sidebar)',
      borderRight: '1px solid var(--border-color)',
      display: 'flex',
      flexDirection: 'column',
      boxShadow: 'var(--shadow-md)',
      zIndex: 60,
      flexShrink: 0,
      transition: 'all 0.25s ease-in-out'
    }}>
      {/* Sidebar Header Bar */}
      <div style={{
        padding: '16px',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        backgroundColor: 'var(--bg-surface)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.92rem' }}>
          <Clock size={16} style={{ color: 'var(--accent-sage)' }} />
          <span>Chat History</span>
        </div>

        <button
          type="button"
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            padding: '4px',
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title="Collapse Sidebar"
        >
          <ChevronLeft size={18} />
        </button>
      </div>

      {/* History List */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px'
      }}>
        {sessions.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '30px 14px',
            color: 'var(--text-muted)',
            fontSize: '0.82rem'
          }}>
            <MessageSquare size={24} style={{ opacity: 0.4, marginBottom: '8px' }} />
            <p>No saved conversations yet.</p>
            <p style={{ fontSize: '0.75rem', marginTop: '4px' }}>Ask a question to start a chat session.</p>
          </div>
        ) : (
          sessions.map((session) => {
            const isActive = session.id === activeSessionId;
            return (
              <div
                key={session.id}
                onClick={() => onSelectSession(session.id)}
                style={{
                  backgroundColor: isActive ? 'var(--accent-sage-light)' : 'var(--bg-surface)',
                  border: `1px solid ${isActive ? 'var(--accent-sage-border)' : 'var(--border-subtle)'}`,
                  borderRadius: 'var(--radius-md)',
                  padding: '10px 12px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  gap: '8px',
                  transition: 'all 0.15s ease',
                  position: 'relative'
                }}
              >
                <div style={{ flex: 1, overflow: 'hidden' }}>
                  <div style={{
                    fontSize: '0.84rem',
                    fontWeight: isActive ? 600 : 450,
                    color: isActive ? 'var(--accent-sage-dark)' : 'var(--text-primary)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    lineHeight: 1.3
                  }}>
                    {session.title || 'Untitled Chat'}
                  </div>

                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    marginTop: '4px',
                    fontSize: '0.72rem',
                    color: 'var(--text-muted)'
                  }}>
                    <FileText size={11} style={{ color: 'var(--accent-sage)' }} />
                    <span style={{ textTransform: 'uppercase', fontWeight: 600 }}>
                      {session.selectedDrug || 'RINVOQ'}
                    </span>
                    <span>•</span>
                    <span>{session.formattedDate || 'Recent'}</span>
                  </div>
                </div>

                {/* Delete Individual Chat Button */}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteSession(session.id);
                  }}
                  title="Delete conversation"
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    padding: '3px',
                    borderRadius: '4px',
                    opacity: isActive ? 0.9 : 0.5,
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-red)'}
                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                >
                  <Trash2 size={13} />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Sidebar Footer / Clear All */}
      {sessions.length > 0 && (
        <div style={{
          padding: '12px 16px',
          borderTop: '1px solid var(--border-color)',
          backgroundColor: 'var(--bg-surface)'
        }}>
          <button
            type="button"
            onClick={onClearAllSessions}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              backgroundColor: 'transparent',
              border: '1px solid var(--border-color)',
              color: 'var(--text-secondary)',
              borderRadius: 'var(--radius-sm)',
              padding: '6px 10px',
              fontSize: '0.78rem',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            <RefreshCw size={12} />
            <span>Clear All History</span>
          </button>
        </div>
      )}
    </aside>
  );
}
