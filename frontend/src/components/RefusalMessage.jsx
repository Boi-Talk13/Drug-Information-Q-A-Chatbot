/**
 * RefusalMessage — shown when the bot safely declines: no matching document,
 * out-of-scope question, or nothing found in the label. This is the Responsible-AI
 * moment (the bot knows when NOT to answer) rather than guessing.
 */
import React from 'react';
import { HelpCircle, ShieldAlert, Info } from 'lucide-react';

export default function RefusalMessage({ message }) {
  const { refusal_reason, drug_name } = message;

  return (
    <div className="animate-fade-in" style={{
      display: 'flex',
      justifyContent: 'flex-start',
      marginBottom: '24px',
      paddingRight: '20px'
    }}>
      <div style={{
        maxWidth: '90%',
        display: 'flex',
        gap: '14px',
        alignItems: 'flex-start'
      }}>
        {/* Refusal Avatar Badge */}
        <div style={{
          width: '34px',
          height: '34px',
          borderRadius: '10px',
          backgroundColor: 'var(--accent-amber-light)',
          color: 'var(--accent-amber)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid var(--accent-amber-border)',
          flexShrink: 0,
          boxShadow: 'var(--shadow-sm)'
        }}>
          <HelpCircle size={18} />
        </div>

        {/* Refusal Card */}
        <div style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--accent-amber-border)',
          borderRadius: '4px 16px 16px 16px',
          padding: '18px 22px',
          boxShadow: 'var(--shadow-md)',
          width: '100%'
        }}>
          {/* Header Badge */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '10px'
          }}>
            <span style={{
              fontSize: '0.72rem',
              fontWeight: 700,
              padding: '3px 8px',
              borderRadius: '4px',
              backgroundColor: 'var(--accent-amber-light)',
              color: 'var(--accent-amber)',
              border: '1px solid var(--accent-amber-border)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}>
              <ShieldAlert size={12} />
              Responsible AI Safeguard — Hallucination Prevention
            </span>
          </div>

          <h3 style={{
            fontSize: '1.05rem',
            fontWeight: 650,
            color: 'var(--text-primary)',
            marginBottom: '6px',
            letterSpacing: '-0.01em'
          }}>
            I don't know based on the available documents.
          </h3>

          <p style={{
            fontSize: '0.92rem',
            color: 'var(--text-secondary)',
            lineHeight: 1.55,
            marginBottom: '12px'
          }}>
            The available prescribing documents do not contain explicit information to answer this question accurately. MedCite is strictly configured never to guess or make up medical facts.
          </p>

          {refusal_reason && (
            <div style={{
              backgroundColor: 'var(--bg-surface-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '10px 14px',
              fontSize: '0.82rem',
              color: 'var(--text-secondary)',
              borderLeft: '3px solid var(--accent-amber)',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px'
            }}>
              <Info size={15} style={{ color: 'var(--accent-amber)', flexShrink: 0, marginTop: '2px' }} />
              <span>{refusal_reason}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
