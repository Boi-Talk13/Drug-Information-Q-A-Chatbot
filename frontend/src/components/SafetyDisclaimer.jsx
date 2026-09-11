import React from 'react';
import { ShieldCheck, Info } from 'lucide-react';

export default function SafetyDisclaimer() {
  return (
    <footer style={{
      textAlign: 'center',
      padding: '8px 16px',
      fontSize: '0.76rem',
      color: 'var(--text-secondary)',
      backgroundColor: 'var(--bg-canvas)',
      borderTop: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '4px'
    }}>
      {/* Simple, plain-language description of what the app does */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-primary)', fontWeight: 600 }}>
        <ShieldCheck size={13} style={{ color: 'var(--accent-sage)', flexShrink: 0 }} />
        <span>
          MedCite reads a medicine's official PDF, answers your question using only that document,
          and shows the exact page for every fact — if the PDF doesn't say it, it won't guess.
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Info size={13} style={{ color: 'var(--accent-sage)', flexShrink: 0 }} />
        <span>
          Not medical advice. For medical decisions, consult a qualified healthcare professional.
        </span>
      </div>
    </footer>
  );
}
