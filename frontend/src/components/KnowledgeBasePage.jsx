import React from 'react';
import { ArrowLeft, FileText, BookOpen, ExternalLink, CheckCircle2, ShieldCheck, Pill } from 'lucide-react';
import { getAvailableDrugs } from '../services/apiService';

export default function KnowledgeBasePage({ onBackToLanding, onOpenChatWithDrug }) {
  const drugs = getAvailableDrugs();

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: 'var(--bg-canvas)',
      color: 'var(--text-primary)',
      fontFamily: 'var(--font-sans)',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Header Bar */}
      <header style={{
        padding: '16px 40px',
        backgroundColor: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        boxShadow: 'var(--shadow-sm)'
      }}>
        {/* Back Button to Landing Page */}
        <button
          type="button"
          onClick={onBackToLanding}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: 'var(--bg-surface-subtle)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '8px 16px',
            fontSize: '0.88rem',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <ArrowLeft size={16} />
          <span>Back to Landing Page</span>
        </button>

        {/* Brand Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            position: 'relative',
            width: '36px',
            height: '36px',
            borderRadius: '10px',
            backgroundColor: 'var(--accent-sage-light)',
            border: '1px solid var(--accent-sage-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--accent-sage)'
          }}>
            <Pill size={18} style={{ transform: 'rotate(-45deg)' }} />
          </div>
          <div>
            <h1 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
              Knowledge Base Index
            </h1>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: 0 }}>
              Verified Prescribing Documents
            </p>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main style={{
        maxWidth: '1000px',
        margin: '0 auto',
        padding: '50px 20px',
        width: '100%',
        flex: 1
      }}>
        {/* Page Banner */}
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: 'var(--accent-sage-light)',
            color: 'var(--accent-sage-dark)',
            padding: '4px 14px',
            borderRadius: '999px',
            fontSize: '0.8rem',
            fontWeight: 600,
            marginBottom: '14px',
            border: '1px solid var(--accent-sage-border)'
          }}>
            <BookOpen size={14} />
            Official Medical Prescribing Documents Index
          </div>

          <h2 style={{ fontSize: '2.2rem', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: '10px' }}>
            Explore Verified Drug Knowledge Base
          </h2>

          <p style={{ fontSize: '1rem', color: 'var(--text-secondary)', maxWidth: '650px', margin: '0 auto', lineHeight: 1.5 }}>
            MedCite answers questions exclusively from these official prescribing PDFs. Every document is pre-indexed by section with exact page numbers.
          </p>
        </div>

        {/* Documents Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(440px, 1fr))', gap: '20px' }}>
          {drugs.map((drug) => (
            <div
              key={drug.id}
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-lg)',
                padding: '24px',
                boxShadow: 'var(--shadow-sm)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '16px'
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{
                      width: '40px',
                      height: '40px',
                      borderRadius: '10px',
                      backgroundColor: 'var(--accent-sage-light)',
                      color: 'var(--accent-sage)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      border: '1px solid var(--accent-sage-border)'
                    }}>
                      <FileText size={20} />
                    </div>
                    <div>
                      <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                        {drug.name}
                      </h3>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                        {drug.manufacturer || 'Pharmaceutical Prescribing Information'}
                      </div>
                    </div>
                  </div>

                  <span style={{
                    fontSize: '0.72rem',
                    fontWeight: 600,
                    backgroundColor: 'var(--accent-sage-light)',
                    color: 'var(--accent-sage-dark)',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    border: '1px solid var(--accent-sage-border)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}>
                    <CheckCircle2 size={12} />
                    {drug.status || 'Indexed & Verified'}
                  </span>
                </div>

                <div style={{
                  backgroundColor: 'var(--bg-surface-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: '12px 14px',
                  fontSize: '0.82rem',
                  color: 'var(--text-secondary)',
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '8px'
                }}>
                  <div>Document File: <code style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{drug.pdf}</code></div>
                  <div>Total Index Pages: <strong style={{ color: 'var(--text-primary)' }}>{drug.pages} pages</strong></div>
                  <div>Search Types: <strong>BM25 + Vector</strong></div>
                  <div>Citation Format: <strong>Page-Level [p. X]</strong></div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '14px' }}>
                <a
                  href={drug.source_url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    fontSize: '0.8rem',
                    color: 'var(--accent-blue)',
                    textDecoration: 'none',
                    fontWeight: 600,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <span>View Source Link</span>
                  <ExternalLink size={12} />
                </a>

                <button
                  type="button"
                  onClick={() => onOpenChatWithDrug(drug.id)}
                  style={{
                    backgroundColor: 'var(--accent-sage)',
                    color: 'var(--text-inverse)',
                    border: 'none',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 14px',
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    boxShadow: 'var(--shadow-sm)'
                  }}
                >
                  <span>Ask in Chatbot →</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer style={{
        padding: '20px 40px',
        backgroundColor: 'var(--bg-surface)',
        borderTop: '1px solid var(--border-color)',
        textAlign: 'center',
        fontSize: '0.8rem',
        color: 'var(--text-secondary)'
      }}>
        MedCite Verified Prescribing Knowledge Base • Every answer cites official document page numbers.
      </footer>
    </div>
  );
}
