/**
 * ChatHistorySidebar — the left panel listing saved conversations.
 * Each chat has a right-click (or ⋯) menu with Open / Rename / Delete. Renaming
 * edits the title inline. Sessions are stored in the browser (localStorage).
 */
import React, { useState, useEffect } from 'react';
import { MessageSquare, Trash2, Clock, FileText, ChevronLeft, RefreshCw, Pencil, Check, MoreVertical, FolderOpen } from 'lucide-react';

export default function ChatHistorySidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onDeleteSession,
  onClearAllSessions,
  onRenameSession,
  isOpen,
  onClose
}) {
  const [editingId, setEditingId] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [menu, setMenu] = useState(null); // { id, x, y }

  // Close the context menu on any outside click or Escape.
  useEffect(() => {
    if (!menu) return;
    const close = () => setMenu(null);
    const onKey = (e) => { if (e.key === 'Escape') setMenu(null); };
    window.addEventListener('click', close);
    window.addEventListener('keydown', onKey);
    return () => { window.removeEventListener('click', close); window.removeEventListener('keydown', onKey); };
  }, [menu]);

  if (!isOpen) return null;

  const startEdit = (session) => {
    setEditingId(session.id);
    setEditValue(session.title || '');
  };
  const commitEdit = () => {
    if (editingId && onRenameSession) {
      const name = editValue.trim();
      if (name) onRenameSession(editingId, name);
    }
    setEditingId(null);
    setEditValue('');
  };

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
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700, color: 'var(--text-primary)', fontSize: '1.1rem' }}>
          <Clock size={20} style={{ color: 'var(--accent-sage)' }} />
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
                onContextMenu={(e) => { e.preventDefault(); e.stopPropagation(); setMenu({ id: session.id, x: e.clientX, y: e.clientY }); }}
                style={{
                  backgroundColor: isActive ? 'var(--accent-sage-light)' : 'var(--bg-surface)',
                  border: `1px solid ${isActive ? 'var(--accent-sage-border)' : 'var(--border-subtle)'}`,
                  borderRadius: 'var(--radius-md)',
                  padding: '14px 16px',
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
                  {editingId === session.id ? (
                    <input
                      autoFocus
                      value={editValue}
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => setEditValue(e.target.value)}
                      onBlur={commitEdit}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') commitEdit();
                        if (e.key === 'Escape') { setEditingId(null); setEditValue(''); }
                      }}
                      style={{
                        width: '100%',
                        fontSize: '1rem',
                        fontWeight: 700,
                        color: 'var(--text-primary)',
                        border: '1px solid var(--accent-sage)',
                        borderRadius: '6px',
                        padding: '4px 8px',
                        outline: 'none'
                      }}
                    />
                  ) : (
                    <div style={{
                      fontSize: '1rem',
                      fontWeight: isActive ? 700 : 600,
                      color: isActive ? 'var(--accent-sage-dark)' : 'var(--text-primary)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      lineHeight: 1.35
                    }}>
                      {session.title || 'Untitled Chat'}
                    </div>
                  )}

                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    marginTop: '6px',
                    fontSize: '0.84rem',
                    color: 'var(--text-muted)'
                  }}>
                    <FileText size={14} style={{ color: 'var(--accent-sage)' }} />
                    <span style={{ textTransform: 'uppercase', fontWeight: 600 }}>
                      {session.selectedDrug || 'RINVOQ'}
                    </span>
                    <span>•</span>
                    <span>{session.formattedDate || 'Recent'}</span>
                  </div>
                </div>

                {editingId === session.id ? (
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); commitEdit(); }}
                    title="Save name"
                    style={{ background: 'transparent', border: 'none', color: 'var(--accent-sage)', cursor: 'pointer', padding: '4px', borderRadius: '4px', display: 'flex', flexShrink: 0 }}
                  >
                    <Check size={18} />
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); setMenu({ id: session.id, x: e.clientX, y: e.clientY }); }}
                    title="Options"
                    style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px', borderRadius: '4px', opacity: 0.7, display: 'flex', flexShrink: 0 }}
                    onMouseEnter={(e) => e.currentTarget.style.color = 'var(--text-primary)'}
                    onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                  >
                    <MoreVertical size={18} />
                  </button>
                )}
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
              padding: '10px 14px',
              fontSize: '0.92rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            <RefreshCw size={15} />
            <span>Clear All History</span>
          </button>
        </div>
      )}

      {/* Right-click / ⋯ context menu: Open · Rename · Delete */}
      {menu && (() => {
        const session = sessions.find(s => s.id === menu.id);
        if (!session) return null;
        const item = (icon, label, onClick, danger) => (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); setMenu(null); onClick(); }}
            style={{
              display: 'flex', alignItems: 'center', gap: '10px', width: '100%',
              background: 'transparent', border: 'none', textAlign: 'left',
              padding: '9px 14px', fontSize: '0.92rem', fontWeight: 500, cursor: 'pointer',
              color: danger ? 'var(--accent-red, #B4453C)' : 'var(--text-primary)'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--bg-surface-subtle)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            {icon}<span>{label}</span>
          </button>
        );
        return (
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              position: 'fixed',
              top: Math.min(menu.y, window.innerHeight - 150),
              left: Math.min(menu.x, window.innerWidth - 180),
              width: 170,
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              borderRadius: '10px',
              boxShadow: 'var(--shadow-lg)',
              padding: '6px',
              zIndex: 2000
            }}
          >
            {item(<FolderOpen size={16} />, 'Open', () => onSelectSession(session.id))}
            {item(<Pencil size={16} />, 'Rename', () => startEdit(session))}
            <div style={{ height: 1, backgroundColor: 'var(--border-subtle)', margin: '4px 0' }} />
            {item(<Trash2 size={16} />, 'Delete', () => onDeleteSession(session.id), true)}
          </div>
        );
      })()}
    </aside>
  );
}
