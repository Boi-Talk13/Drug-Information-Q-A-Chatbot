/**
 * SuggestedQuestion — the welcome screen shown before any messages.
 * If the user's library is empty it prompts them to upload a PDF; otherwise it
 * shows example questions (indications, dose, side effects, warnings) plus two
 * Responsible-AI test prompts (an advice question and an unanswerable one).
 */
import React, { useRef, useState } from 'react';
import { BookOpen, ShieldAlert, HelpCircle, ArrowRight, Sparkles, UploadCloud, Loader2 } from 'lucide-react';
import { uploadMedicinePdfs, getAvailableDrugs } from '../services/apiService';

export default function SuggestedQuestion({ onSelectQuestion, selectedDrugName, hasDrugs = true, onUploaded }) {
  const drug = selectedDrugName || 'this medicine';
  const fileRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  const handleFiles = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    setUploadError(null);
    setUploading(true);
    try {
      const added = await uploadMedicinePdfs(files, true);
      getAvailableDrugs();
      if (onUploaded) onUploaded(added[0]?.id);
    } catch (err) {
      setUploadError(err.message || 'Upload failed.');
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };
  const suggestions = [
    {
      type: 'indication',
      question: `What are the approved indications for ${drug}?`,
      category: 'Indications & Uses',
      icon: BookOpen
    },
    {
      type: 'dose',
      question: `What is the recommended starting dose of ${drug}?`,
      category: 'Dosage & Admin',
      icon: BookOpen
    },
    {
      type: 'side_effects',
      question: `What are the common side effects listed in the label?`,
      category: 'Side Effects',
      icon: BookOpen
    },
    {
      type: 'warnings',
      question: `What boxed warnings are listed for ${drug}?`,
      category: 'Boxed Warnings',
      icon: BookOpen
    },
    {
      type: 'advice_test',
      question: `Should I stop taking ${drug} if my symptoms improve?`,
      category: 'Safety Advice Test',
      icon: ShieldAlert,
      tag: 'Responsible AI Test'
    },
    {
      type: 'refusal_test',
      question: `What is the approved dose for newborn babies under 1 month?`,
      category: 'Refusal Test',
      icon: HelpCircle,
      tag: 'Refusal Safeguard Test'
    }
  ];

  return (
    <div className="animate-fade-in" style={{
      maxWidth: '760px',
      margin: '40px auto',
      padding: '0 20px',
      textAlign: 'center'
    }}>
      {/* Welcome Title */}
      <div style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        backgroundColor: 'var(--accent-sage-light)',
        color: 'var(--accent-sage-dark)',
        padding: '4px 12px',
        borderRadius: '999px',
        fontSize: '0.78rem',
        fontWeight: 600,
        marginBottom: '16px',
        border: '1px solid var(--accent-sage-border)'
      }}>
        <Sparkles size={13} />
        Prescribing Information Q&A Engine
      </div>

      <h2 style={{
        fontSize: '2rem',
        fontWeight: 700,
        color: 'var(--text-primary)',
        letterSpacing: '-0.02em',
        marginBottom: '10px',
        fontFamily: 'var(--font-sans)'
      }}>
        Ask about a medicine
      </h2>

      <p style={{
        fontSize: '1rem',
        color: 'var(--text-secondary)',
        maxWdith: '580px',
        margin: '0 auto 32px auto',
        lineHeight: 1.5
      }}>
        Get information directly from official medicine prescribing documents, with the exact source page shown for every fact.
      </p>

      {/* Empty state: a clickable dropzone to upload the first PDF */}
      {!hasDrugs ? (
        <div
          onClick={() => !uploading && fileRef.current && fileRef.current.click()}
          style={{
            border: '2px dashed var(--accent-sage-border)',
            backgroundColor: 'var(--bg-surface)',
            borderRadius: 'var(--radius-md)',
            padding: '36px 24px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '12px',
            cursor: uploading ? 'wait' : 'pointer',
            transition: 'all 0.15s ease'
          }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--accent-sage)'; e.currentTarget.style.backgroundColor = 'var(--accent-sage-light)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--accent-sage-border)'; e.currentTarget.style.backgroundColor = 'var(--bg-surface)'; }}
        >
          <input ref={fileRef} type="file" accept=".pdf" multiple onChange={handleFiles} style={{ display: 'none' }} />
          <UploadCloud size={38} style={{ color: 'var(--accent-sage)' }} />
          <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            {uploading ? 'Uploading & indexing…' : 'Upload a medicine PDF to get started'}
          </div>
          <div style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', maxWidth: '460px', lineHeight: 1.5 }}>
            Your library is empty. <strong>Click here</strong> (or the Upload PDF button top-right)
            to add one or more medicine PDFs. Then ask questions and every answer cites the exact page.
          </div>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); if (!uploading && fileRef.current) fileRef.current.click(); }}
            disabled={uploading}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '8px',
              backgroundColor: 'var(--accent-sage)', color: 'var(--text-inverse, #fff)',
              border: 'none', borderRadius: 'var(--radius-md)', padding: '10px 20px',
              fontSize: '0.95rem', fontWeight: 700, cursor: uploading ? 'wait' : 'pointer',
              marginTop: '4px'
            }}
          >
            {uploading ? <Loader2 size={16} className="pulse-badge" /> : <UploadCloud size={16} />}
            <span>{uploading ? 'Please wait…' : 'Choose PDF file(s)'}</span>
          </button>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>PDF only · max 100 MB per file</div>
          {uploadError && <div style={{ color: 'var(--accent-red, #B4453C)', fontSize: '0.85rem' }}>{uploadError}</div>}
        </div>
      ) : (
      /* Suggestion Grid */
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: '12px',
        textAlign: 'left'
      }}>
        {suggestions.map((item, idx) => {
          const ItemIcon = item.icon;
          return (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectQuestion(item.question)}
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                padding: '14px 16px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '8px',
                boxShadow: 'var(--shadow-sm)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent-sage)';
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = 'var(--shadow-md)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-color)';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{
                  fontSize: '0.72rem',
                  fontWeight: 600,
                  color: 'var(--accent-sage-dark)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em'
                }}>
                  {item.category}
                </span>
                {item.tag && (
                  <span style={{
                    fontSize: '0.68rem',
                    backgroundColor: 'var(--accent-amber-light)',
                    color: 'var(--accent-amber)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontWeight: 600
                  }}>
                    {item.tag}
                  </span>
                )}
              </div>

              <div style={{
                fontSize: '0.92rem',
                fontWeight: 500,
                color: 'var(--text-primary)',
                lineHeight: 1.4,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '8px'
              }}>
                <span>"{item.question}"</span>
                <ArrowRight size={15} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
              </div>
            </button>
          );
        })}
      </div>
      )}
    </div>
  );
}
