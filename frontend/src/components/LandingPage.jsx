import React from 'react';
import {
  Pill,
  ShieldCheck,
  FileText,
  Sparkles,
  BookOpen,
  AlertTriangle,
  RefreshCcw,
  ArrowRight,
  Bot,
  CheckCircle2
} from 'lucide-react';

export default function LandingPage({ onGetStarted }) {
  const featureCards = [
    {
      icon: Pill,
      title: 'Drug Information',
      description: 'Get information about medicines and their common uses directly from official prescribing labels.',
      badge: 'Core Feature'
    },
    {
      icon: FileText,
      title: 'Dosage & Administration',
      description: 'Understand dosage-related information, starting doses, and administration directions available in the knowledge base.',
      badge: 'Clinical Data'
    },
    {
      icon: AlertTriangle,
      title: 'Side Effects & Precautions',
      description: 'Learn about potential adverse reactions, boxed warnings, contraindications, and mandatory precautions.',
      badge: 'Safety First'
    },
    {
      icon: RefreshCcw,
      title: 'Drug Interactions',
      description: 'Find relevant information about possible drug-drug interactions and laboratory testing precautions.',
      badge: 'Interactions'
    },
    {
      icon: BookOpen,
      title: 'PDF-Based Knowledge',
      description: 'Answers are generated strictly using the official medical/drug information documents provided to the system.',
      badge: 'RAG Pipeline'
    },
    {
      icon: Bot,
      title: 'AI-Powered Q&A',
      description: 'Ask questions naturally, follow up with conversation context, and receive structured, page-cited answers.',
      badge: 'Responsible AI'
    }
  ];

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: 'var(--bg-canvas)',
      color: 'var(--text-primary)',
      fontFamily: 'var(--font-sans)',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Top Header Bar */}
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
        {/* Brand Logo with Custom Healthcare AI Icon */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            position: 'relative',
            width: '42px',
            height: '42px',
            borderRadius: '12px',
            backgroundColor: 'var(--accent-sage-light)',
            border: '1.5px solid var(--accent-sage-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--accent-sage)',
            boxShadow: 'var(--shadow-sm)'
          }}>
            <Pill size={20} style={{ transform: 'rotate(-45deg)' }} />
            <ShieldCheck size={14} style={{
              position: 'absolute',
              bottom: '2px',
              right: '2px',
              color: 'var(--accent-sage-dark)'
            }} />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
                MedCite
              </span>
              <span style={{
                fontSize: '0.68rem',
                fontWeight: 700,
                backgroundColor: 'var(--accent-sage-light)',
                color: 'var(--accent-sage-dark)',
                padding: '2px 8px',
                borderRadius: '999px',
                border: '1px solid var(--accent-sage-border)'
              }}>
                RAG Engine
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              Drug Information Q&A Chatbot
            </p>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section style={{
        padding: '80px 20px 60px 20px',
        maxWidth: '1100px',
        margin: '0 auto',
        textAlign: 'center',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center'
      }}>
        {/* Responsible AI Badge */}
        <div className="animate-fade-in" style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          backgroundColor: 'var(--accent-sage-light)',
          color: 'var(--accent-sage-dark)',
          border: '1px solid var(--accent-sage-border)',
          borderRadius: '999px',
          padding: '6px 16px',
          fontSize: '0.82rem',
          fontWeight: 600,
          marginBottom: '24px'
        }}>
          <Sparkles size={14} />
          <span>Verifiable Medical RAG Platform • Responsible AI</span>
        </div>

        {/* Project Title */}
        <h1 className="animate-fade-in" style={{
          fontSize: '2.8rem',
          fontWeight: 800,
          color: 'var(--text-primary)',
          letterSpacing: '-0.03em',
          lineHeight: 1.15,
          marginBottom: '16px',
          maxWidth: '900px'
        }}>
          Drug Information Q&A Chatbot
        </h1>

        {/* Tagline */}
        <p className="animate-fade-in" style={{
          fontSize: '1.35rem',
          fontWeight: 600,
          color: 'var(--accent-sage-dark)',
          marginBottom: '20px',
          letterSpacing: '-0.01em'
        }}>
          “Your AI-Powered Assistant for Reliable Drug Information”
        </p>

        {/* Short Description */}
        <p className="animate-fade-in" style={{
          fontSize: '1.05rem',
          color: 'var(--text-secondary)',
          maxWidth: '780px',
          lineHeight: 1.6,
          marginBottom: '36px'
        }}>
          Get clear and structured information about medicines, their uses, dosage, side effects, precautions, interactions, and other important drug-related details through an easy-to-use AI chatbot.
        </p>

        {/* SINGLE "Get Started" Button */}
        <div className="animate-fade-in" style={{ display: 'flex', justifyContent: 'center' }}>
          <button
            type="button"
            onClick={onGetStarted}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '10px',
              backgroundColor: 'var(--accent-sage)',
              color: 'var(--text-inverse)',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              padding: '14px 36px',
              fontSize: '1.05rem',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: 'var(--shadow-md)',
              transition: 'all 0.15s ease'
            }}
          >
            <span>Get Started</span>
            <ArrowRight size={18} />
          </button>
        </div>

        {/* Trust Points Ribbon */}
        <div style={{
          marginTop: '60px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '24px',
          flexWrap: 'wrap',
          fontSize: '0.85rem',
          color: 'var(--text-secondary)',
          borderTop: '1px solid var(--border-subtle)',
          paddingTop: '24px',
          width: '100%',
          maxWidth: '860px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <CheckCircle2 size={16} style={{ color: 'var(--accent-sage)' }} />
            <span>100% Page Citations</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <CheckCircle2 size={16} style={{ color: 'var(--accent-sage)' }} />
            <span>Hallucination Prevention</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <CheckCircle2 size={16} style={{ color: 'var(--accent-sage)' }} />
            <span>Official Prescribing PDFs</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <CheckCircle2 size={16} style={{ color: 'var(--accent-sage)' }} />
            <span>Medical Disclaimer Safeguards</span>
          </div>
        </div>
      </section>

      {/* Feature Cards Section ("What Our Project Provides") */}
      <section style={{
        padding: '60px 20px',
        backgroundColor: 'var(--bg-surface-subtle)',
        borderTop: '1px solid var(--border-color)',
        borderBottom: '1px solid var(--border-color)'
      }}>
        <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '44px' }}>
            <span style={{
              fontSize: '0.78rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: 'var(--accent-sage-dark)'
            }}>
              PROJECT CAPABILITIES
            </span>
            <h2 style={{
              fontSize: '2rem',
              fontWeight: 800,
              color: 'var(--text-primary)',
              letterSpacing: '-0.02em',
              marginTop: '6px'
            }}>
              What Our Project Provides
            </h2>
            <p style={{ fontSize: '0.96rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
              Structured, reliable answers backed by verifiable page-level evidence from prescribing documents.
            </p>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '20px'
          }}>
            {featureCards.map((card, idx) => {
              const CardIcon = card.icon;
              return (
                <div
                  key={idx}
                  style={{
                    backgroundColor: 'var(--bg-surface)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-lg)',
                    padding: '24px',
                    boxShadow: 'var(--shadow-sm)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    transition: 'all 0.2s ease-in-out'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--accent-sage)';
                    e.currentTarget.style.transform = 'translateY(-3px)';
                    e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'var(--border-color)';
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                      <div style={{
                        width: '42px',
                        height: '42px',
                        borderRadius: '10px',
                        backgroundColor: 'var(--accent-sage-light)',
                        color: 'var(--accent-sage)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        border: '1px solid var(--accent-sage-border)'
                      }}>
                        <CardIcon size={22} />
                      </div>
                      <span style={{
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        backgroundColor: 'var(--bg-surface-subtle)',
                        color: 'var(--text-secondary)',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        border: '1px solid var(--border-subtle)'
                      }}>
                        {card.badge}
                      </span>
                    </div>

                    <h3 style={{
                      fontSize: '1.1rem',
                      fontWeight: 700,
                      color: 'var(--text-primary)',
                      marginBottom: '8px'
                    }}>
                      {card.title}
                    </h3>

                    <p style={{
                      fontSize: '0.9rem',
                      color: 'var(--text-secondary)',
                      lineHeight: 1.55
                    }}>
                      {card.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{
        marginTop: 'auto',
        padding: '20px 40px',
        backgroundColor: 'var(--bg-surface)',
        borderTop: '1px solid var(--border-color)',
        textAlign: 'center',
        fontSize: '0.8rem',
        color: 'var(--text-secondary)'
      }}>
        <div>
          <strong>Cognizant + GITAM Student Buildathon</strong> • Use Case #7: Drug Information Q&A Chatbot with Citations
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
          GenAI / RAG / Responsible AI • Built for verifiable, proof-backed medical document exploration.
        </div>
      </footer>
    </div>
  );
}
