import React, { useState } from 'react';
import { ShieldCheck, FileText, RefreshCw, PanelRight, Database, Upload, Plus, PanelLeft, Pill, ArrowLeft } from 'lucide-react';
import { getAvailableDrugs } from '../services/apiService';
import MedicineListModal from './MedicineListModal';

export default function ChatHeader({
  selectedDrug,
  onSelectDrug,
  useLiveApi,
  onToggleLiveApi,
  showPdfPanel,
  onTogglePdfPanel,
  showHistorySidebar,
  onToggleHistorySidebar,
  onNewChat,
  onClearChat,
  isChatEmpty,
  onBackToLanding
}) {
  const [showLibraryModal, setShowLibraryModal] = useState(false);
  const drugs = getAvailableDrugs();
  const currentDrug = drugs.find(d => d.id === selectedDrug) || drugs[0];

  const handleNewChatClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (typeof onNewChat === 'function') {
      onNewChat();
    }
  };

  return (
    <>
      <header className="chat-header" style={{
        backgroundColor: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border-color)',
        padding: '12px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        boxShadow: 'var(--shadow-sm)'
      }}>
        {/* Left Brand, Sidebar Toggle, & Back Navigation */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Explicit Back to Landing Page Button */}
          {onBackToLanding && (
            <button
              type="button"
              onClick={onBackToLanding}
              title="Return to Landing Page"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: 'var(--bg-surface-subtle)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-primary)',
                borderRadius: 'var(--radius-md)',
                padding: '7px 12px',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              <ArrowLeft size={15} />
              <span>Back</span>
            </button>
          )}

          {/* History Sidebar Toggle Button */}
          <button
            type="button"
            onClick={onToggleHistorySidebar}
            title={showHistorySidebar ? "Close Chat History Sidebar" : "Open Chat History Sidebar"}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '36px',
              height: '36px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: showHistorySidebar ? 'var(--accent-sage-light)' : 'var(--bg-canvas)',
              border: `1px solid ${showHistorySidebar ? 'var(--accent-sage-border)' : 'var(--border-color)'}`,
              color: showHistorySidebar ? 'var(--accent-sage-dark)' : 'var(--text-secondary)',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            <PanelLeft size={18} />
          </button>

          {/* New Chat Button */}
          <button
            type="button"
            onClick={handleNewChatClick}
            title="Start New Chat"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: 'var(--accent-sage)',
              color: 'var(--text-inverse)',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              padding: '7px 12px',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: 'var(--shadow-sm)',
              transition: 'all 0.15s ease'
            }}
          >
            <Plus size={15} style={{ pointerEvents: 'none' }} />
            <span style={{ pointerEvents: 'none' }}>New Chat</span>
          </button>

          {/* Brand Logo & Subtitle */}
          <div
            onClick={onBackToLanding}
            title="Return to Landing Page"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              marginLeft: '4px',
              cursor: onBackToLanding ? 'pointer' : 'default'
            }}
          >
            <div style={{
              position: 'relative',
              width: '34px',
              height: '34px',
              borderRadius: '8px',
              backgroundColor: 'var(--accent-sage-light)',
              color: 'var(--accent-sage)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid var(--accent-sage-border)'
            }}>
              <Pill size={16} style={{ transform: 'rotate(-45deg)' }} />
              <ShieldCheck size={11} style={{
                position: 'absolute',
                bottom: '1px',
                right: '1px',
                color: 'var(--accent-sage-dark)'
              }} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h1 style={{
                  fontSize: '1.2rem',
                  fontWeight: 700,
                  color: 'var(--text-primary)',
                  letterSpacing: '-0.02em',
                  lineHeight: 1.2
                }}>
                  MedCite
                </h1>
                <span style={{
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  padding: '2px 7px',
                  borderRadius: '999px',
                  backgroundColor: 'var(--accent-sage-light)',
                  color: 'var(--accent-sage-dark)',
                  border: '1px solid var(--accent-sage-border)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px'
                }}>
                  <span className="pulse-badge" style={{
                    width: '5px',
                    height: '5px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--accent-sage)'
                  }}></span>
                  Verified Drug PDFs
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Controls & PDF Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Active Drug Dropdown & Library Manager */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: 'var(--bg-surface-subtle)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-md) 0 0 var(--radius-md)',
              padding: '6px 10px',
              fontSize: '0.82rem',
              color: 'var(--text-primary)'
            }}>
              <FileText size={15} style={{ color: 'var(--accent-sage)' }} />
              <select
                value={selectedDrug}
                onChange={(e) => onSelectDrug(e.target.value)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-primary)',
                  fontWeight: 600,
                  fontSize: '0.82rem',
                  cursor: 'pointer',
                  outline: 'none',
                  paddingRight: '4px'
                }}
              >
                {drugs.map(d => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              onClick={() => setShowLibraryModal(true)}
              title="Open Medicine Library & Upload PDF"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                backgroundColor: 'var(--accent-sage-light)',
                border: '1px solid var(--accent-sage-border)',
                color: 'var(--accent-sage-dark)',
                borderRadius: '0 var(--radius-md) var(--radius-md) 0',
                padding: '6px 10px',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              <Upload size={13} />
              <span>Upload PDF</span>
            </button>
          </div>

          {/* API Engine Toggle (Mock vs FastAPI) */}
          <button
            type="button"
            onClick={onToggleLiveApi}
            title={useLiveApi ? 'Switch to Offline Demo Engine Mode' : 'Switch to Live FastAPI Backend'}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: useLiveApi ? 'var(--accent-blue-light)' : 'var(--bg-canvas)',
              border: `1px solid ${useLiveApi ? 'var(--accent-blue-border)' : 'var(--border-color)'}`,
              color: useLiveApi ? 'var(--accent-blue)' : 'var(--text-secondary)',
              borderRadius: 'var(--radius-md)',
              padding: '6px 10px',
              fontSize: '0.78rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            <Database size={14} />
            <span>{useLiveApi ? 'Live API' : 'Demo Mode'}</span>
          </button>

          {/* PDF Split View Toggle */}
          <button
            type="button"
            onClick={onTogglePdfPanel}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: showPdfPanel ? 'var(--accent-sage-light)' : 'var(--bg-canvas)',
              border: `1px solid ${showPdfPanel ? 'var(--accent-sage-border)' : 'var(--border-color)'}`,
              color: showPdfPanel ? 'var(--accent-sage)' : 'var(--text-secondary)',
              borderRadius: 'var(--radius-md)',
              padding: '6px 10px',
              fontSize: '0.78rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            <PanelRight size={15} />
            <span>{showPdfPanel ? 'Hide PDF' : 'PDF Viewer'}</span>
          </button>

          {/* Clear Current Chat */}
          {!isChatEmpty && (
            <button
              type="button"
              onClick={onClearChat}
              title="Clear current conversation stream"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '32px',
                height: '32px',
                backgroundColor: 'transparent',
                border: '1px solid var(--border-color)',
                color: 'var(--text-muted)',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              <RefreshCw size={14} />
            </button>
          )}
        </div>
      </header>

      {/* Medicine PDF Library & Upload Modal */}
      {showLibraryModal && (
        <MedicineListModal
          selectedDrug={selectedDrug}
          onSelectDrug={onSelectDrug}
          useLiveApi={useLiveApi}
          onClose={() => setShowLibraryModal(false)}
        />
      )}
    </>
  );
}
