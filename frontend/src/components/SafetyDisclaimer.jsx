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
      alignItems: 'center',
      justifyContent: 'center',
      gap: '6px'
    }}>
      <Info size={13} style={{ color: 'var(--accent-sage)', flexShrink: 0 }} />
      <span>
        <strong>MedCite</strong> provides factual information extracted from public medicine labels and is not medical advice. For medical decisions, consult a qualified healthcare professional.
      </span>
    </footer>
  );
}
