/**
 * Citation — the small clickable "[p. N]" tag shown inside an answer.
 * On click it tells the PDF viewer which page (and which answer sentence) to
 * open and highlight. Hovering shows the source, section and a text preview.
 */
import React from 'react';
import { BookOpen } from 'lucide-react';

/**
 * Citation Component
 * Renders an elegant inline citation tag [p. 12] with hover tooltips and click handler.
 */
export default function Citation({ page, source = 'Prescribing Information', section, text, answerText, onClick }) {
  const handleClick = (e) => {
    e.preventDefault();
    if (onClick) {
      onClick({ page, source, section, text, answerText });
    }
  };

  const tooltipText = `Source: ${source} — Page ${page}${section ? ` (${section})` : ''}`;

  return (
    <span className="tooltip-wrapper">
      <button
        type="button"
        className="citation-tag"
        onClick={handleClick}
        aria-label={`Jump to page ${page} in ${source}`}
        title={tooltipText}
      >
        <BookOpen size={11} style={{ opacity: 0.8 }} />
        <span>p. {page}</span>
      </button>
      <span className="tooltip-content" role="tooltip">
        <strong style={{ display: 'block', marginBottom: '2px', color: '#B6D0C2' }}>
          {source}
        </strong>
        {section && <div style={{ fontSize: '0.72rem', color: '#9DB3A7', marginBottom: '4px' }}>{section}</div>}
        <span>Page {page}</span>
        {text && (
          <p style={{ marginTop: '4px', fontStyle: 'italic', color: '#D4DDD8', fontSize: '0.73rem', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '4px' }}>
            "{text.length > 90 ? text.substring(0, 90) + '...' : text}"
          </p>
        )}
      </span>
    </span>
  );
}
