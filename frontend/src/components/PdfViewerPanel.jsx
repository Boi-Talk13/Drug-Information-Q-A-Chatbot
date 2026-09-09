import React, { useState, useEffect } from 'react';
import { X, FileText, ChevronLeft, ChevronRight, Download, BookOpen, ExternalLink, Hash } from 'lucide-react';
import { getAvailableDrugs } from '../services/apiService';

export default function PdfViewerPanel({ activeCitation, selectedDrug, onClose }) {
  const drugs = getAvailableDrugs();
  const currentDrug = drugs.find(d => d.id === selectedDrug) || drugs[0];

  const totalPages = currentDrug ? currentDrug.pages : 92;

  // Track active page in viewer
  const [currentPage, setCurrentPage] = useState(activeCitation?.page || 12);
  const [pageInputValue, setPageInputValue] = useState(String(currentPage));

  // Sync page number whenever activeCitation changes
  useEffect(() => {
    if (activeCitation?.page) {
      setCurrentPage(activeCitation.page);
      setPageInputValue(String(activeCitation.page));
    }
  }, [activeCitation]);

  const handlePrevPage = () => {
    if (currentPage > 1) {
      const p = currentPage - 1;
      setCurrentPage(p);
      setPageInputValue(String(p));
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      const p = currentPage + 1;
      setCurrentPage(p);
      setPageInputValue(String(p));
    }
  };

  const handlePageInputChange = (e) => {
    setPageInputValue(e.target.value);
  };

  const handlePageInputSubmit = (e) => {
    e.preventDefault();
    const p = parseInt(pageInputValue, 10);
    if (!isNaN(p) && p >= 1 && p <= totalPages) {
      setCurrentPage(p);
    } else {
      setPageInputValue(String(currentPage));
    }
  };

  const sectionTitle = activeCitation ? (activeCitation.section || 'PRESCRIBING INFORMATION SECTION') : '2 DOSAGE AND ADMINISTRATION';
  const textExcerpt = activeCitation ? activeCitation.text : `The recommended dosage of ${currentDrug.name} is determined based on prescribed indication.`;

  return (
    <aside style={{
      width: '440px',
      height: '100%',
      backgroundColor: 'var(--bg-sidebar)',
      borderLeft: '1px solid var(--border-color)',
      display: 'flex',
      flexDirection: 'column',
      boxShadow: 'var(--shadow-lg)',
      zIndex: 50,
      transition: 'all 0.3s ease'
    }}>
      {/* Viewer Header */}
      <div style={{
        padding: '14px 18px',
        backgroundColor: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '6px',
            backgroundColor: 'var(--accent-sage-light)',
            color: 'var(--accent-sage-dark)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <FileText size={18} />
          </div>
          <div>
            <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.2 }}>
              {currentDrug ? currentDrug.name : 'Prescribing PDF'}
            </div>
            <div style={{ fontSize: '0.73rem', color: 'var(--text-secondary)' }}>
              Official PDF: <code style={{ fontFamily: 'var(--font-mono)' }}>{currentDrug?.pdf || 'prescribing_info.pdf'}</code>
            </div>
          </div>
        </div>

        <button
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
          title="Close PDF Panel"
        >
          <X size={18} />
        </button>
      </div>

      {/* Interactive Page Navigation Bar */}
      <div style={{
        padding: '8px 16px',
        backgroundColor: 'var(--bg-surface-subtle)',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '0.8rem',
        color: 'var(--text-secondary)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            type="button"
            onClick={handlePrevPage}
            disabled={currentPage <= 1}
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              borderRadius: '4px',
              padding: '2px 6px',
              cursor: currentPage <= 1 ? 'not-allowed' : 'pointer',
              opacity: currentPage <= 1 ? 0.4 : 1
            }}
            title="Previous Page"
          >
            <ChevronLeft size={14} />
          </button>

          <form onSubmit={handlePageInputSubmit} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ fontWeight: 600 }}>Page</span>
            <input
              type="text"
              value={pageInputValue}
              onChange={handlePageInputChange}
              onBlur={handlePageInputSubmit}
              style={{
                width: '38px',
                textAlign: 'center',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                padding: '1px 2px',
                fontSize: '0.8rem',
                fontFamily: 'var(--font-mono)',
                fontWeight: 600,
                color: 'var(--text-primary)'
              }}
            />
            <span style={{ opacity: 0.6 }}>/ {totalPages}</span>
          </form>

          <button
            type="button"
            onClick={handleNextPage}
            disabled={currentPage >= totalPages}
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              borderRadius: '4px',
              padding: '2px 6px',
              cursor: currentPage >= totalPages ? 'not-allowed' : 'pointer',
              opacity: currentPage >= totalPages ? 0.4 : 1
            }}
            title="Next Page"
          >
            <ChevronRight size={14} />
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {activeCitation && activeCitation.page === currentPage && (
            <span style={{
              backgroundColor: 'var(--accent-sage-light)',
              color: 'var(--accent-sage-dark)',
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '0.72rem',
              fontWeight: 600,
              fontFamily: 'var(--font-mono)'
            }}>
              Citation Highlighted
            </span>
          )}
        </div>
      </div>

      {/* Main Document Reader Content Area */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px'
      }}>
        {/* Document Header Page View Simulation */}
        <div style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          padding: '20px',
          boxShadow: 'var(--shadow-sm)',
          fontFamily: 'var(--font-serif)'
        }}>
          <div style={{
            fontSize: '0.72rem',
            fontFamily: 'var(--font-sans)',
            textTransform: 'uppercase',
            color: 'var(--text-muted)',
            letterSpacing: '0.05em',
            marginBottom: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <span>DOCUMENT SECTION • PAGE {currentPage}</span>
            <span style={{ fontFamily: 'var(--font-mono)' }}>{currentDrug?.pdf}</span>
          </div>

          <h3 style={{
            fontSize: '1.05rem',
            fontWeight: 700,
            color: 'var(--accent-sage-dark)',
            marginBottom: '12px',
            borderBottom: '2px solid var(--accent-sage-border)',
            paddingBottom: '6px',
            fontFamily: 'var(--font-sans)'
          }}>
            {sectionTitle}
          </h3>

          {/* Citation Text Excerpt Highlight Box */}
          <div style={{
            backgroundColor: '#FFFDF5',
            border: '1.5px solid #E6D8A8',
            borderRadius: 'var(--radius-sm)',
            padding: '14px 16px',
            marginBottom: '16px',
            position: 'relative'
          }}>
            <div style={{
              fontSize: '0.68rem',
              fontWeight: 700,
              color: '#8A6818',
              fontFamily: 'var(--font-sans)',
              textTransform: 'uppercase',
              marginBottom: '4px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}>
              <BookOpen size={11} />
              Extracted Line from Page {currentPage}:
            </div>
            <p style={{
              fontSize: '0.92rem',
              color: '#2C2618',
              lineHeight: 1.6,
              fontStyle: 'italic',
              margin: 0
            }}>
              "{textExcerpt}"
            </p>
          </div>

          {/* Surrounding Context Contextual Text */}
          <div style={{
            fontSize: '0.85rem',
            color: 'var(--text-secondary)',
            lineHeight: 1.6
          }}>
            <p style={{ marginBottom: '10px' }}>
              <strong>Prescribing Directions:</strong> Administer {currentDrug.name} as directed by healthcare provider guidelines. Store at room temperature 20°C to 25°C (68°F to 77°F).
            </p>
            <p>
              <strong>Special Populations & Precautions:</strong> Refer to full prescribing information for complete dosage adjustments in patients with hepatic or renal impairment.
            </p>
          </div>
        </div>

        {/* Verification Index Metadata Card */}
        <div style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          padding: '14px 16px',
          fontSize: '0.78rem',
          color: 'var(--text-secondary)'
        }}>
          <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
            PyMuPDF Index Metadata
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
            <div>Document: <span style={{ fontFamily: 'var(--font-mono)' }}>{currentDrug?.pdf}</span></div>
            <div>Page Index: <span style={{ fontFamily: 'var(--font-mono)' }}>{currentPage}</span></div>
            <div>Chunk ID: <span style={{ fontFamily: 'var(--font-mono)' }}>chk_p{currentPage}_sec</span></div>
            <div>Search Strategy: <span style={{ color: 'var(--accent-sage)', fontWeight: 600 }}>BM25 + Vector</span></div>
          </div>
        </div>
      </div>
    </aside>
  );
}
