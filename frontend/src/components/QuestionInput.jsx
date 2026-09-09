import React, { useState, useRef, useEffect } from 'react';
import { Send, CornerDownLeft, Sparkles, AlertCircle } from 'lucide-react';

export default function QuestionInput({ onSend, isLoading, disabled }) {
  const [query, setQuery] = useState('');
  const textareaRef = useRef(null);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!query.trim() || isLoading || disabled) return;
    onSend(query.trim());
    setQuery('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [query]);

  return (
    <form onSubmit={handleSubmit} style={{
      width: '100%',
      maxWidth: '820px',
      margin: '0 auto',
      position: 'relative'
    }}>
      <div style={{
        backgroundColor: 'var(--bg-input)',
        border: '1px solid var(--border-color)',
        borderRadius: 'var(--radius-lg)',
        padding: '8px 12px 8px 16px',
        display: 'flex',
        alignItems: 'flex-end',
        gap: '10px',
        boxShadow: 'var(--shadow-md)',
        transition: 'all 0.15s ease'
      }}
      onFocusCapture={(e) => {
        e.currentTarget.style.borderColor = 'var(--accent-sage)';
        e.currentTarget.style.boxShadow = '0 0 0 3px rgba(74, 107, 93, 0.12)';
      }}
      onBlurCapture={(e) => {
        e.currentTarget.style.borderColor = 'var(--border-color)';
        e.currentTarget.style.boxShadow = 'var(--shadow-md)';
      }}
      >
        <textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about a medicine..."
          rows={1}
          disabled={isLoading || disabled}
          style={{
            flex: 1,
            border: 'none',
            outline: 'none',
            backgroundColor: 'transparent',
            color: 'var(--text-primary)',
            fontSize: '0.96rem',
            fontFamily: 'var(--font-sans)',
            resize: 'none',
            padding: '6px 0',
            lineHeight: '1.45',
            maxHeight: '120px'
          }}
        />

        <button
          type="submit"
          disabled={!query.trim() || isLoading || disabled}
          title="Send Question (Enter)"
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '10px',
            backgroundColor: (!query.trim() || isLoading || disabled) ? 'var(--bg-hover)' : 'var(--accent-sage)',
            color: (!query.trim() || isLoading || disabled) ? 'var(--text-muted)' : 'var(--text-inverse)',
            border: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: (!query.trim() || isLoading || disabled) ? 'not-allowed' : 'pointer',
            transition: 'all 0.15s ease',
            flexShrink: 0,
            marginBottom: '2px'
          }}
        >
          <Send size={16} />
        </button>
      </div>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginTop: '6px',
        padding: '0 4px',
        fontSize: '0.73rem',
        color: 'var(--text-muted)'
      }}>
        <span>Press <kbd style={{ fontFamily: 'var(--font-mono)', padding: '1px 4px', background: 'var(--bg-hover)', borderRadius: '3px' }}>Enter</kbd> to send, <kbd style={{ fontFamily: 'var(--font-mono)', padding: '1px 4px', background: 'var(--bg-hover)', borderRadius: '3px' }}>Shift + Enter</kbd> for new line</span>
        <span>Answers derived only from verified drug label PDFs</span>
      </div>
    </form>
  );
}
