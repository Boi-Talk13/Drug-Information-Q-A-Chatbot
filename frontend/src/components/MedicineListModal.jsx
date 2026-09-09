import React, { useState, useRef } from 'react';
import { X, Upload, FileText, CheckCircle2, AlertCircle, Loader2, Sparkles, ExternalLink } from 'lucide-react';
import { getAvailableDrugs, uploadMedicinePdf } from '../services/apiService';

export default function MedicineListModal({ selectedDrug, onSelectDrug, onClose, useLiveApi }) {
  const [medicines, setMedicines] = useState(getAvailableDrugs());
  const [isUploading, setIsUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const fileInputRef = useRef(null);

  const handleUploadClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setErrorMsg(null);
    setSuccessMsg(null);

    // Validate PDF file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setErrorMsg('Invalid file type. Please select an official medicine Prescribing Information PDF (.pdf).');
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    setIsUploading(true);

    try {
      const newMed = await uploadMedicinePdf(file, useLiveApi);
      setMedicines(getAvailableDrugs());
      onSelectDrug(newMed.id);
      setSuccessMsg(`Successfully loaded and indexed "${file.name}". PDF is ready for Q&A!`);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to upload PDF file.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
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
              <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                Medicine PDF Library
              </h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0 }}>
                Data-driven list of prescribing PDFs loaded into the RAG search index
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
            fontSize: '0.84rem',
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
            fontSize: '0.84rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Action Upload Bar */}
        <div style={{
          padding: '16px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid var(--border-subtle)',
          backgroundColor: 'var(--bg-canvas)'
        }}>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Total Loaded PDFs: <strong style={{ color: 'var(--text-primary)' }}>{medicines.length}</strong>
          </div>

          <button
            type="button"
            onClick={handleUploadClick}
            disabled={isUploading}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: 'var(--accent-sage)',
              color: 'var(--text-inverse)',
              border: 'none',
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: isUploading ? 'not-allowed' : 'pointer',
              boxShadow: 'var(--shadow-sm)',
              transition: 'all 0.15s ease'
            }}
          >
            {isUploading ? <Loader2 size={16} className="pulse-badge" /> : <Upload size={16} />}
            <span>{isUploading ? 'Parsing & Indexing PDF...' : 'Upload Medicine PDF (.pdf)'}</span>
          </button>
        </div>

        {/* Scrollable Medicines List */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          {medicines.map((med) => {
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
                      <h4 style={{ fontSize: '0.94rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
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
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '2px', display: 'flex', gap: '12px' }}>
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
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
