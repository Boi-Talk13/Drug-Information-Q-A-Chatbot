import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import { X, FileText, ChevronLeft, ChevronRight, Loader2, AlertCircle, ZoomIn, ZoomOut } from 'lucide-react';
import { getAvailableDrugs, getPdfUrl } from '../services/apiService';

// Point pdf.js at its worker (bundled by Vite).
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

// Normalise text for matching (lowercase, strip citation markers & punctuation).
function normalise(s) {
  return (s || '')
    .toLowerCase()
    // Drop bracketed cross-references and citation markers: [p. 8], [see ...].
    .replace(/\[[^\]]*\]/g, ' ')
    // Drop section-number parentheticals like (2.4, 2.10) or (5.1).
    .replace(/\([^)]*\d[^)]*\)/g, ' ')
    .replace(/[^a-z0-9 ]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Longest common substring between the citation `a` and the page text `b`.
// Returns the match's start position IN `b` and its length. Character-level DP
// with a rolling row so memory stays small.
function longestCommonRun(a, b) {
  if (!a || !b) return { pos: -1, length: 0 };
  const n = a.length, m = b.length;
  let best = 0, bestEndB = 0;
  let prev = new Uint16Array(m + 1);
  for (let i = 1; i <= n; i++) {
    const cur = new Uint16Array(m + 1);
    const ai = a.charCodeAt(i - 1);
    for (let j = 1; j <= m; j++) {
      if (ai === b.charCodeAt(j - 1)) {
        const v = prev[j - 1] + 1;
        cur[j] = v;
        if (v > best) { best = v; bestEndB = j; }
      }
    }
    prev = cur;
  }
  return { pos: bestEndB - best, length: best };
}

export default function PdfViewerPanel({ activeCitation, selectedDrug, onClose }) {
  const drugs = getAvailableDrugs();
  const currentDrug = drugs.find(d => d.id === selectedDrug) || drugs[0] || { id: selectedDrug, name: selectedDrug || 'PDF', pdf: '', pages: 0 };
  const pdfUrl = getPdfUrl(selectedDrug);

  const [numPages, setNumPages] = useState(null);
  const [currentPage, setCurrentPage] = useState(activeCitation?.page || 1);
  const [pageInput, setPageInput] = useState(String(activeCitation?.page || 1));
  const [loadError, setLoadError] = useState(false);
  const [width, setWidth] = useState(400);
  const [zoom, setZoom] = useState(1.35);   // pages start a bit larger for readability
  const pageWidth = Math.round(width * zoom);
  const [panelWidth, setPanelWidth] = useState(480);  // draggable panel width

  // Drag the left edge to resize the whole PDF panel.
  const startResize = (e) => {
    e.preventDefault();
    const startX = e.clientX;
    const startW = panelWidth;
    const onMove = (ev) => {
      const dx = startX - ev.clientX; // drag left → wider
      const max = Math.min(1100, window.innerWidth - 340);
      setPanelWidth(Math.min(Math.max(360, startW + dx), max));
    };
    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      document.body.style.userSelect = '';
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    document.body.style.userSelect = 'none';
  };

  const scrollRef = useRef(null);
  const pageRefs = useRef({});
  const pdfDocRef = useRef(null);
  // { page, set:Set<itemIndex> } computed for the cited page only.
  const [highlight, setHighlight] = useState({ page: null, set: new Set() });

  // react-pdf reloads if the options object identity changes — memoise it.
  const fileProp = useMemo(() => (pdfUrl ? { url: pdfUrl } : null), [pdfUrl]);
  const options = useMemo(() => ({ cMapUrl: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.8.69/cmaps/', cMapPacked: true }), []);

  // Measure the panel width so pages fit nicely.
  useEffect(() => {
    if (!scrollRef.current) return;
    const el = scrollRef.current;
    const measure = () => setWidth(Math.max(240, el.clientWidth - 32));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [numPages]);

  const scrollToPage = useCallback((pageNum) => {
    const node = pageRefs.current[pageNum];
    if (node && scrollRef.current) {
      node.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, []);

  // When a citation is clicked, jump to its page (once the PDF is loaded).
  useEffect(() => {
    if (activeCitation?.page) {
      setCurrentPage(activeCitation.page);
      setPageInput(String(activeCitation.page));
      if (numPages) {
        // small delay so the target page is mounted
        setTimeout(() => scrollToPage(activeCitation.page), 120);
      }
    }
  }, [activeCitation, numPages, scrollToPage]);

  // Reset when the document changes.
  useEffect(() => {
    setNumPages(null);
    setLoadError(false);
    pageRefs.current = {};
  }, [pdfUrl]);

  // Track which page is in view while scrolling, so the lazy-render window
  // follows the reader. Only a few pages are ever mounted at once → fast.
  useEffect(() => {
    if (!numPages || !scrollRef.current) return;
    const root = scrollRef.current;
    const io = new IntersectionObserver((entries) => {
      let topP = null, topTop = Infinity;
      for (const e of entries) {
        if (e.isIntersecting) {
          const p = parseInt(e.target.dataset.page, 10);
          const top = e.boundingClientRect.top;
          if (top < topTop) { topTop = top; topP = p; }
        }
      }
      if (topP) setCurrentPage((cur) => (cur === topP ? cur : topP));
    }, { root, threshold: 0.05 });
    Object.values(pageRefs.current).forEach((el) => el && io.observe(el));
    return () => io.disconnect();
  }, [numPages, width]);

  // Keep the page-number box in sync with the page in view.
  useEffect(() => { setPageInput(String(currentPage)); }, [currentPage]);

  const onDocLoad = (pdf) => {
    pdfDocRef.current = pdf;
    setNumPages(pdf.numPages);
    if (activeCitation?.page) setTimeout(() => scrollToPage(activeCitation.page), 200);
  };

  // Compute the exact contiguous run of text items on the cited page that
  // matches the answer's source text, so we highlight only that sentence.
  useEffect(() => {
    let cancelled = false;
    async function compute() {
      const pdf = pdfDocRef.current;
      if (!pdf || !activeCitation?.page || !activeCitation?.text) {
        setHighlight({ page: null, set: new Set() });
        return;
      }
      try {
        const page = await pdf.getPage(activeCitation.page);
        const tc = await page.getTextContent();
        // Build a normalised concatenation of the page, remembering the char
        // span each text item occupies.
        let concat = '';
        const spans = [];
        tc.items.forEach((it, idx) => {
          const nrm = normalise(it.str);
          const start = concat.length;
          concat += nrm + ' ';
          spans.push({ idx, start, end: concat.length });
        });
        // Prefer the answer sentence for this page (it holds the verbatim label
        // phrase the user is checking); fall back to the chunk snippet.
        const answerNorm = normalise(activeCitation.answerText);
        const textNorm = normalise(activeCitation.text);
        let best = { pos: -1, length: 0 };
        if (answerNorm) best = longestCommonRun(answerNorm, concat);
        // If the answer sentence didn't give a solid, specific match, fall back
        // to the chunk snippet (which is verbatim page text).
        if (best.length < 22 && textNorm) {
          const alt = longestCommonRun(textNorm, concat);
          if (alt.length > best.length) best = alt;
        }
        const { pos, length } = best;
        const set = new Set();
        if (pos >= 0 && length >= 18) {
          const endPos = pos + length;
          spans.forEach(s => {
            if (s.start < endPos && s.end > pos) set.add(s.idx);
          });
        }
        if (!cancelled) setHighlight({ page: activeCitation.page, set });
      } catch {
        if (!cancelled) setHighlight({ page: null, set: new Set() });
      }
    }
    compute();
    return () => { cancelled = true; };
  }, [activeCitation, numPages]);

  const goto = (p) => {
    if (!numPages) return;
    const n = Math.min(Math.max(1, p), numPages);
    setCurrentPage(n);
    setPageInput(String(n));
    scrollToPage(n);
  };

  // Highlight only the exact matched item indices on the cited page.
  const makeTextRenderer = useCallback((pageNumber) => {
    if (!highlight.set || highlight.page !== pageNumber || highlight.set.size === 0) {
      return undefined;
    }
    return ({ str, itemIndex }) => {
      const s = str || '';
      return highlight.set.has(itemIndex)
        ? `<mark class="medcite-hl">${escapeHtml(s)}</mark>`
        : escapeHtml(s);
    };
  }, [highlight]);

  return (
    <aside style={{
      width: `${panelWidth}px`,
      flexShrink: 0,
      height: '100%',
      position: 'relative',
      backgroundColor: 'var(--bg-sidebar)',
      borderLeft: '1px solid var(--border-color)',
      display: 'flex',
      flexDirection: 'column',
      boxShadow: 'var(--shadow-lg)',
      zIndex: 50
    }}>
      {/* Drag handle to resize the panel */}
      <div
        onMouseDown={startResize}
        title="Drag to resize"
        style={{
          position: 'absolute', left: -4, top: 0, bottom: 0, width: 10,
          cursor: 'col-resize', zIndex: 60,
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}
      >
        <div style={{ width: 4, height: 42, borderRadius: 3, backgroundColor: 'var(--accent-sage)', opacity: 0.55 }} />
      </div>
      <style>{`
        /* Semi-transparent so the canvas text underneath stays readable. */
        .medcite-hl { background-color: rgba(255, 210, 0, 0.40); color: transparent; border-radius: 2px; }
        .medcite-pdf-page { margin: 0 auto 14px auto; box-shadow: var(--shadow-md); background:#fff; }
        .medcite-pdf-page .react-pdf__Page__canvas { border-radius: 4px; }
      `}</style>

      {/* Header */}
      <div style={{
        padding: '14px 18px',
        backgroundColor: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
          <div style={{
            width: '32px', height: '32px', borderRadius: '6px',
            backgroundColor: 'var(--accent-sage-light)', color: 'var(--accent-sage-dark)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
          }}>
            <FileText size={18} />
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {currentDrug ? currentDrug.name : 'Prescribing PDF'}
            </div>
            <div style={{ fontSize: '0.73rem', color: 'var(--text-secondary)' }}>
              Official PDF: <code style={{ fontFamily: 'var(--font-mono)' }}>{currentDrug?.pdf || 'document.pdf'}</code>
            </div>
          </div>
        </div>
        <button onClick={onClose} title="Close PDF Panel" style={{
          background: 'transparent', border: 'none', color: 'var(--text-muted)',
          cursor: 'pointer', padding: '4px', borderRadius: '4px', display: 'flex'
        }}>
          <X size={18} />
        </button>
      </div>

      {/* Page navigation */}
      <div style={{
        padding: '8px 16px', backgroundColor: 'var(--bg-surface-subtle)',
        borderBottom: '1px solid var(--border-subtle)', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button type="button" onClick={() => goto(currentPage - 1)} disabled={currentPage <= 1}
            style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '2px 6px', cursor: currentPage <= 1 ? 'not-allowed' : 'pointer', opacity: currentPage <= 1 ? 0.4 : 1 }}>
            <ChevronLeft size={14} />
          </button>
          <form onSubmit={(e) => { e.preventDefault(); goto(parseInt(pageInput, 10) || 1); }} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ fontWeight: 600 }}>Page</span>
            <input type="text" value={pageInput} onChange={(e) => setPageInput(e.target.value)} onBlur={(e) => goto(parseInt(e.target.value, 10) || currentPage)}
              style={{ width: '40px', textAlign: 'center', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '1px 2px', fontSize: '0.8rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)' }} />
            <span style={{ opacity: 0.6 }}>/ {numPages || '—'}</span>
          </form>
          <button type="button" onClick={() => goto(currentPage + 1)} disabled={numPages ? currentPage >= numPages : true}
            style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '2px 6px', cursor: 'pointer', opacity: (numPages && currentPage < numPages) ? 1 : 0.4 }}>
            <ChevronRight size={14} />
          </button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Zoom controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '3px' }}>
            <button type="button" title="Zoom out" onClick={() => setZoom(z => Math.max(0.6, +(z - 0.15).toFixed(2)))}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 30, height: 28, background: 'var(--bg-surface-subtle)', border: '1px solid var(--border-color)', borderRadius: '6px', cursor: 'pointer', color: 'var(--text-primary)' }}>
              <ZoomOut size={18} />
            </button>
            <span style={{ minWidth: 46, textAlign: 'center', fontSize: '0.85rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-primary)' }}>{Math.round(zoom * 100)}%</span>
            <button type="button" title="Zoom in" onClick={() => setZoom(z => Math.min(3, +(z + 0.15).toFixed(2)))}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 30, height: 28, background: 'var(--bg-surface-subtle)', border: '1px solid var(--border-color)', borderRadius: '6px', cursor: 'pointer', color: 'var(--text-primary)' }}>
              <ZoomIn size={18} />
            </button>
          </div>
          {activeCitation && (
            <span style={{ backgroundColor: 'var(--accent-sage-light)', color: 'var(--accent-sage-dark)', padding: '4px 8px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
              p. {activeCitation.page}
            </span>
          )}
        </div>
      </div>

      {/* PDF scroll area */}
      <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', overflowX: 'auto', padding: '16px', backgroundColor: 'var(--bg-canvas)' }}>
        {!pdfUrl || loadError ? (
          <div style={{ padding: '30px 16px', textAlign: 'center', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
            <AlertCircle size={26} style={{ color: 'var(--accent-amber, #C9922B)' }} />
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>No PDF loaded for “{currentDrug?.name || selectedDrug}”.</div>
            <div style={{ fontSize: '0.82rem', lineHeight: 1.5 }}>
              Upload this medicine’s PDF (Upload PDF button, top right) and it will appear here, page by page, with the cited text highlighted.
            </div>
          </div>
        ) : (
          <Document
            file={fileProp}
            options={options}
            onLoadSuccess={onDocLoad}
            onLoadError={() => setLoadError(true)}
            loading={<div style={{ display: 'flex', gap: 8, alignItems: 'center', justifyContent: 'center', padding: 40, color: 'var(--text-secondary)' }}><Loader2 size={18} className="spin" /> Loading PDF…</div>}
          >
            {numPages && Array.from({ length: numPages }, (_, i) => i + 1).map((p) => {
              // Render only pages near the viewport (and the cited page). The
              // rest are light placeholders sized so scrolling stays accurate.
              const estHeight = Math.round(pageWidth * 1.3);
              const render = Math.abs(p - currentPage) <= 1 || p === activeCitation?.page;
              return (
                <div key={p} data-page={p} ref={(el) => { if (el) pageRefs.current[p] = el; }}
                  className="medcite-pdf-page" style={{ position: 'relative' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', padding: '2px 4px' }}>
                    Page {p}{activeCitation?.page === p ? '  • cited' : ''}
                  </div>
                  {render ? (
                    <Page
                      pageNumber={p}
                      width={pageWidth}
                      renderAnnotationLayer={false}
                      renderTextLayer={true}
                      customTextRenderer={makeTextRenderer(p)}
                      loading={<div style={{ height: estHeight, background: '#fff' }} />}
                    />
                  ) : (
                    <div style={{ height: estHeight, background: '#fff', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                      Page {p}
                    </div>
                  )}
                </div>
              );
            })}
          </Document>
        )}
      </div>
    </aside>
  );
}
