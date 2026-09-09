import React from 'react';
import { User } from 'lucide-react';

export default function UserMessage({ message, timestamp }) {
  return (
    <div className="animate-fade-in" style={{
      display: 'flex',
      justifyContent: 'flex-end',
      marginBottom: '20px',
      paddingLeft: '40px'
    }}>
      <div style={{
        maxWidth: '85%',
        display: 'flex',
        gap: '12px',
        alignItems: 'flex-start',
        flexDirection: 'row-reverse'
      }}>
        <div style={{
          width: '32px',
          height: '32px',
          borderRadius: '50%',
          backgroundColor: 'var(--bg-hover)',
          color: 'var(--text-secondary)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid var(--border-color)',
          flexShrink: 0
        }}>
          <User size={16} />
        </div>

        <div style={{
          backgroundColor: 'var(--bg-surface-subtle)',
          border: '1px solid var(--border-color)',
          borderRadius: '16px 4px 16px 16px',
          padding: '12px 18px',
          boxShadow: 'var(--shadow-sm)'
        }}>
          <p style={{
            fontSize: '0.95rem',
            color: 'var(--text-primary)',
            lineHeight: 1.5,
            whiteSpace: 'pre-wrap',
            fontWeight: 450
          }}>
            {message.text}
          </p>
          {timestamp && (
            <div style={{
              fontSize: '0.7rem',
              color: 'var(--text-muted)',
              marginTop: '4px',
              textAlign: 'right'
            }}>
              {timestamp}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
