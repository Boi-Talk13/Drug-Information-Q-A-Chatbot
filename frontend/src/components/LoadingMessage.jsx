import React, { useState, useEffect } from 'react';
import { Search, BookOpen, ShieldCheck } from 'lucide-react';

export default function LoadingMessage() {
  const [step, setStep] = useState(0);

  const steps = [
    { label: 'Searching medicine documents index...', icon: Search },
    { label: 'Matching relevant sections & page numbers...', icon: BookOpen },
    { label: 'Preparing answer with page-level citations...', icon: ShieldCheck }
  ];

  useEffect(() => {
    const timer1 = setTimeout(() => setStep(1), 600);
    const timer2 = setTimeout(() => setStep(2), 1200);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, []);

  const CurrentIcon = steps[step].icon;

  return (
    <div className="animate-fade-in" style={{
      display: 'flex',
      justifyContent: 'flex-start',
      marginBottom: '20px'
    }}>
      <div style={{
        display: 'flex',
        gap: '12px',
        alignItems: 'center',
        backgroundColor: 'var(--bg-surface)',
        border: '1px solid var(--border-color)',
        borderRadius: 'var(--radius-lg)',
        padding: '10px 18px',
        boxShadow: 'var(--shadow-sm)'
      }}>
        <div style={{
          color: 'var(--accent-sage)',
          display: 'flex',
          alignItems: 'center',
          animation: 'pulseDot 1.5s infinite ease-in-out'
        }}>
          <CurrentIcon size={18} />
        </div>

        <span style={{
          fontSize: '0.88rem',
          color: 'var(--text-secondary)',
          fontWeight: 500
        }}>
          {steps[step].label}
        </span>
      </div>
    </div>
  );
}
