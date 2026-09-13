/**
 * MedicineListModal — the "Medicine PDF Library" popup.
 * Lists THIS user's uploaded PDFs, lets them upload one or many at once,
 * select one for Q&A, or delete one. All actions call the backend scoped by
 * user_id so each user manages only their own private library.
 */
import React, { useState, useRef, useEffect } from 'react';
import { X, Upload, FileText, CheckCircle2, AlertCircle, Loader2, Trash2, Link2, ShieldCheck } from 'lucide-react';
import { getAvailableDrugs, fetchAvailableDrugs, uploadMedicinePdfs, deleteMedicine, checkSourceUrl, getSourcePolicy } from '../services/apiService';

export default function MedicineListModal({ selectedDrug, onSelectDrug, onClose, useLiveApi, onLibraryChanged }) {
  const [medicines, setMedicines] = useState(getAvailableDrugs());
  const [isUploading, setIsUploading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  // A PDF can only be added by pasting the official link it is published at.
  // The link is typed here and verified again by the backend.
  const [sourceUrl, setSourceUrl] = useState('');
  const policy = getSourcePolicy();
  // The built-in library lives in the header dropdown; this dialog only shows
  // what the user added themselves, because only those can be deleted.
  const ownUploads = medicines.filter(m => !m.shared);
  // Live feedback on the link alone (the file is checked when it is picked).
  const linkError = sourceUrl.trim() ? checkSourceUrl(sourceUrl) : null;
  const linkReady = sourceUrl.trim() && !linkError;

  const fileInputRef = useRef(null);

  // Load the real, indexed medicine list from the backend when live.
  useEffect(() => {
    let alive = true;
    if (useLiveApi) {
      fetchAvailableDrugs().then(list => { if (alive) setMedicines(list); });
    } else {
      setMedicines(getAvailableDrugs());
    }
    return () => { alive = false; };
  }, [useLiveApi]);

  const handleFileChange = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    setErrorMsg(null);
    setSuccessMsg(null);
    setIsUploading(true);

    try {
      const added = await uploadMedicinePdfs(files, useLiveApi, sourceUrl.trim());
      const list = getAvailableDrugs();
      setMedicines(list);
      if (added[0]?.id) onSelectDrug(added[0].id);
      onLibraryChanged && onLibraryChanged();
      setSuccessMsg(`Verified against ${policy.host} — loaded and indexed `
        + `"${added[0].name}". Ready for Q&A!`);
      setSourceUrl('');
    } catch (err) {
      setErrorMsg(err.message || 'Failed to upload PDF file(s).');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (med) => {
    if (!window.confirm(`Delete "${med.name}" and its PDF from the library?`)) return;
    setErrorMsg(null);
    setSuccessMsg(null);
    setDeletingId(med.id);
    try {
      await deleteMedicine(med.id, useLiveApi);
      const list = getAvailableDrugs();
      setMedicines(list);
      onLibraryChanged && onLibraryChanged();
      if (med.id === selectedDrug && list[0]) onSelectDrug(list[0].id);
      setSuccessMsg(`Deleted "${med.name}".`);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to delete.');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(31, 37, 34, 0.45)',
      backdropFilter: 'blur(3px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div className="animate-fade-in" style={{
        backgroundColor: 'var(--bg-surface)',
        border: '1px solid var(--border-color)',
        borderRadius: 'var(--radius-lg)',
        width: '100%',
        maxWidth: '680px',
        maxHeight: '85vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: 'var(--shadow-lg)',
        overflow: 'hidden'
      }}>
        {/* Modal Header */}
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'var(--bg-surface-subtle)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FileText size={22} style={{ color: 'var(--accent-sage)' }} />
            <div>
              <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                Add a Medicine PDF
              </h2>
              <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', margin: 0 }}>
                Browse and switch medicines from the dropdown in the header
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Hidden File Input for PDF Upload */}
        <input
          type="file"
          ref={fileInputRef}
          accept=".pdf"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />

        {/* Alert Banners */}
        {errorMsg && (
          <div style={{
            margin: '16px 24px 0 24px',
            backgroundColor: 'var(--accent-red-light)',
            border: '1px solid var(--accent-red-border)',
            color: 'var(--accent-red)',
            padding: '10px 14px',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.95rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <span>{errorMsg}</span>
          </div>
        )}

        {successMsg && (
          <div style={{
            margin: '16px 24px 0 24px',
            backgroundColor: 'var(--accent-sage-light)',
            border: '1px solid var(--accent-sage-border)',
            color: 'var(--accent-sage-dark)',
            padding: '10px 14px',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.95rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Source-link box. A PDF is only accepted when the user can supply
            the official link it is published at, and the file they pick has
            the same name as that link. */}
        {(
          <div style={{
            padding: '14px 24px',
            borderBottom: '1px solid var(--border-subtle)',
            backgroundColor: 'var(--bg-surface-subtle)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <ShieldCheck size={15} style={{ color: 'var(--accent-sage)' }} />
              <span style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                Verified source required
              </span>
            </div>
            <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', margin: '0 0 12px 0', lineHeight: 1.55 }}>
              Only prescribing PDFs published on <strong>{policy.host}</strong> can be added
              {policy.catalogSize ? ` (${policy.catalogSize} documents)` : ''}. Paste the link
              to the PDF, then choose that same file from your computer.
            </p>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="url"
                className="source-url-input"
                value={sourceUrl}
                autoFocus
                spellCheck={false}
                placeholder={`example: https://${policy.host}/pdf/rinvoq_pi.pdf`}
                onChange={(e) => { setSourceUrl(e.target.value); setErrorMsg(null); }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && linkReady && fileInputRef.current) {
                    fileInputRef.current.click();
                  }
                }}
                style={{
                  flex: 1,
                  padding: '11px 14px',
                  borderRadius: 'var(--radius-sm)',
                  border: `1px solid ${linkError ? 'var(--accent-red, #B4453C)' : (linkReady ? 'var(--accent-sage)' : 'var(--border-color)')}`,
                  backgroundColor: 'var(--bg-surface)',
                  color: 'var(--text-primary)',
                  fontSize: '0.98rem',
                  fontFamily: 'var(--font-mono, monospace)'
                }}
              />
              <button
                type="button"
                disabled={!linkReady}
                onClick={() => fileInputRef.current && fileInputRef.current.click()}
                style={{
                  backgroundColor: linkReady ? 'var(--accent-sage)' : 'var(--bg-surface-subtle)',
                  color: linkReady ? 'var(--text-inverse)' : 'var(--text-muted)',
                  border: '1px solid var(--border-color)',
                  padding: '8px 16px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.95rem',
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                  cursor: linkReady ? 'pointer' : 'not-allowed'
                }}
              >
                Choose PDF
              </button>
            </div>

            {/* The caution: link and file must name the same document. */}
            <div style={{
              display: 'flex', alignItems: 'flex-start', gap: '6px', marginTop: '8px',
              fontSize: '0.87rem',
              lineHeight: 1.5,
              color: linkError ? 'var(--accent-red, #B4453C)' : 'var(--text-muted)'
            }}>
              <AlertCircle size={13} style={{ flexShrink: 0, marginTop: '1px' }} />
              <span>
                {linkError
                  ? linkError
                  : linkReady
                    ? `Link verified. Now choose "${decodeURIComponent(sourceUrl.trim()).split('/').pop()}" — the file name must match the link.`
                    : 'The link and the PDF file name must be the same, or the upload is rejected.'}
              </span>
            </div>
          </div>
        )}

        {/* Only the user's OWN uploads are listed here. The built-in library
            is browsed from the medicine dropdown in the header — repeating it
            in this dialog was just a second copy of the same list. What can't
            be done from the dropdown is DELETING an upload, so that stays. */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: ownUploads.length ? '20px 24px' : '0 24px 20px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          {ownUploads.length > 0 && (
            <div style={{
              fontSize: '0.82rem', fontWeight: 600, letterSpacing: '0.04em',
              textTransform: 'uppercase', color: 'var(--text-muted)'
            }}>
              Your uploads
            </div>
          )}
          {ownUploads.map((med) => {
            const isSelected = med.id === selectedDrug;
            return (
              <div
                key={med.id}
                style={{
                  backgroundColor: isSelected ? 'var(--accent-sage-light)' : 'var(--bg-surface)',
                  border: `1.5px solid ${isSelected ? 'var(--accent-sage-border)' : 'var(--border-color)'}`,
                  borderRadius: 'var(--radius-md)',
                  padding: '14px 18px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '16px',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '8px',
                    backgroundColor: isSelected ? 'var(--accent-sage)' : 'var(--bg-surface-subtle)',
                    color: isSelected ? 'var(--text-inverse)' : 'var(--accent-sage)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px solid var(--border-color)',
                    flexShrink: 0
                  }}>
                    <FileText size={20} />
                  </div>

                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                        {med.name}
                      </h4>
                      {isSelected && (
                        <span style={{
                          fontSize: '0.68rem',
                          fontWeight: 700,
                          backgroundColor: 'var(--accent-sage)',
                          color: 'var(--text-inverse)',
                          padding: '1px 6px',
                          borderRadius: '4px'
                        }}>
                          ACTIVE FOR Q&A
                        </span>
                      )}
                      {med.shared && (
                        <span
                          title="Part of the verified built-in library — available to every user"
                          style={{
                            fontSize: '0.68rem',
                            fontWeight: 700,
                            backgroundColor: 'var(--bg-surface-subtle)',
                            color: 'var(--text-secondary)',
                            border: '1px solid var(--border-color)',
                            padding: '1px 6px',
                            borderRadius: '4px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '3px'
                          }}>
                          <ShieldCheck size={11} /> BUILT-IN
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.87rem', color: 'var(--text-secondary)', marginTop: '3px', display: 'flex', gap: '12px' }}>
                      <span>PDF: <code style={{ fontFamily: 'var(--font-mono)' }}>{med.pdf}</code></span>
                      <span>Pages: {med.pages}</span>
                      {med.manufacturer && <span>Mfr: {med.manufacturer}</span>}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {!isSelected ? (
                    <button
                      type="button"
                      onClick={() => {
                        onSelectDrug(med.id);
                        onClose();
                      }}
                      style={{
                        backgroundColor: 'var(--bg-surface)',
                        border: '1px solid var(--border-color)',
                        color: 'var(--text-primary)',
                        padding: '6px 12px',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.8rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      Select
                    </button>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--accent-sage-dark)', fontSize: '0.8rem', fontWeight: 600 }}>
                      <CheckCircle2 size={16} />
                      <span>Selected</span>
                    </div>
                  )}
                  {/* Built-in library PDFs are read-only — no delete control. */}
                  {!med.shared && (
                  <button
                    type="button"
                    title={`Delete ${med.name}`}
                    onClick={() => handleDelete(med)}
                    disabled={deletingId === med.id}
                    style={{
                      backgroundColor: 'transparent',
                      border: '1px solid var(--accent-red-border, #E4B4B4)',
                      color: 'var(--accent-red, #B4453C)',
                      padding: '6px 8px',
                      borderRadius: 'var(--radius-sm)',
                      cursor: deletingId === med.id ? 'not-allowed' : 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '0.8rem'
                    }}
                  >
                    {deletingId === med.id ? <Loader2 size={14} className="pulse-badge" /> : <Trash2 size={14} />}
                  </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
