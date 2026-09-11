/**
 * AssistantMessage — renders one bot answer.
 * It scans the answer text for page markers like "[p. 8]" and turns each into a
 * clickable Citation tag; clicking one opens the PDF at that page and highlights
 * the sentence. Also shows the section, the medical-advice banner, and the list
 * of verified source pages.
 */
import React, { useState } from 'react';
import { ShieldCheck, AlertTriangle, BookOpen, Copy, Check, ExternalLink, Sparkles } from 'lucide-react';
import Citation from './Citation';

export default function AssistantMessage({ message, onCitationClick }) {
  const [copied, setCopied] = useState(false);
  const { text, citations = [], section, is_advice, drug_name } = message;

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  /**
   * Helper to parse citation strings like "[p. 12]" or "[p. 8]" and replace with interactive Citation tags
   */
  // The clause of the answer that ends in this page's citation marker. This is
  // the sentence the user is verifying, so the PDF viewer highlights it on the
  // page (it usually contains the verbatim label phrase).
  const answerSentenceForPage = (pageNum) => {
    if (!text) return '';
    const re = new RegExp(`\\[p\\.\\s*(?:\\d+\\s*,\\s*)*${pageNum}(?:\\s*,\\s*\\d+)*\\s*\\]`);
    const m = text.match(re);
    if (!m) return '';
    const before = text.slice(0, m.index);
    const start = Math.max(before.lastIndexOf('. '), before.lastIndexOf('• '), before.lastIndexOf('\n'));
    return text.slice(start + 1, m.index).trim();
  };

  const renderFormattedText = (content) => {
    if (!content) return null;

    // Pattern to match citations like [p. 12] or [p. 1, 2]
    const citationRegex = /\[p\.\s*(\d+)(?:,\s*(\d+))?\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = citationRegex.exec(content)) !== null) {
      // Text before citation
      if (match.index > lastIndex) {
        parts.push(content.substring(lastIndex, match.index));
      }

      const page1 = parseInt(match[1], 10);
      const page2 = match[2] ? parseInt(match[2], 10) : null;

      // Find matching citation object if available
      const citObj1 = citations.find(c => c.page === page1) || { page: page1, section, source: drug_name || 'Prescribing Information' };
      
      parts.push(
        <Citation
          key={`cit-${match.index}`}
          page={page1}
          source={citObj1.source || drug_name || 'Prescribing Information'}
          section={citObj1.section || section}
          text={citObj1.text}
          answerText={answerSentenceForPage(page1)}
          onClick={onCitationClick}
        />
      );

      if (page2) {
        const citObj2 = citations.find(c => c.page === page2) || { page: page2, section, source: drug_name || 'Prescribing Information' };
        parts.push(
          <Citation
            key={`cit2-${match.index}`}
            page={page2}
            source={citObj2.source || drug_name || 'Prescribing Information'}
            section={citObj2.section || section}
            text={citObj2.text}
            answerText={answerSentenceForPage(page2)}
            onClick={onCitationClick}
          />
        );
      }

      lastIndex = citationRegex.lastIndex;
    }

    if (lastIndex < content.length) {
      parts.push(content.substring(lastIndex));
    }

    return parts;
  };

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
        {/* Assistant Avatar */}
        <div style={{
          width: '34px',
          height: '34px',
          borderRadius: '10px',
          backgroundColor: 'var(--accent-sage-light)',
          color: 'var(--accent-sage)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid var(--accent-sage-border)',
          flexShrink: 0,
          boxShadow: 'var(--shadow-sm)'
        }}>
          <ShieldCheck size={18} />
        </div>

        {/* Answer Content Card */}
        <div style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-color)',
          borderRadius: '4px 16px 16px 16px',
          padding: '18px 22px',
          boxShadow: 'var(--shadow-md)',
          width: '100%'
        }}>
          {/* Top Metadata Header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '10px',
            borderBottom: '1px solid var(--border-subtle)',
            paddingBottom: '8px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{
                fontSize: '0.8rem',
                fontWeight: 700,
                color: 'var(--accent-sage-dark)',
                letterSpacing: '-0.01em'
              }}>
                MedCite Response
              </span>
              {section && (
                <span style={{
                  fontSize: '0.72rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-secondary)',
                  backgroundColor: 'var(--bg-surface-subtle)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  border: '1px solid var(--border-subtle)'
                }}>
                  {section}
                </span>
              )}
            </div>

            <button
              onClick={handleCopy}
              title="Copy answer text"
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '0.75rem',
                padding: '2px 6px',
                borderRadius: '4px',
                transition: 'all 0.15s ease'
              }}
            >
              {copied ? <Check size={13} style={{ color: 'var(--accent-sage)' }} /> : <Copy size={13} />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>

          {/* Medical Advice Warning Banner if applicable */}
          {is_advice && (
            <div style={{
              backgroundColor: 'var(--accent-amber-light)',
              border: '1px solid var(--accent-amber-border)',
              borderRadius: 'var(--radius-md)',
              padding: '12px 14px',
              marginBottom: '14px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '10px',
              color: 'var(--accent-amber)'
            }}>
              <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div style={{ fontSize: '0.84rem', lineHeight: 1.4 }}>
                <strong style={{ display: 'block', marginBottom: '2px', fontWeight: 600 }}>
                  Medical Advice Notice:
                </strong>
                Please consult a doctor or qualified healthcare professional before making any medical decisions. The prescribing document provides the facts below:
              </div>
            </div>
          )}

          {/* Answer Text */}
          <div style={{
            fontSize: '0.96rem',
            color: 'var(--text-primary)',
            lineHeight: 1.65,
            fontFamily: 'var(--font-sans)',
            whiteSpace: 'pre-wrap'
          }}>
            {renderFormattedText(text)}
          </div>

          {/* Citations Footer summary list */}
          {citations && citations.length > 0 && (
            <div style={{
              marginTop: '16px',
              paddingTop: '12px',
              borderTop: '1px dashed var(--border-color)',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}>
              <div style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                color: 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                gap: '5px'
              }}>
                <BookOpen size={12} />
                <span>VERIFIED DOCUMENT SOURCES:</span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {citations.map((c, i) => (
                  <div
                    key={i}
                    onClick={() => onCitationClick && onCitationClick({ ...c, answerText: answerSentenceForPage(c.page) })}
                    style={{
                      fontSize: '0.78rem',
                      backgroundColor: 'var(--bg-surface-subtle)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '4px 10px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      color: 'var(--text-secondary)',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <span style={{ fontWeight: 600, color: 'var(--accent-sage-dark)' }}>Page {c.page}</span>
                    {c.section && <span style={{ opacity: 0.85 }}>• {c.section}</span>}
                    <ExternalLink size={11} style={{ opacity: 0.6 }} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
