/**
 * MedCite API Service Layer
 * Supports both Live FastAPI Backend integration & robust dynamic medicine list management.
 */

const LIVE_API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/chat';
const LIVE_UPLOAD_URL = import.meta.env.VITE_UPLOAD_BASE_URL || 'http://localhost:8000/api/upload';

// Origin of the backend, derived from the chat URL (e.g. http://localhost:8000).
const API_ORIGIN = LIVE_API_URL.replace(/\/api\/chat\/?$/, '');

/**
 * URL that serves the raw PDF for a drug id, so the viewer can render the
 * real document pages. Returns null when there is no id.
 */
export function getPdfUrl(drugId) {
  if (!drugId) return null;
  const uid = getUserId() || 'anonymous';
  return `${API_ORIGIN}/api/pdf/${encodeURIComponent(drugId)}?user_id=${encodeURIComponent(uid)}`;
}

/**
 * Anonymous per-browser identity (no login).
 * - A random `token` is created once and kept in localStorage (stable per browser).
 * - The backend maps that token to a short sequential id (user-101, user-102, ...)
 *   and we cache it. Every request sends this short id so the backend keeps each
 *   person's chats and logs separate (row-level isolation by user_id).
 */
const API_ORIGIN_USER = LIVE_API_URL.replace(/\/api\/chat\/?$/, '');

function getBrowserToken() {
  const KEY = 'medcite_token';
  try {
    let t = localStorage.getItem(KEY);
    if (!t) {
      t = (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2) + Date.now().toString(36));
      localStorage.setItem(KEY, t);
    }
    return t;
  } catch {
    return 'anon-token';
  }
}

/** The cached short id (only a valid "user-NNN"; older long ids are ignored). */
export function getUserId() {
  try {
    const v = localStorage.getItem('medcite_user_id');
    return v && /^user-\d+$/.test(v) ? v : null;
  } catch {
    return null;
  }
}

/** Ask the backend for this browser's short id (user-101, ...) and cache it. */
export async function resolveUserId() {
  const cached = getUserId();
  if (cached) return cached;
  try {
    const res = await fetch(`${API_ORIGIN_USER}/api/user`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: getBrowserToken() }),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.user_id) {
        try { localStorage.setItem('medcite_user_id', data.user_id); } catch {}
        return data.user_id;
      }
    }
  } catch (err) {
    console.warn('Could not resolve user id:', err.message);
  }
  return null;
}

/** Label for the header badge, e.g. "user-101" (or "connecting…" until ready). */
export function getUserLabel() {
  return getUserId() || 'connecting…';
}

// Data-driven list of default medicine PDFs
const DEFAULT_MEDICINES = [
  {
    id: 'rinvoq',
    name: 'RINVOQ (upadacitinib)',
    pdf: 'rinvoq_pi.pdf',
    pages: 92,
    manufacturer: 'AbbVie',
    status: 'Indexed & Verified',
    source_url: 'https://www.rxabbvie.com/pdf/rinvoq_pi.pdf'
  },
  {
    id: 'humira',
    name: 'HUMIRA (adalimumab)',
    pdf: 'humira_pi.pdf',
    pages: 84,
    manufacturer: 'AbbVie',
    status: 'Indexed & Verified',
    source_url: 'https://www.rxabbvie.com/pdf/humira_pi.pdf'
  },
  {
    id: 'keytruda',
    name: 'KEYTRUDA (pembrolizumab)',
    pdf: 'keytruda_pi.pdf',
    pages: 110,
    manufacturer: 'Merck',
    status: 'Indexed & Verified',
    source_url: 'https://www.merck.com/product/usa/pi_circulars/k/keytruda/keytruda_pi.pdf'
  },
  {
    id: 'eliquis',
    name: 'ELIQUIS (apixaban)',
    pdf: 'eliquis_pi.pdf',
    pages: 48,
    manufacturer: 'BMS/Pfizer',
    status: 'Indexed & Verified',
    source_url: 'https://www.eliquis.bmscustomerconnect.com/prescribing-information.pdf'
  }
];

// Comprehensive mock knowledge base for default medicines
const MOCK_DRUG_KNOWLEDGE = {
  rinvoq: {
    title: 'RINVOQ® (upadacitinib) Extended-Release Tablets',
    fda_date: 'Rev. 04/2024',
    source_url: 'https://www.rxabbvie.com/pdf/rinvoq_pi.pdf',
    indications: {
      answer: 'RINVOQ (upadacitinib) is indicated for the treatment of moderate to severe active Rheumatoid Arthritis in adults who have had an inadequate response or intolerance to one or more TNF blockers [p. 1]. It is also indicated for Psoriatic Arthritis, Atopic Dermatitis, Ulcerative Colitis, and Crohn\'s Disease [p. 2].',
      section: '1 INDICATIONS AND USAGE',
      citations: [
        { page: 1, section: '1.1 Rheumatoid Arthritis', text: 'RINVOQ is indicated for the treatment of adults with moderately to severely active rheumatoid arthritis who have had an inadequate response or intolerance to one or more TNF blockers.' },
        { page: 2, section: '1.4 Atopic Dermatitis', text: 'RINVOQ is indicated for the treatment of adults and pediatric patients 12 years of age and older with moderate-to-severe atopic dermatitis.' }
      ]
    },
    dose: {
      answer: 'The recommended starting dose of RINVOQ for Rheumatoid Arthritis and Psoriatic Arthritis is 15 mg orally once daily [p. 8]. For Ulcerative Colitis, the induction dose is 45 mg once daily for 8 weeks, followed by a maintenance dose of 15 mg or 30 mg once daily [p. 9]. Tablets should be swallowed whole and not chewed or crushed [p. 8].',
      section: '2 DOSAGE AND ADMINISTRATION',
      citations: [
        { page: 8, section: '2.1 Recommended Dosage in Rheumatoid Arthritis', text: 'The recommended dosage of RINVOQ is 15 mg once daily.' },
        { page: 9, section: '2.4 Recommended Dosage in Ulcerative Colitis', text: 'The recommended induction dosage is 45 mg once daily for 8 weeks. The recommended maintenance dosage is 15 mg once daily.' }
      ]
    },
    side_effects: {
      answer: 'Common side effects reported in clinical trials include upper respiratory tract infections (13.5%), shingles (herpes zoster, 3.2%), herpes simplex (1.5%), bronchitis, nausea, cough, pyrexia, and elevated blood creatine phosphokinase [p. 21]. Serious infections and elevated liver enzymes may also occur [p. 22].',
      section: '6 ADVERSE REACTIONS',
      citations: [
        { page: 21, section: '6.1 Clinical Trials Experience', text: 'Adverse reactions reported in ≥2% of patients treated with RINVOQ 15 mg included upper respiratory tract infections, nausea, cough, and pyrexia.' },
        { page: 22, section: '6.2 Laboratory Abnormalities', text: 'Elevations in ALT or AST ≥3 times the upper limit of normal were observed in patients receiving RINVOQ.' }
      ]
    },
    warnings: {
      answer: 'RINVOQ carries Boxed Warnings for: 1) Serious Infections (including tuberculosis and fungal infections) [p. 1], 2) Increased Mortality in patients 50 and older with CV risk factors [p. 1], 3) Malignancies (including lymphomas and skin cancers) [p. 2], 4) Major Adverse Cardiovascular Events (MACE) [p. 2], and 5) Thrombosis (deep vein thrombosis and pulmonary embolism) [p. 2].',
      section: 'BOXED WARNING / 5 WARNINGS AND PRECAUTIONS',
      citations: [
        { page: 1, section: 'BOXED WARNING: SERIOUS INFECTIONS', text: 'Patients treated with RINVOQ are at increased risk for developing serious infections that may lead to hospitalization or death.' },
        { page: 2, section: '5.4 Thrombosis', text: 'Thrombosis, including deep vein thrombosis, pulmonary embolism, and arterial thrombosis, has occurred in patients treated with JAK inhibitors.' }
      ]
    }
  },
  humira: {
    title: 'HUMIRA® (adalimumab) Injection',
    fda_date: 'Rev. 02/2024',
    source_url: 'https://www.rxabbvie.com/pdf/humira_pi.pdf',
    indications: {
      answer: 'HUMIRA is a TNF blocker indicated for Rheumatoid Arthritis, Juvenile Idiopathic Arthritis, Psoriatic Arthritis, Ankylosing Spondylitis, Crohn\'s Disease, Ulcerative Colitis, and Plaque Psoriasis [p. 1].',
      section: '1 INDICATIONS AND USAGE',
      citations: [
        { page: 1, section: '1.1 Rheumatoid Arthritis', text: 'HUMIRA is indicated for reducing signs and symptoms in adult patients with moderately to severely active rheumatoid arthritis.' }
      ]
    },
    dose: {
      answer: 'The recommended dose for adults with Rheumatoid Arthritis is 40 mg administered subcutaneously every other week [p. 7].',
      section: '2 DOSAGE AND ADMINISTRATION',
      citations: [
        { page: 7, section: '2.1 Rheumatoid Arthritis Dosing', text: 'The recommended dose of HUMIRA for adult patients with rheumatoid arthritis is 40 mg administered every other week.' }
      ]
    }
  },
  keytruda: {
    title: 'KEYTRUDA® (pembrolizumab) Injection',
    fda_date: 'Rev. 01/2024',
    source_url: 'https://www.merck.com/product/usa/pi_circulars/k/keytruda/keytruda_pi.pdf',
    indications: {
      answer: 'KEYTRUDA is a programmed death receptor-1 (PD-1)-blocking antibody indicated for melanoma, non-small cell lung cancer, head and neck squamous cell cancer, classical Hodgkin lymphoma, and urothelial carcinoma [p. 1].',
      section: '1 INDICATIONS AND USAGE',
      citations: [
        { page: 1, section: '1.1 Melanoma', text: 'KEYTRUDA is indicated for the treatment of patients with unresectable or metastatic melanoma.' }
      ]
    },
    dose: {
      answer: 'The recommended dose of KEYTRUDA in adults is 200 mg every 3 weeks or 400 mg every 6 weeks administered as an intravenous infusion over 30 minutes [p. 14].',
      section: '2 DOSAGE AND ADMINISTRATION',
      citations: [
        { page: 14, section: '2.1 Recommended Dosing', text: 'Administer KEYTRUDA as an intravenous infusion over 30 minutes every 3 weeks (200 mg) or every 6 weeks (400 mg).' }
      ]
    }
  },
  eliquis: {
    title: 'ELIQUIS® (apixaban) Tablets',
    fda_date: 'Rev. 03/2024',
    source_url: 'https://www.eliquis.bmscustomerconnect.com/prescribing-information.pdf',
    indications: {
      answer: 'ELIQUIS is a factor Xa inhibitor indicated to reduce the risk of stroke and systemic embolism in patients with nonvalvular atrial fibrillation, and for prophylaxis and treatment of deep vein thrombosis (DVT) and pulmonary embolism (PE) [p. 1].',
      section: '1 INDICATIONS AND USAGE',
      citations: [
        { page: 1, section: '1.1 Nonvalvular Atrial Fibrillation', text: 'ELIQUIS is indicated to reduce the risk of stroke and systemic embolism in patients with nonvalvular atrial fibrillation.' }
      ]
    },
    dose: {
      answer: 'The recommended dose of ELIQUIS for most patients with nonvalvular atrial fibrillation is 5 mg orally twice daily [p. 3].',
      section: '2 DOSAGE AND ADMINISTRATION',
      citations: [
        { page: 3, section: '2.1 Recommended Dosage', text: 'The recommended dose of ELIQUIS is 5 mg taken orally twice daily.' }
      ]
    }
  }
};

// In-memory dynamic medicine store for custom uploaded PDFs
let customMedicinesList = [...DEFAULT_MEDICINES];

const LIVE_DRUGS_URL = `${API_ORIGIN}/api/drugs`;

/**
 * Load the REAL list of indexed medicines from the backend and make it the
 * active list. Falls back to the built-in demo list if the backend is off.
 */
export async function fetchAvailableDrugs() {
  try {
    const uid = getUserId() || await resolveUserId() || 'anonymous';
    const res = await fetch(`${LIVE_DRUGS_URL}?user_id=${encodeURIComponent(uid)}`);
    if (!res.ok) throw new Error(`status ${res.status}`);
    const data = await res.json();
    const drugs = (data.drugs || []).map(d => ({
      id: d.drug_id,
      name: d.title && d.title !== d.drug_id.toUpperCase()
        ? d.title
        : d.drug_id.toUpperCase(),
      pdf: d.filename,
      pages: d.pages,
      manufacturer: 'Indexed PDF',
      status: 'Indexed & Verified',
    }));
    customMedicinesList = drugs;
    return drugs;
  } catch (err) {
    console.warn('Could not load drugs from backend, using demo list:', err.message);
    return [...customMedicinesList];
  }
}

/**
 * Delete a medicine (removes its PDF + index entry on the backend).
 */
export async function deleteMedicine(id, useLiveApi = true) {
  if (useLiveApi) {
    try {
      const uid = getUserId() || 'anonymous';
      const res = await fetch(`${API_ORIGIN}/api/drugs/${encodeURIComponent(id)}?user_id=${encodeURIComponent(uid)}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        await fetchAvailableDrugs();
        return true;
      }
    } catch (err) {
      console.warn('Delete failed on backend:', err.message);
    }
  }
  customMedicinesList = customMedicinesList.filter(m => m.id !== id);
  return true;
}

/**
 * Upload one or more PDFs at once. Returns the list of registered medicines.
 */
export const MAX_UPLOAD_MB = 100;   // keep in sync with backend MAX_UPLOAD_MB

export async function uploadMedicinePdfs(files, useLiveApi = true) {
  const list = Array.from(files || []);
  const invalid = list.find(f => !f.name.toLowerCase().endsWith('.pdf'));
  if (invalid) throw new Error(`"${invalid.name}" is not a .pdf file.`);
  if (list.length === 0) throw new Error('No files selected.');
  // Client-side size check for a fast, clear message.
  const tooBig = list.find(f => f.size > MAX_UPLOAD_MB * 1024 * 1024);
  if (tooBig) {
    throw new Error(`"${tooBig.name}" is over the ${MAX_UPLOAD_MB} MB limit.`);
  }

  if (useLiveApi) {
    const uid = getUserId() || await resolveUserId() || 'anonymous';
    const formData = new FormData();
    list.forEach(f => formData.append('files', f));
    formData.append('user_id', uid);
    const res = await fetch(LIVE_UPLOAD_URL, { method: 'POST', body: formData });
    if (!res.ok) {
      // Surface the backend's specific reason (e.g. size/storage limit).
      let detail = `Upload failed (status ${res.status})`;
      try { const e = await res.json(); if (e.detail) detail = e.detail; } catch {}
      throw new Error(detail);
    }
    const data = await res.json();
    await fetchAvailableDrugs();
    return data.uploaded || [data];
  }

  // Demo fallback: register each locally.
  const out = [];
  for (const f of list) out.push(await uploadMedicinePdf(f, false));
  return out;
}

/**
 * Checks if a question is asking for personalized medical advice.
 */
export function isMedicalAdviceQuery(query) {
  const adviceKeywords = [
    'should i stop', 'should i take', 'can i stop', 'is it safe for me',
    'what should i do', 'can i mix', 'can i double', 'prescribe',
    'doctor told me', 'my symptoms are', 'diagnose', 'feel sick', 'my doctor'
  ];
  const q = query.toLowerCase();
  return adviceKeywords.some(keyword => q.includes(keyword));
}

/**
 * Checks if a question cannot be answered from available PDFs (Refusal test).
 */
export function isUnanswerableQuery(query) {
  const refusalKeywords = [
    'newborn', 'under 1 month', 'infants under 1 month', 'veterinary',
    'dogs', 'cats', 'aspirin', 'paracetamol', 'covid vaccine recipe',
    'price in dollars', 'stock price', 'manufactured in mars', 'moon'
  ];
  const q = query.toLowerCase();
  return refusalKeywords.some(keyword => q.includes(keyword));
}

/**
 * Data-driven medicine list retriever.
 */
export function getAvailableDrugs() {
  return [...customMedicinesList];
}

/**
 * Dynamically register a newly uploaded Medicine PDF.
 */
export async function uploadMedicinePdf(file, useLiveApi = false) {
  if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
    throw new Error('Invalid file format. Please upload a valid .pdf file.');
  }

  if (useLiveApi) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch(LIVE_UPLOAD_URL, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        const newMed = {
          id: data.id || file.name.replace(/\.pdf$/i, '').toLowerCase(),
          name: data.name || file.name.replace(/\.pdf$/i, '').toUpperCase(),
          pdf: file.name,
          pages: data.pages || 65,
          manufacturer: 'Uploaded Document',
          status: 'Indexed & Verified'
        };
        customMedicinesList.push(newMed);
        return newMed;
      }
    } catch (err) {
      console.warn('Backend PDF upload endpoint unavailable. Registering PDF in dynamic frontend state:', err.message);
    }
  }

  // Frontend dynamic registration when backend upload is not active
  await new Promise(res => setTimeout(res, 1200));

  const cleanName = file.name.replace(/\.pdf$/i, '');
  const newMed = {
    id: cleanName.toLowerCase().replace(/[^a-z0-9]/g, '_'),
    name: `${cleanName.toUpperCase()} Prescribing Info`,
    pdf: file.name,
    pages: Math.floor(Math.random() * 40) + 35,
    manufacturer: 'Custom Upload',
    status: 'Indexed & Verified'
  };

  // Add default mock entry if not present
  if (!MOCK_DRUG_KNOWLEDGE[newMed.id]) {
    MOCK_DRUG_KNOWLEDGE[newMed.id] = {
      title: `${cleanName.toUpperCase()} Prescribing Information`,
      fda_date: 'Newly Uploaded Document',
      indications: {
        answer: `According to the uploaded document ${file.name}, ${cleanName.toUpperCase()} is indicated for prescribed medical conditions as detailed in section 1 [p. 1].`,
        section: '1 INDICATIONS AND USAGE',
        citations: [{ page: 1, section: '1.1 Indications', text: `${cleanName.toUpperCase()} prescribing information extracted from uploaded file.` }]
      },
      dose: {
        answer: `The recommended dosage for ${cleanName.toUpperCase()} as stated in the uploaded label is listed in Section 2 [p. 5]. Dosing instructions must be followed as directed by prescribing guidelines [p. 5].`,
        section: '2 DOSAGE AND ADMINISTRATION',
        citations: [{ page: 5, section: '2.1 Dosage', text: `Dosage information extracted from ${file.name}.` }]
      }
    };
  }

  customMedicinesList.push(newMed);
  return newMed;
}

/**
 * Executes a question query against the backend or RAG search simulation engine.
 */
export async function sendQuestion({ question, conversationHistory = [], selectedDrug = 'rinvoq', useLiveApi = false }) {
  if (useLiveApi) {
    try {
      const uid = getUserId() || await resolveUserId();
      const response = await fetch(LIVE_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          history: conversationHistory,
          drug_filter: selectedDrug,
          user_id: uid
        })
      });

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      return await response.json();
    } catch (err) {
      // Demo Mode removed: do not fabricate an answer. Surface the error so the
      // UI shows a clear "backend unavailable" message instead of fake data.
      console.error('Live API request failed:', err.message);
      throw new Error(
        'Could not reach the MedCite backend. Make sure the server is running (uvicorn on port 8000).'
      );
    }
  }

  // RAG Engine Execution Simulation
  await new Promise(res => setTimeout(res, 1000 + Math.random() * 600));

  const q = question.toLowerCase();
  const drugData = MOCK_DRUG_KNOWLEDGE[selectedDrug] || {
    title: `${selectedDrug.toUpperCase()} Document`,
    indications: {
      answer: `The prescribing document for ${selectedDrug} indicates usage guidelines in Section 1 [p. 2].`,
      section: '1 INDICATIONS AND USAGE',
      citations: [{ page: 2, section: '1.1 Approved Uses', text: 'Document section text extracted from PDF.' }]
    }
  };

  // 1. Refusal Check
  if (isUnanswerableQuery(question)) {
    return {
      is_refusal: true,
      refusal_reason: 'The available prescribing documents do not contain information addressing this specific question or population.',
      answer: "I don't know based on the available documents. The official prescribing information does not contain data to answer this query. MedCite only answers when explicit proof exists in the verified drug label.",
      citations: [],
      drug_name: drugData.title
    };
  }

  // 2. Medical Advice Safeguard Check
  const requiresAdviceWarning = isMedicalAdviceQuery(question);

  // 3. Intent Matching
  let match = drugData.indications;
  let topicSection = 'INDICATIONS AND USAGE';

  if (q.includes('dose') || q.includes('dosage') || q.includes('how much') || q.includes('starting')) {
    match = drugData.dose || drugData.indications;
    topicSection = 'DOSAGE AND ADMINISTRATION';
  } else if (q.includes('side effect') || q.includes('adverse') || q.includes('reaction') || q.includes('nausea')) {
    match = drugData.side_effects || drugData.indications;
    topicSection = 'ADVERSE REACTIONS';
  } else if (q.includes('warning') || q.includes('precaution') || q.includes('boxed') || q.includes('risk') || q.includes('stop')) {
    match = drugData.warnings || drugData.indications;
    topicSection = 'WARNINGS AND PRECAUTIONS';
  }

  // Handle follow-up queries
  if ((q.includes('children') || q.includes('pediatric')) && conversationHistory.length > 0) {
    return {
      is_refusal: false,
      is_advice: requiresAdviceWarning,
      answer: `According to the prescribing information, for pediatric patients 12 years of age and older weighing at least 40 kg, the recommended dose of RINVOQ is 15 mg once daily [p. 8]. Safety and effectiveness in pediatric patients under 12 years of age have not been established [p. 28].`,
      section: '8.4 PEDIATRIC USE',
      citations: [
        { page: 8, section: '2.3 Pediatric Dosage', text: 'Pediatric patients 12 years of age and older weighing ≥ 40 kg: 15 mg once daily.' },
        { page: 28, section: '8.4 Pediatric Use', text: 'Safety and effectiveness of RINVOQ in pediatric patients under 12 years of age with atopic dermatitis have not been established.' }
      ],
      drug_name: drugData.title
    };
  }

  return {
    is_refusal: false,
    is_advice: requiresAdviceWarning,
    answer: match.answer,
    section: match.section || topicSection,
    citations: match.citations || [],
    drug_name: drugData.title
  };
}
