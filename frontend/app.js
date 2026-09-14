// ================= AUTH GUARD & SESSION CHECK =================
(function enforceAuthGuard() {
  const token = localStorage.getItem('access_token');
  if (!token || token === 'session_active' || token.startsWith('mock_')) {
    localStorage.clear();
    window.location.replace('login.html');
  }
})();

function logoutUser() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user_email');
  localStorage.removeItem('user_name');
  localStorage.removeItem('user_role');
  localStorage.removeItem('legaldrishti_cases');
  window.location.replace('login.html');
}

// ================= STATE & DEFAULTS =================
let activeNav = 'chat';
let activeSessionId = null;
let userChatSessions = [];
let deepSearchActive = false;
let credits = 3;

// Document vaults data (synced with PostgreSQL backend)
const defaultCases = [];
let casesData = [];
try {
  const cached = localStorage.getItem('legaldrishti_cases');
  if (cached) casesData = JSON.parse(cached);
} catch (e) {}

let activeCaseId = null;
let activeCaseTitle = '';

function saveCasesToStorage() {
  localStorage.setItem('legaldrishti_cases', JSON.stringify(casesData));
}

// Default recent chats
const defaultRecentChats = [
  { query: "Section 138 Negotiable Instruments Act vicarious liability of non-executive independent director who resigned before cheque issuance", title: "Section 138 NI Act – Key Precedents", time: "2 hours ago" },
  { query: "What are the essential requirements and limitation period for statutory notice under Section 138 NI Act?", title: "Requirements for Notice under 138", time: "4 hours ago" },
  { query: "Grounds for Anticipatory Bail under Section 482 of Bharatiya Nagarik Suraksha Sanhita, 2023", title: "Bail under BNSS 482", time: "6 hours ago" },
  { query: "Limitation period for filing complaint under Section 138 after 15 days notice expire", title: "Limitation for complaint", time: "1 day ago" },
  { query: "Statutory presumption of legally enforceable debt under Section 139 Negotiable Instruments Act", title: "Interpretation of NI Act", time: "1 day ago" }
];

let parsedChats = null;
try {
  parsedChats = JSON.parse(localStorage.getItem('legaldrishti_recent_chats'));
} catch (e) {
  parsedChats = null;
}
let recentChats = (Array.isArray(parsedChats) && parsedChats.length > 0) ? parsedChats : defaultRecentChats;

function saveRecentChats() {
  localStorage.setItem('legaldrishti_recent_chats', JSON.stringify(recentChats));
}

// ================= DOM ELEMENTS =================
const btnNewConsultation = document.getElementById('btn-new-consultation');
const heroView = document.getElementById('hero-view');
const messagesStream = document.getElementById('messages-stream');
const casesView = document.getElementById('cases-view');
const capsuleWrapper = document.getElementById('capsule-wrapper');

const queryInput = document.getElementById('query-input');
const sendBtn = document.getElementById('send-btn');
const modeToggleBtn = document.getElementById('mode-toggle-btn');
const modeLabel = document.getElementById('mode-label');
const themeToggleBtn = document.getElementById('theme-toggle-btn');

// Cases Workspace Elements
const casesCardsStack = document.getElementById('cases-cards-stack');
const casesSearchInput = document.getElementById('cases-search-input');
const openCreateCaseModalBtn = document.getElementById('open-create-case-modal-btn');
const newCaseModal = document.getElementById('new-case-modal');
const closeCaseModalBtn = document.getElementById('close-case-modal-btn');
const cancelCaseModalBtn = document.getElementById('cancel-case-modal-btn');
const submitCreateCaseBtn = document.getElementById('submit-create-case-btn');

const caseFileUploadInput = document.getElementById('case-file-upload-input');
const caseDropzone = document.getElementById('case-dropzone');
const btnResearchThisCase = document.getElementById('btn-research-this-case');
const quickAttachFile = document.getElementById('quick-attach-file');

// Helper: Auth Headers
function getAuthHeaders(isJson = true) {
  const headers = {};
  if (isJson) headers['Content-Type'] = 'application/json';
  const token = localStorage.getItem('access_token');
  if (token && token !== 'session_active' && !token.startsWith('mock_')) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// ================= NAVIGATION =================
const navButtons = document.querySelectorAll('.nav-item');
navButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    const view = btn.getAttribute('data-view');
    switchView(view);
  });
});

// Primary Action: + New Consultation
if (btnNewConsultation) {
  btnNewConsultation.addEventListener('click', () => {
    startNewConsultation();
  });
}

function startNewConsultation() {
  activeSessionId = null;
  switchView('chat');
  if (messagesStream) {
    messagesStream.innerHTML = '';
    messagesStream.style.display = 'none';
  }
  if (heroView) {
    heroView.style.display = 'flex';
  }
  const allItems = document.querySelectorAll('.recent-item');
  allItems.forEach(el => el.classList.remove('active'));
  if (queryInput) {
    queryInput.value = '';
    queryInput.style.height = 'auto';
    queryInput.focus();
  }
}

function switchView(view) {
  activeNav = view;

  // Sync sidebar active state
  navButtons.forEach(btn => {
    if (btn.getAttribute('data-view') === view) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Hide all views
  if (heroView) heroView.style.display = 'none';
  if (messagesStream) messagesStream.style.display = 'none';
  if (casesView) casesView.style.display = 'none';
  const settingsView = document.getElementById('settings-view');
  if (settingsView) settingsView.style.display = 'none';
  if (capsuleWrapper) capsuleWrapper.style.display = 'flex';

  if (view === 'chat') {
    if (!activeSessionId && (!messagesStream || messagesStream.children.length === 0)) {
      if (heroView) heroView.style.display = 'flex';
    } else {
      if (messagesStream) messagesStream.style.display = 'flex';
    }
    if (queryInput) queryInput.focus();
  } else if (view === 'cases') {
    if (casesView) casesView.style.display = 'block';
    if (capsuleWrapper) capsuleWrapper.style.display = 'none';
    renderUserVaults();
    loadUserVaults();
    renderLegalCorpus();
  } else if (view === 'settings') {
    if (settingsView) settingsView.style.display = 'block';
    if (capsuleWrapper) capsuleWrapper.style.display = 'none';
    if (typeof window.loadSettingsData === 'function') {
      window.loadSettingsData();
    }
  }
}

// ================= DEEP SEARCH TOGGLE =================
if (modeToggleBtn) {
  modeToggleBtn.addEventListener('click', () => {
    deepSearchActive = !deepSearchActive;
    if (deepSearchActive) {
      modeToggleBtn.classList.add('active');
      if (modeLabel) modeLabel.textContent = "Deep Search ON";
    } else {
      modeToggleBtn.classList.remove('active');
      if (modeLabel) modeLabel.textContent = "Deep Search";
    }
  });
}

// ================= CHAT & RESEARCH =================
async function handleSend() {
  const text = queryInput ? queryInput.value.trim() : '';
  if (!text) return;

  // Switch to chat view if not already
  if (activeNav !== 'chat') {
    switchView('chat');
  }

  // Ensure messages stream is visible
  if (heroView) heroView.style.display = 'none';
  if (messagesStream) messagesStream.style.display = 'flex';

  // Store attached doc reference if any
  const attachedFileToUpload = activeSessionDoc;
  activeSessionDoc = null;
  if (sessionDocPill) sessionDocPill.style.display = 'none';
  if (quickAttachFile) quickAttachFile.value = '';

  // Append user message with attachment badge if present
  appendMessage('user', text, [], attachedFileToUpload ? attachedFileToUpload.name : null);
  if (queryInput) {
    queryInput.value = '';
    queryInput.style.height = 'auto';
  }
  if (sendBtn) sendBtn.disabled = true;

  // Append loading indicator
  const loadingEl = document.createElement('div');
  loadingEl.className = 'loading-indicator';
  loadingEl.innerHTML = `
    <svg class="spin-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
    </svg>
    <span>${deepSearchActive ? 'Researching precedents...' : 'Generating response...'}</span>
  `;
  messagesStream.appendChild(loadingEl);
  messagesStream.scrollTop = messagesStream.scrollHeight;

  try {
    // 1. Ensure an active session exists in backend
    if (!activeSessionId) {
      try {
        const titleText = text.length > 38 ? text.slice(0, 38) + '...' : text;
        const sessionRes = await fetch('/api/v1/chat/sessions', {
          method: 'POST',
          headers: getAuthHeaders(true),
          body: JSON.stringify({
            title: titleText,
            case_id: activeCaseId ? parseInt(activeCaseId) : null
          })
        });
        if (sessionRes.status === 401) {
          alert("⚠️ Your session has expired. Please sign in again.");
          logoutUser();
          return;
        }
        if (sessionRes.ok) {
          const newSession = await sessionRes.json();
          activeSessionId = newSession.id;
          loadUserChatSessions();
        }
      } catch (sessErr) {
        console.warn("Session creation fallback:", sessErr);
      }
    }

    // If a document was attached with this prompt, upload it to this session
    if (attachedFileToUpload && activeSessionId) {
      try {
        const uploadForm = new FormData();
        uploadForm.append('file', attachedFileToUpload);
        await fetch(`/api/v1/chat/sessions/${activeSessionId}/upload`, {
          method: 'POST',
          headers: getAuthHeaders(false),
          body: uploadForm
        });
        console.log("Attached document uploaded to session:", attachedFileToUpload.name);
      } catch (upErr) {
        console.warn("Session doc upload error:", upErr);
      }
    }

    // 2. Dispatch message to chat endpoint if session exists
    let responseHandled = false;
    if (activeSessionId) {
      const msgRes = await fetch(`/api/v1/chat/sessions/${activeSessionId}/messages`, {
        method: 'POST',
        headers: getAuthHeaders(true),
        body: JSON.stringify({
          content: text,
          mode: deepSearchActive ? 'deep_search' : 'dual_stream'
        })
      });

      if (loadingEl.parentNode) loadingEl.remove();

      if (msgRes.status === 401) {
        alert("⚠️ Your session has expired. Please sign in again.");
        logoutUser();
        return;
      }

      if (msgRes.ok) {
        const data = await msgRes.json();
        const asst = data.assistant_message || data;
        let sources = [];
        if (Array.isArray(asst.sources)) {
          sources = asst.sources.map(s => {
            if (typeof s === 'string') return s;
            if (s.case_title) return `🏛️ ${s.case_title} [${s.citation || ''}] — ${s.court || ''}`;
            if (s.document_title) return `📖 ${s.document_title}${s.page_number ? `, Page ${s.page_number}` : ''}`;
            return JSON.stringify(s);
          });
        }
        appendMessage('ai', asst.content || asst.answer || '', sources);
        responseHandled = true;

        if (deepSearchActive) {
          deepSearchActive = false;
          if (modeToggleBtn) modeToggleBtn.classList.remove('active');
          if (modeLabel) modeLabel.textContent = "Deep Search";
        }

        // Refresh sidebar sessions to reflect updated title and order
        loadUserChatSessions();
      } else {
        const err = await msgRes.json().catch(() => ({}));
        appendMessage('ai', `⚠️ Notice: ${err.detail || 'Server could not process inquiry at this moment.'}`);
        responseHandled = true;
      }
    }

    // Fallback if session wasn't available
    if (!responseHandled) {
      let endpoint = `/api/v1/cases/${activeCaseId}/qa`;
      let payload = { query: text };

      if (deepSearchActive) {
        endpoint = '/api/v1/research/precedents';
        payload = { query: text, max_precedents: 3 };
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: getAuthHeaders(true),
        body: JSON.stringify(payload),
      });

      if (loadingEl.parentNode) loadingEl.remove();

      if (res.status === 401) {
        alert("⚠️ Your session has expired. Please sign in again.");
        logoutUser();
        return;
      }

      if (res.ok) {
        const data = await res.json();
        if (deepSearchActive) {
          let content = `**LEGAL RESEARCH & STRATEGY**\n${data.legal_analysis_and_strategy || data.answer || ''}\n\n`;
          const sources = (data.precedents || []).map(p => `🏛️ ${p.case_title} [${p.citation}] — ${p.court} (${p.year})`);
          appendMessage('ai', content, sources);

          deepSearchActive = false;
          if (modeToggleBtn) modeToggleBtn.classList.remove('active');
          if (modeLabel) modeLabel.textContent = "Deep Search";
        } else {
          const sources = (data.sources || []).map(s => `📖 ${s.document_title}, Page ${s.page_number}`);
          appendMessage('ai', data.answer, sources);
        }

        // Refresh sidebar sessions to reflect latest updated_at timestamp & order
        loadUserChatSessions();
      } else {
        const err = await res.json().catch(() => ({}));
        appendMessage('ai', `⚠️ Notice: ${err.detail || 'Server could not process inquiry at this moment.'}`);
      }
    }
  } catch (err) {
    if (loadingEl.parentNode) loadingEl.remove();
    appendMessage('ai', '⚠️ Connection Notice: Backend is currently processing or offline. Please ensure the FastAPI server is running.');
  } finally {
    if (sendBtn) sendBtn.disabled = false;
  }
}

// Configure Marked.js for GitHub Flavored Markdown (GFM) and line breaks
if (typeof marked !== 'undefined' && typeof marked.setOptions === 'function') {
  marked.setOptions({
    gfm: true,
    breaks: true
  });
}

function renderAssistantMessage(rawMarkdownText, containerElement) {
  if (!rawMarkdownText) return '';
  let parsedHtml = '';

  if (typeof marked !== 'undefined') {
    const parseFn = typeof marked.parse === 'function' ? marked.parse : marked;
    try {
      parsedHtml = parseFn(rawMarkdownText, { gfm: true, breaks: true });
    } catch (e) {
      console.warn("Marked parse error:", e);
      parsedHtml = renderMarkdownFallback(rawMarkdownText);
    }
  } else {
    parsedHtml = renderMarkdownFallback(rawMarkdownText);
  }

  const cleanHtml = (typeof DOMPurify !== 'undefined' && typeof DOMPurify.sanitize === 'function')
    ? DOMPurify.sanitize(parsedHtml)
    : parsedHtml;

  if (containerElement) {
    containerElement.innerHTML = cleanHtml;
  }
  return cleanHtml;
}

function renderMarkdownFallback(rawText) {
  if (!rawText) return '';

  let html = rawText
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Markdown Tables
  const lines = html.split('\n');
  let inTable = false;
  let tableHtml = '';
  let processedLines = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.startsWith('|') && line.endsWith('|')) {
      if (!inTable) {
        inTable = true;
        tableHtml = '<div class="table-responsive"><table><tbody>';
      }
      if (line.includes('---')) continue;
      const cells = line.split('|').filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
      const isHeader = (tableHtml.indexOf('<tr>') === -1);
      const tag = isHeader ? 'th' : 'td';
      tableHtml += '<tr>' + cells.map(c => `<${tag}>${c.trim()}</${tag}>`).join('') + '</tr>';
    } else {
      if (inTable) {
        inTable = false;
        tableHtml += '</tbody></table></div>';
        processedLines.push(tableHtml);
      }
      processedLines.push(line);
    }
  }
  if (inTable) {
    tableHtml += '</tbody></table></div>';
    processedLines.push(tableHtml);
  }
  html = processedLines.join('\n');

  // Dividers
  html = html.replace(/^---$/gim, '<hr/>');

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  // Bold & Italic
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

  // Lists
  html = html.replace(/^\s*-\s+(.*$)/gim, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/gms, '<ul>$1</ul>');

  // Paragraphs
  html = html.replace(/\n\n/g, '<p></p>');

  return html;
}

function appendMessage(sender, text, sources = [], attachedFileName = null) {
  if (!messagesStream) return;
  const msgEl = document.createElement('div');
  msgEl.className = `message-bubble ${sender}`;

  let sourcesHtml = '';
  if (sources && sources.length > 0) {
    const resourceCount = sources.length;
    sourcesHtml = `
      <div class="resources-wrapper">
        <div class="resources-header">
          <span class="resources-label">Resources :</span>
          <button class="btn-toggle-resources" type="button" aria-expanded="false" title="Click to view all resources">
            <svg class="chevron-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
            <span class="btn-toggle-text">View Resources (${resourceCount})</span>
          </button>
        </div>
        <div class="resources-list" style="display: none;">
          ${sources.map(s => `<span class="source-tag">${escapeHtml(s)}</span>`).join('')}
        </div>
      </div>
    `;
  }

  const attachmentHtml = attachedFileName ? `
    <div class="user-attached-file-badge">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
      <span>Attached: ${escapeHtml(attachedFileName)}</span>
    </div>
  ` : '';

  const contentHtml = (sender === 'ai') 
    ? `<div class="markdown-body">${renderAssistantMessage(text)}</div>` 
    : `${attachmentHtml}<div style="white-space: pre-wrap;">${escapeHtml(text)}</div>`;

  msgEl.innerHTML = `
    <div class="bubble-content">
      ${contentHtml}
      ${sourcesHtml}
    </div>
  `;

  // Attach toggle listener for the collapsible resources button
  const toggleBtn = msgEl.querySelector('.btn-toggle-resources');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const listEl = msgEl.querySelector('.resources-list');
      const textSpan = toggleBtn.querySelector('.btn-toggle-text');
      if (listEl) {
        const isHidden = (listEl.style.display === 'none' || !listEl.style.display);
        if (isHidden) {
          listEl.style.display = 'flex';
          toggleBtn.setAttribute('aria-expanded', 'true');
          toggleBtn.classList.add('expanded');
          if (textSpan) textSpan.textContent = 'Hide Resources';
        } else {
          listEl.style.display = 'none';
          toggleBtn.setAttribute('aria-expanded', 'false');
          toggleBtn.classList.remove('expanded');
          if (textSpan) textSpan.textContent = `View Resources (${sources.length})`;
        }
      }
    });
  }

  messagesStream.appendChild(msgEl);
  messagesStream.scrollTop = messagesStream.scrollHeight;
}

if (sendBtn) sendBtn.addEventListener('click', handleSend);
if (queryInput) {
  queryInput.addEventListener('keydown', (e) => {
    // Enter sends message; Shift + Enter creates a new line (2nd line, 3rd line like ChatGPT / Antigravity)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  // Auto-resize textarea to fit multiline content dynamically
  queryInput.addEventListener('input', () => {
    queryInput.style.height = 'auto';
    const newHeight = Math.min(queryInput.scrollHeight, 160);
    queryInput.style.height = newHeight + 'px';
  });
}

// ================= 3-TIER DOCUMENT VAULTS & LEGAL CORPUS =================

// 28 Indian Statutes & Bare Acts foundational corpus
const legalStatutesData = [
  {
    name: "Bharatiya Nyaya Sanhita, 2023 (BNS)",
    file: "Bharatiya Nyaya Sanhita, 2023.pdf",
    category: "criminal",
    categoryLabel: "Criminal Law",
    summary: "Substantive penal code of India replacing the Indian Penal Code, 1860. Defines offenses, penalties, corporate liability, and general exceptions."
  },
  {
    name: "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
    file: "THE BHARATIYA NAGARIK SURAKSHA SANHITA, 2023.pdf",
    category: "criminal",
    categoryLabel: "Criminal Procedure",
    summary: "Governs criminal procedure, investigation, arrest, regular & anticipatory bail, trial proceedings, and High Court inherent powers."
  },
  {
    name: "Bharatiya Sakshya Adhiniyam, 2023 (BSA)",
    file: "THE BHARATIYA SAKSHYA ADHINIYAM,2023.pdf",
    category: "criminal",
    categoryLabel: "Law of Evidence",
    summary: "Modernized evidence law covering electronic & digital records, primary vs secondary evidence, burden of proof, and witness testimony."
  },
  {
    name: "The Negotiable Instruments Act, 1881",
    file: "The Negotiable Instruments Act, 1881.PDF",
    category: "commercial",
    categoryLabel: "Banking & Commercial",
    summary: "Governs promissory notes, bills of exchange, cheques, statutory notices, and criminal liability for cheque bounce under Section 138."
  },
  {
    name: "The Constitution of India",
    file: "THE CONSTITUTION OF INDIA.pdf",
    category: "constitutional",
    categoryLabel: "Constitutional Law",
    summary: "Supreme law of India establishing fundamental rights, directive principles, judiciary structures, and constitutional writs."
  },
  {
    name: "Constitutional Law Principles",
    file: "CONSTITUTIONAL LAW.pdf",
    category: "constitutional",
    categoryLabel: "Constitutional Law",
    summary: "Doctrines of constitutional interpretation, landmark Supreme Court rulings, federalism, and basic structure doctrine."
  },
  {
    name: "Constitutional Law - Fundamental Freedoms",
    file: "Constitutional Law - I.pdf",
    category: "constitutional",
    categoryLabel: "Constitutional Law",
    summary: "Comprehensive jurisprudence on Articles 14, 19, and 21, rule of law, reasonable restrictions, and personal liberty."
  },
  {
    name: "Code of Civil Procedure & Limitation Act",
    file: "Code of Civil Procedure & Limitation Act.pdf",
    category: "civil",
    categoryLabel: "Civil Procedure",
    summary: "Adjudication of civil suits, jurisdiction, pleadings, interim injunctions, decree executions, and statutory periods of limitation."
  },
  {
    name: "The Companies Act, 2013",
    file: "THE COMPANIES ACT, 2013.pdf",
    category: "commercial",
    categoryLabel: "Corporate Law",
    summary: "Incorporation, corporate governance, director fiduciary duties, share capital, NCLT jurisdiction, and corporate resolution."
  },
  {
    name: "The Consumer Protection Act, 2019",
    file: "THE CONSUMER PROTECTION ACT, 2019.pdf",
    category: "commercial",
    categoryLabel: "Consumer Rights",
    summary: "Statutory rights of consumers, e-commerce regulations, product liability claims, and dispute adjudication across commissions."
  },
  {
    name: "The Information Technology Act, 2000",
    file: "THE INFORMATION TECHNOLOGY ACT, 2000.pdf",
    category: "special",
    categoryLabel: "Cyber & Tech Law",
    summary: "Legal framework for electronic commerce, digital signatures, data privacy, cyber offenses, and intermediary liability."
  },
  {
    name: "Right to Information Act, 2005",
    file: "Right to Information Act, 2005.pdf",
    category: "special",
    categoryLabel: "Administrative Law",
    summary: "Guarantees citizen access to public authority records, proactive disclosure obligations, exemption grounds, and appeals."
  },
  {
    name: "The Motor Vehicles Act, 1988",
    file: "THE MOTOR VEHICLES ACT, 1988.pdf",
    category: "special",
    categoryLabel: "Transport & Insurance",
    summary: "Road safety standards, third-party mandatory vehicular insurance, and Motor Accident Claims Tribunal (MACT) compensation principles."
  },
  {
    name: "Transfer of Property Act & Property Law",
    file: "Property Law.pdf",
    category: "civil",
    categoryLabel: "Property Law",
    summary: "Sale, mortgage, lease, exchange, and gifts of immovable property, including doctrine of lis pendens and equity rules."
  },
  {
    name: "Special Contracts & Commercial Engagements",
    file: "Special Contracts.pdf",
    category: "commercial",
    categoryLabel: "Contract Law",
    summary: "Indemnity, guarantee, bailment, pledge, commercial agency, partnership rights, and sale of goods provisions."
  },
  {
    name: "Family Law & Matrimonial Statutes",
    file: "Family Law – I.pdf",
    category: "civil",
    categoryLabel: "Family Law",
    summary: "Marriage laws, judicial separation, divorce, permanent alimony, maintenance, and child custody rights in Indian civil law."
  },
  {
    name: "Labour & Industrial Relations Law",
    file: "Labour Law.pdf",
    category: "civil",
    categoryLabel: "Labour & Employment",
    summary: "Industrial disputes, trade union rights, lay-offs, retrenchment, workman compensation, and fair employment conditions."
  },
  {
    name: "Intellectual Property Rights Law",
    file: "Intellectual Property Rights Law- I.pdf",
    category: "commercial",
    categoryLabel: "Intellectual Property",
    summary: "Patentability criteria, trademark registration and infringement, copyright protections, and passing-off equitable remedies."
  },
  {
    name: "Administrative Law & Judicial Review",
    file: "Administrative Law.pdf",
    category: "special",
    categoryLabel: "Public Law",
    summary: "Principles of natural justice, audi alteram partem, rule against bias, legitimate expectation, and judicial control of power."
  },
  {
    name: "Substantive Law of Crimes - Advanced",
    file: "Law of Crimes-III.pdf",
    category: "criminal",
    categoryLabel: "Criminal Jurisprudence",
    summary: "Advanced criminal doctrines including joint liability, conspiracy, corporate criminality, and special statutory offenses."
  },
  {
    name: "Legislative Drafting & Statutory Interpretation",
    file: "Legislative Drafting.pdf",
    category: "special",
    categoryLabel: "Legal Interpretation",
    summary: "Statutory construction, canons of interpretation, literal/purposive approaches, external aids, and legislative design."
  },
  {
    name: "Media Law, Free Expression & Censorship",
    file: "MEDIA LAW AND CENSORSHIP.pdf",
    category: "special",
    categoryLabel: "Media & Press",
    summary: "Free speech boundaries, criminal & civil defamation, contempt of court, broadcast regulations, and cinematograph laws."
  },
  {
    name: "Private International Law (Conflict of Laws)",
    file: "Private International Law.pdf",
    category: "special",
    categoryLabel: "Cross-Border Law",
    summary: "Cross-border litigation, jurisdiction, choice of applicable law, and foreign judgment recognition in Indian courts."
  },
  {
    name: "Public International Law & Sovereign Relations",
    file: "Public International Law.pdf",
    category: "special",
    categoryLabel: "International Law",
    summary: "Sovereign rights, state succession, diplomatic immunities, treaties under Vienna Convention, and law of the sea."
  },
  {
    name: "International Institutions & Multi-Lateral Treaties",
    file: "International Institutions.pdf",
    category: "special",
    categoryLabel: "International Bodies",
    summary: "United Nations Charter, ICJ judicial determinations, multilateral trade accords, and international arbitration tribunals."
  },
  {
    name: "Humanitarian Law & Refugee Conventions",
    file: "HUMANITARIAN LAW AND REFUGEE LAW.pdf",
    category: "special",
    categoryLabel: "Humanitarian Law",
    summary: "Geneva Conventions, international human rights treaties, protection of civilians, and non-refoulement doctrines."
  },
  {
    name: "Jurisprudence & Legal Theory",
    file: "JURISPRUDENCE-I (Legal Method).pdf",
    category: "special",
    categoryLabel: "Legal Theory",
    summary: "Philosophical foundations of law, positivism, natural law, realism, legal reasoning, and doctrine of judicial precedents."
  },
  {
    name: "Moot Court, Pleadings & Trial Practice",
    file: "THE MOOT COURT, MOCK TRIAL AND INTERNSHIP.pdf",
    category: "special",
    categoryLabel: "Trial Advocacy",
    summary: "Trial preparation, examination of witnesses, oral argument strategy, and courtroom drafting standards."
  }
];

// Active Session Document state (Temporary file for current consultation only)
let activeSessionDoc = null;
let activeDetailVaultId = null;

// Segmented Tab Switcher Logic
const tabBtnUserVaults = document.getElementById('tab-btn-user-vaults');
const tabBtnLegalCorpus = document.getElementById('tab-btn-legal-corpus');
const paneUserVaults = document.getElementById('pane-user-vaults');
const paneLegalCorpus = document.getElementById('pane-legal-corpus');

function switchVaultTab(tab) {
  if (tab === 'user-vaults') {
    if (tabBtnUserVaults) tabBtnUserVaults.classList.add('active');
    if (tabBtnLegalCorpus) tabBtnLegalCorpus.classList.remove('active');
    if (paneUserVaults) paneUserVaults.style.display = 'block';
    if (paneLegalCorpus) paneLegalCorpus.style.display = 'none';
    renderUserVaults();
  } else {
    if (tabBtnLegalCorpus) tabBtnLegalCorpus.classList.add('active');
    if (tabBtnUserVaults) tabBtnUserVaults.classList.remove('active');
    if (paneLegalCorpus) paneLegalCorpus.style.display = 'block';
    if (paneUserVaults) paneUserVaults.style.display = 'none';
    renderLegalCorpus();
  }
}

if (tabBtnUserVaults) tabBtnUserVaults.addEventListener('click', () => switchVaultTab('user-vaults'));
if (tabBtnLegalCorpus) tabBtnLegalCorpus.addEventListener('click', () => switchVaultTab('legal-corpus'));

// Load User Vaults & their permanent documents from PostgreSQL backend
async function loadUserVaults() {
  try {
    const res = await fetch('/api/v1/cases?page_size=100', {
      headers: getAuthHeaders(true)
    });
    if (res.status === 401) {
      logoutUser();
      return;
    }
    if (res.ok) {
      const data = await res.json();
      casesData = (data.items || []).map(item => ({
        id: item.id,
        title: item.title,
        desc: item.description || '',
        client: item.client_name || 'Personal Vault',
        opponent: item.opponent_name || '--',
        court: item.court_name || 'Isolated Vault',
        type: item.case_type || 'Document Vault',
        caseNum: item.case_number || `VLT/${String(item.id).padStart(4, '0')}`,
        status: item.status || 'Active',
        docs: (item.docs || []).map(d => ({
          id: d.id,
          backendId: d.backendId || d.id,
          name: d.name,
          type: d.type || 'Document',
          submitted: true,
          status: 'Submitted',
        }))
      }));
      saveCasesToStorage();
      renderUserVaults();
    }
  } catch (err) {
    console.warn("Could not load backend vaults:", err);
    renderUserVaults();
  }
}

// Render User's Permanent Vaults
function renderUserVaults(searchFilter = '') {
  const grid = document.getElementById('user-vaults-grid');
  const badge = document.getElementById('user-vaults-badge');
  if (badge) badge.textContent = casesData.length;
  if (!grid) return;

  grid.innerHTML = '';

  const filtered = casesData.filter(v =>
    (v.title || '').toLowerCase().includes(searchFilter.toLowerCase()) ||
    (v.desc || '').toLowerCase().includes(searchFilter.toLowerCase())
  );

  if (casesData.length === 0) {
    grid.innerHTML = `
      <div class="vaults-empty-box">
        <div class="vaults-empty-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="28" height="28"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>
        </div>
        <h3>No Document Vaults Yet</h3>
        <p>Add your legal documents or legal books. Documents uploaded here are stored permanently in your account.</p>
        <button type="button" class="btn-primary" id="btn-create-vault-empty">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          <span>Create Your First Vault</span>
        </button>
      </div>
    `;
    const emptyBtn = document.getElementById('btn-create-vault-empty');
    if (emptyBtn) emptyBtn.addEventListener('click', openCreateVaultModal);
    return;
  }

  if (filtered.length === 0) {
    grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 36px; font-size: 13px;">No matching vaults found for "${escapeHtml(searchFilter)}".</div>`;
    return;
  }

  // Prepend "+ Create New Vault" card
  const addCard = document.createElement('div');
  addCard.className = 'user-vault-card add-vault-card';
  addCard.innerHTML = `
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 120px; text-align: center;">
      <div style="width: 38px; height: 38px; border-radius: 50%; background: var(--bg-hover); display: flex; align-items: center; justify-content: center; margin-bottom: 8px; color: var(--accent-blue);">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="18" height="18"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      </div>
      <span style="font-size: 13.5px; font-weight: 700; color: var(--text-primary);">+ Create New Vault</span>
    </div>
  `;
  addCard.addEventListener('click', openCreateVaultModal);
  grid.appendChild(addCard);

  filtered.forEach(vault => {
    const card = document.createElement('div');
    card.className = 'user-vault-card';
    const docCount = vault.docs ? vault.docs.length : 0;
    card.innerHTML = `
      <div>
        <div class="vault-card-top">
          <div class="vault-card-icon-title">
            <div class="vault-card-folder-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>
            </div>
            <div>
              <div class="vault-card-title">${escapeHtml(vault.title)}</div>
            </div>
          </div>
        </div>
        <p class="vault-card-desc">${vault.desc ? escapeHtml(vault.desc) : 'Permanent document vault. Files indexed here are grounded into all your chats.'}</p>
      </div>
      <div class="vault-card-footer">
        <span class="vault-doc-stat">📄 ${docCount} ${docCount === 1 ? 'Document' : 'Documents'}</span>
        <div class="vault-card-actions">
          <button type="button" class="btn-vault-action btn-vault-research" data-action="chat" title="Chat with this Vault">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            <span>Chat with Vault</span>
          </button>
          <button type="button" class="btn-vault-action btn-vault-delete" data-action="delete" title="Delete Vault">✕</button>
        </div>
      </div>
    `;

    // Card click opens detail modal
    card.addEventListener('click', (e) => {
      if (e.target.closest('[data-action]')) return;
      openVaultDetailModal(vault.id);
    });

    const chatBtn = card.querySelector('[data-action="chat"]');
    if (chatBtn) {
      chatBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        activateVaultForChat(vault.id, vault.title);
      });
    }

    const deleteBtn = card.querySelector('[data-action="delete"]');
    if (deleteBtn) {
      deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (confirm(`Are you sure you want to delete the vault "${vault.title}" and its permanent documents?`)) {
          deleteUserVault(vault.id);
        }
      });
    }

    grid.appendChild(card);
  });
}

// Vault Creation
const newCaseFileInput = document.getElementById('new-case-file-input');
const newVaultDropzone = document.getElementById('new-vault-dropzone');
const newCaseFileList = document.getElementById('new-case-file-list');
let queuedCreateFiles = [];

if (newVaultDropzone && newCaseFileInput) {
  newVaultDropzone.addEventListener('click', () => {
    newCaseFileInput.click();
  });

  newCaseFileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      queuedCreateFiles = Array.from(e.target.files);
      if (newCaseFileList) {
        newCaseFileList.innerHTML = queuedCreateFiles.map(f => `📄 ${escapeHtml(f.name)}`).join('<br>');
      }
    }
  });
}

function openCreateVaultModal() {
  queuedCreateFiles = [];
  if (newCaseFileList) newCaseFileList.innerHTML = '';
  if (newCaseFileInput) newCaseFileInput.value = '';
  if (newCaseModal) {
    newCaseModal.style.display = 'flex';
    const titleInput = document.getElementById('new-case-title');
    if (titleInput) titleInput.focus();
  }
}

function closeCaseModal() {
  if (newCaseModal) newCaseModal.style.display = 'none';
  queuedCreateFiles = [];
  if (newCaseFileList) newCaseFileList.innerHTML = '';
  if (newCaseFileInput) newCaseFileInput.value = '';
}
if (closeCaseModalBtn) closeCaseModalBtn.addEventListener('click', closeCaseModal);
if (cancelCaseModalBtn) cancelCaseModalBtn.addEventListener('click', closeCaseModal);

if (newCaseModal) {
  newCaseModal.addEventListener('click', (e) => {
    if (e.target === newCaseModal) closeCaseModal();
  });
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeCaseModal();
    closeVaultDetailModal();
  }
});

// Submit Vault Creation
if (submitCreateCaseBtn) {
  submitCreateCaseBtn.addEventListener('click', async () => {
    const title = document.getElementById('new-case-title')?.value.trim();
    const desc = document.getElementById('new-case-desc')?.value.trim() || '';

    if (!title) {
      alert("Please enter a name for your Document Vault.");
      return;
    }

    submitCreateCaseBtn.disabled = true;
    submitCreateCaseBtn.textContent = "Creating...";

    let vaultId = Date.now();
    const caseNum = `VLT/${Date.now().toString().slice(-4)}`;

    // Sync with backend FIRST so we have the real persistent ID
    try {
      const caseRes = await fetch('/api/v1/cases', {
        method: 'POST',
        headers: getAuthHeaders(true),
        body: JSON.stringify({
          title,
          description: desc,
          case_number: caseNum,
          case_type: "Document Vault",
          status: "Active",
        }),
      });
      if (caseRes.ok) {
        const saved = await caseRes.json();
        if (saved && saved.id) vaultId = saved.id;
      }
    } catch (e) {
      console.log("Offline/fallback vault creation:", e);
    }

    // Immediately upload any files selected during creation to this new vault
    if (queuedCreateFiles.length > 0) {
      for (const file of queuedCreateFiles) {
        try {
          const formData = new FormData();
          formData.append('file', file);
          if (Number.isInteger(Number(vaultId)) && Number(vaultId) > 0 && Number(vaultId) < 100000000) {
            formData.append('case_id', String(vaultId));
          }
          await fetch('/api/v1/documents/upload', {
            method: 'POST',
            headers: getAuthHeaders(false),
            body: formData,
          });
        } catch (upErr) {
          console.warn("Error uploading initial file to vault:", upErr);
        }
      }
      queuedCreateFiles = [];
    }

    await loadUserVaults();
    closeCaseModal();

    if (document.getElementById('new-case-title')) document.getElementById('new-case-title').value = '';
    if (document.getElementById('new-case-desc')) document.getElementById('new-case-desc').value = '';
    submitCreateCaseBtn.disabled = false;
    submitCreateCaseBtn.textContent = "Create Document Vault";

    // Immediately open newly created vault with stable ID
    openVaultDetailModal(vaultId);
  });
}

// Delete Vault
async function deleteUserVault(vaultId) {
  casesData = casesData.filter(v => String(v.id) !== String(vaultId));
  if (String(activeCaseId) === String(vaultId)) {
    updateActiveVaultPill(null, null);
  }
  saveCasesToStorage();
  renderUserVaults();

  if (Number.isInteger(Number(vaultId)) && Number(vaultId) > 0 && Number(vaultId) < 100000000) {
    try {
      await fetch(`/api/v1/cases/${vaultId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(true)
      });
      await loadUserVaults();
    } catch (e) {
      console.warn("Backend vault delete notice:", e);
    }
  }
}

// Vault Detail Modal & File Upload
const vaultDetailOverlay = document.getElementById('vault-detail-overlay');
const closeVaultDetailBtn = document.getElementById('close-vault-detail-btn');
const btnChatWithDetailVault = document.getElementById('btn-chat-with-detail-vault');
const vaultDetailFileInput = document.getElementById('vault-detail-file-input');
const vaultModalDropzone = document.getElementById('vault-modal-dropzone');
const btnSubmitVaultDocs = document.getElementById('btn-submit-vault-docs');
const btnCloseVaultDetailFooter = document.getElementById('btn-close-vault-detail-footer');

const vaultPendingFiles = new Map();

function openVaultDetailModal(vaultId) {
  activeDetailVaultId = vaultId;
  const vault = casesData.find(v => String(v.id) === String(vaultId));
  if (!vault || !vaultDetailOverlay) return;

  const titleEl = document.getElementById('detail-modal-vault-title');
  const descEl = document.getElementById('detail-modal-vault-desc');
  const countEl = document.getElementById('detail-modal-docs-count');

  if (titleEl) titleEl.textContent = vault.title;
  if (descEl) descEl.textContent = vault.desc || 'Files uploaded here are permanently indexed in Weaviate for this specific vault.';
  const docCount = vault.docs ? vault.docs.length : 0;
  if (countEl) countEl.textContent = `${docCount} ${docCount === 1 ? 'Document' : 'Documents'}`;

  renderVaultDetailDocs(vault);
  vaultDetailOverlay.style.display = 'flex';
}

function closeVaultDetailModal() {
  if (vaultDetailOverlay) vaultDetailOverlay.style.display = 'none';
  activeDetailVaultId = null;
}

if (closeVaultDetailBtn) closeVaultDetailBtn.addEventListener('click', closeVaultDetailModal);
if (btnCloseVaultDetailFooter) btnCloseVaultDetailFooter.addEventListener('click', closeVaultDetailModal);
if (btnChatWithDetailVault) {
  btnChatWithDetailVault.addEventListener('click', () => {
    if (activeDetailVaultId) {
      const vault = casesData.find(v => String(v.id) === String(activeDetailVaultId));
      if (vault) {
        closeVaultDetailModal();
        activateVaultForChat(vault.id, vault.title);
      }
    }
  });
}
if (vaultDetailOverlay) {
  vaultDetailOverlay.addEventListener('click', (e) => {
    if (e.target === vaultDetailOverlay) closeVaultDetailModal();
  });
}

function renderVaultDetailDocs(vault) {
  const tbody = document.getElementById('detail-modal-docs-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (!vault.docs || vault.docs.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 32px 16px; font-size: 13px;">
          No documents uploaded yet to this vault.<br />
          <span style="font-size: 11.5px; opacity: 0.8;">Click above to browse and select legal files for this vault.</span>
        </td>
      </tr>
    `;
    return;
  }

  vault.docs.forEach(doc => {
    const isSubmitted = doc.submitted !== false;
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${escapeHtml(doc.name)}</strong></td>
      <td><span style="color: var(--text-secondary);">${escapeHtml(doc.type || 'Document')}</span></td>
      <td>
        <span class="vault-doc-status-badge ${isSubmitted ? '' : 'pending'}">
          ● ${isSubmitted ? 'Submitted' : 'Ready to Submit'}
        </span>
      </td>
      <td style="text-align: right;">
        <div style="display: flex; justify-content: flex-end; align-items: center; gap: 6px;">
          ${!isSubmitted ? `<button type="button" class="btn-vault-action btn-row-submit" data-submit-doc="${doc.id}">Submit</button>` : `<span class="vault-submitted-tag">Submitted</span>`}
          <button type="button" class="btn-vault-action btn-vault-delete" data-del-doc="${doc.id}" title="Remove Document">✕</button>
        </div>
      </td>
    `;

    // Row Submit Button
    const rowSubmitBtn = tr.querySelector('[data-submit-doc]');
    if (rowSubmitBtn) {
      rowSubmitBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        await submitVaultDoc(vault, doc.id);
      });
    }

    // Row Delete Button
    const delBtn = tr.querySelector('[data-del-doc]');
    if (delBtn) {
      delBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        vaultPendingFiles.delete(String(doc.id));
        const backendDocId = doc.backendId || (Number.isInteger(Number(doc.id)) && Number(doc.id) < 100000000 ? doc.id : null);
        vault.docs = vault.docs.filter(d => String(d.id) !== String(doc.id));
        saveCasesToStorage();
        renderVaultDetailDocs(vault);
        renderUserVaults();

        if (backendDocId) {
          try {
            await fetch(`/api/v1/documents/${backendDocId}`, {
              method: 'DELETE',
              headers: getAuthHeaders(true)
            });
            await loadUserVaults();
            const refreshed = casesData.find(v => String(v.id) === String(vault.id));
            if (refreshed) renderVaultDetailDocs(refreshed);
          } catch (delErr) {
            console.warn("Backend document delete notice:", delErr);
          }
        }
      });
    }
    tbody.appendChild(tr);
  });
}

// Submit a single document in a vault
async function submitVaultDoc(vault, docId) {
  const doc = vault.docs ? vault.docs.find(d => String(d.id) === String(docId)) : null;
  if (!doc) return;

  const file = vaultPendingFiles.get(String(docId));
  doc.status = 'Uploading...';
  renderVaultDetailDocs(vault);

  if (file) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      // Only send case_id if it's a real PostgreSQL integer ID (< 100000000)
      if (Number.isInteger(Number(vault.id)) && Number(vault.id) > 0 && Number(vault.id) < 100000000) {
        formData.append('case_id', String(vault.id));
      }
      const res = await fetch('/api/v1/documents/upload', {
        method: 'POST',
        headers: getAuthHeaders(false),
        body: formData,
      });
      if (res.ok) {
        const uploaded = await res.json();
        if (uploaded && uploaded.id) {
          doc.backendId = uploaded.id;
          doc.id = uploaded.id;
        }
      }
      vaultPendingFiles.delete(String(docId));
    } catch (err) {
      console.log("Vault document upload fallback:", err);
    }
  }

  doc.submitted = true;
  doc.status = 'Submitted';
  await loadUserVaults();
  const refreshed = casesData.find(v => String(v.id) === String(vault.id));
  if (refreshed) {
    renderVaultDetailDocs(refreshed);
  } else {
    renderVaultDetailDocs(vault);
  }
}

// Upload/queue file into Active Vault
async function uploadFileToActiveVault(file) {
  if (!file) return;
  let vault = casesData.find(v => String(v.id) === String(activeDetailVaultId));
  if (!vault && casesData.length > 0) {
    vault = casesData[0];
    activeDetailVaultId = vault.id;
  }
  if (!vault) return;

  const newDoc = {
    id: Date.now() + Math.floor(Math.random() * 1000),
    name: file.name,
    type: file.name.endsWith('.pdf') ? 'PDF Contract' : (file.name.endsWith('.docx') ? 'DOCX Pleading' : 'Legal Text'),
    submitted: false,
    status: 'Ready to Submit'
  };

  if (!vault.docs) vault.docs = [];
  vault.docs.unshift(newDoc);
  vaultPendingFiles.set(String(newDoc.id), file);

  saveCasesToStorage();
  renderVaultDetailDocs(vault);
  renderUserVaults();
}

// Submit all unsubmitted documents in the modal
async function submitAllActiveVaultDocs() {
  let vault = casesData.find(v => String(v.id) === String(activeDetailVaultId));
  if (!vault && casesData.length > 0) {
    vault = casesData[0];
    activeDetailVaultId = vault.id;
  }
  if (!vault || !vault.docs || vault.docs.length === 0) {
    closeVaultDetailModal();
    return;
  }

  if (btnSubmitVaultDocs) {
    btnSubmitVaultDocs.textContent = "Uploading...";
    btnSubmitVaultDocs.disabled = true;
  }

  const unsubmitted = vault.docs.filter(doc => doc.submitted === false);
  for (const doc of unsubmitted) {
    await submitVaultDoc(vault, doc.id);
  }

  if (btnSubmitVaultDocs) {
    btnSubmitVaultDocs.textContent = "✓ Submitted";
    setTimeout(() => {
      btnSubmitVaultDocs.textContent = "Submit";
      btnSubmitVaultDocs.disabled = false;
      closeVaultDetailModal();
    }, 400);
  } else {
    closeVaultDetailModal();
  }
}

if (btnSubmitVaultDocs) {
  btnSubmitVaultDocs.addEventListener('click', submitAllActiveVaultDocs);
}

if (vaultDetailFileInput) {
  vaultDetailFileInput.addEventListener('change', (e) => {
    if (e.target.files) {
      Array.from(e.target.files).forEach(f => uploadFileToActiveVault(f));
      e.target.value = '';
    }
  });
}

if (vaultModalDropzone) {
  vaultModalDropzone.addEventListener('click', () => {
    if (vaultDetailFileInput) vaultDetailFileInput.click();
  });
}

// Activate Vault for Chat Consultation
function activateVaultForChat(vaultId, vaultTitle) {
  activeCaseId = vaultId;
  activeCaseTitle = vaultTitle;
  updateActiveVaultPill(vaultId, vaultTitle);
  switchView('chat');
  if (queryInput) queryInput.focus();
}

function updateActiveVaultPill(vaultId, vaultTitle) {
  activeCaseId = vaultId;
  const pill = document.getElementById('active-vault-pill');
  const pillName = document.getElementById('active-vault-pill-name');
  if (pill && pillName) {
    if (vaultId && vaultTitle) {
      pillName.textContent = vaultTitle;
      pillName.title = vaultTitle;
      pill.style.display = 'inline-flex';
      if (queryInput) queryInput.placeholder = `Ask question grounded on "${vaultTitle}" & Indian law...`;
    } else {
      pill.style.display = 'none';
      if (queryInput) queryInput.placeholder = 'Ask any legal question or inquire about your vault...';
    }
  }
}

const btnClearVaultPill = document.getElementById('btn-clear-vault-pill');
if (btnClearVaultPill) {
  btnClearVaultPill.addEventListener('click', (e) => {
    e.stopPropagation();
    updateActiveVaultPill(null, null);
  });
}

// In-Chat Session File Attachment (One-Off, Ephemeral)
const sessionDocPill = document.getElementById('session-doc-pill');
const sessionDocPillName = document.getElementById('session-doc-pill-name');
const btnClearSessionDoc = document.getElementById('btn-clear-session-doc');

if (quickAttachFile) {
  quickAttachFile.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      activeSessionDoc = file;
      if (sessionDocPill && sessionDocPillName) {
        sessionDocPillName.textContent = file.name;
        sessionDocPillName.title = file.name;
        sessionDocPill.style.display = 'inline-flex';
      }
      e.target.value = '';
    }
  });
}

if (btnClearSessionDoc) {
  btnClearSessionDoc.addEventListener('click', (e) => {
    e.stopPropagation();
    activeSessionDoc = null;
    if (sessionDocPill) sessionDocPill.style.display = 'none';
  });
}

// Render Legal Research Corpus (28 Indian Statutes)
function renderLegalCorpus() {
  const grid = document.getElementById('corpus-grid');
  if (!grid) return;
  grid.innerHTML = '';

  legalStatutesData.forEach(statute => {
    const card = document.createElement('div');
    card.className = 'corpus-statute-card';
    card.innerHTML = `
      <div>
        <div class="statute-card-badge-row">
          <span class="statute-cat-pill cat-${statute.category}">${statute.categoryLabel}</span>
          <span class="statute-status-pill">● System Indexed</span>
        </div>
        <div class="statute-card-name">${escapeHtml(statute.name)}</div>
        <div class="statute-card-summary">${escapeHtml(statute.summary)}</div>
      </div>
      <div class="statute-card-bottom">
        <span class="statute-file-pill" title="${escapeHtml(statute.file)}">📄 ${escapeHtml(statute.file)}</span>
        <span>Foundational</span>
      </div>
    `;
    grid.appendChild(card);
  });
}


// ================= RECENT CONSULTATIONS & SESSIONS PERSISTENCE =================
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatRelativeTime(dateStr) {
  if (!dateStr) return 'Just now';
  try {
    let s = String(dateStr).trim();
    // If backend sent ISO string without timezone offset (Z or +/-HH:MM), treat as UTC
    if (!s.endsWith('Z') && !/[+-]\d{2}(?::?\d{2})?$/.test(s)) {
      s += 'Z';
    }
    const d = new Date(s);
    if (isNaN(d.getTime())) return 'Recently';
    const now = new Date();
    const diffSec = Math.floor((now - d) / 1000);
    if (diffSec < 45) return 'Just now';
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    const diffDays = Math.floor(diffHr / 24);
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
  } catch (e) {
    return 'Recently';
  }
}

async function loadUserChatSessions() {
  const listEl = document.getElementById('recent-list');
  if (!listEl) return;

  const token = localStorage.getItem('access_token');
  if (!token || token === 'session_active' || token.startsWith('mock_')) {
    renderRecentChatsLocal();
    return;
  }

  try {
    const res = await fetch('/api/v1/chat/sessions', {
      headers: getAuthHeaders(true)
    });

    if (res.status === 401) {
      logoutUser();
      return;
    }

    if (res.ok) {
      const data = await res.json();
      userChatSessions = data.sessions || [];
      renderUserChatSessions();
    } else {
      renderRecentChatsLocal();
    }
  } catch (err) {
    console.warn("Could not load backend chat sessions:", err);
    renderRecentChatsLocal();
  }
}

function renderUserChatSessions() {
  const listEl = document.getElementById('recent-list');
  if (!listEl) return;
  listEl.innerHTML = '';

  if (!userChatSessions || userChatSessions.length === 0) {
    listEl.innerHTML = `
      <div style="padding: 16px 10px; font-size: 11.5px; color: var(--text-muted); text-align: center; line-height: 1.5;">
        No recent chats.<br/>Click <strong>+ New Chat</strong> to start.
      </div>
    `;
    return;
  }

  userChatSessions.slice(0, 15).forEach(s => {
    const item = document.createElement('div');
    item.className = `recent-item ${s.id === activeSessionId ? 'active' : ''}`;
    item.setAttribute('data-session-id', s.id);

    item.innerHTML = `
      <div class="recent-item-title-row">
        <svg class="recent-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <span class="recent-title" title="${escapeHtml(s.title)}">${escapeHtml(s.title)}</span>
        <button class="recent-del-btn" title="Delete chat" data-id="${s.id}">
          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
        </button>
      </div>
      <span class="recent-time">${formatRelativeTime(s.updated_at || s.created_at)}</span>
    `;

    // Click to select session
    item.addEventListener('click', (e) => {
      if (e.target.closest('.recent-del-btn')) return;
      selectSession(s.id);
    });

    // Delete button click
    const delBtn = item.querySelector('.recent-del-btn');
    if (delBtn) {
      delBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteSession(s.id);
      });
    }

    listEl.appendChild(item);
  });
}

function renderRecentChatsLocal() {
  const listEl = document.getElementById('recent-list');
  if (!listEl) return;
  listEl.innerHTML = '';

  if (recentChats.length === 0) {
    listEl.innerHTML = `
      <div style="padding: 14px 10px; font-size: 11.5px; color: var(--text-muted); text-align: center; line-height: 1.4;">
        No recent chats.<br/>New queries will appear here.
      </div>
    `;
    return;
  }

  recentChats.slice(0, 8).forEach(item => {
    const div = document.createElement('div');
    div.className = 'recent-item';
    div.setAttribute('data-query', item.query);
    div.innerHTML = `
      <div class="recent-item-title-row">
        <svg class="recent-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <span class="recent-title">${escapeHtml(item.title)}</span>
      </div>
      <span class="recent-time">${item.time}</span>
    `;
    div.addEventListener('click', () => {
      switchView('chat');
      if (queryInput) queryInput.value = item.query;
      handleSend();
    });
    listEl.appendChild(div);
  });
}

async function selectSession(sessionId) {
  activeSessionId = sessionId;
  switchView('chat');

  // Highlight in sidebar
  const items = document.querySelectorAll('.recent-item');
  items.forEach(el => {
    if (el.getAttribute('data-session-id') === String(sessionId)) {
      el.classList.add('active');
    } else {
      el.classList.remove('active');
    }
  });

  if (heroView) heroView.style.display = 'none';
  if (messagesStream) {
    messagesStream.style.display = 'flex';
    messagesStream.innerHTML = `
      <div class="loading-indicator">
        <svg class="spin-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        <span>Loading chat transcript...</span>
      </div>
    `;
  }

  try {
    const res = await fetch(`/api/v1/chat/sessions/${sessionId}`, {
      headers: getAuthHeaders(true)
    });

    if (res.status === 401) {
      alert("⚠️ Your session has expired. Please sign in again.");
      logoutUser();
      return;
    }

    if (res.ok) {
      const data = await res.json();
      if (messagesStream) messagesStream.innerHTML = '';

      if ((!data.messages || data.messages.length === 0) && (!data.documents || data.documents.length === 0)) {
        if (heroView) heroView.style.display = 'flex';
        if (messagesStream) messagesStream.style.display = 'none';
      } else {
        // Render chat-level attached documents banner if any exist
        if (data.documents && data.documents.length > 0) {
          const docsBanner = document.createElement('div');
          docsBanner.className = 'session-attached-docs-banner';
          docsBanner.innerHTML = `
            <div class="session-attached-docs-header">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
              <span>Attached to this Chat:</span>
            </div>
            <div class="session-attached-docs-tags">
              ${data.documents.map(d => `<span class="session-doc-badge">📄 ${escapeHtml(d.file_name || d.title)}</span>`).join('')}
            </div>
          `;
          messagesStream.appendChild(docsBanner);
        }

        const sortedMessages = [...(data.messages || [])].sort((a, b) => {
          if (a.id && b.id) return a.id - b.id;
          return new Date(a.created_at || 0) - new Date(b.created_at || 0);
        });
        sortedMessages.forEach(msg => {
          let sources = [];
          if (Array.isArray(msg.sources)) {
            sources = msg.sources.map(s => {
              if (typeof s === 'string') return s;
              if (s.case_title) return `🏛️ ${s.case_title} [${s.citation || ''}] — ${s.court || ''}`;
              if (s.document_title) return `📖 ${s.document_title}${s.page_number ? `, Page ${s.page_number}` : ''}`;
              return JSON.stringify(s);
            });
          }
          appendMessage(msg.role === 'user' ? 'user' : 'ai', msg.content, sources);
        });
      }
    } else {
      if (messagesStream) {
        messagesStream.innerHTML = `<div class="message-bubble ai"><div class="bubble-content">⚠️ Could not load transcript for this chat.</div></div>`;
      }
    }
  } catch (err) {
    console.error("Error loading session transcript:", err);
    if (messagesStream) {
      messagesStream.innerHTML = `<div class="message-bubble ai"><div class="bubble-content">⚠️ Network error loading chat transcript.</div></div>`;
    }
  }
}

async function deleteSession(sessionId) {
  if (!confirm("Are you sure you want to delete this chat thread?")) return;

  try {
    const res = await fetch(`/api/v1/chat/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(true)
    });

    if (res.ok) {
      if (String(activeSessionId) === String(sessionId)) {
        startNewConsultation();
      }
      await loadUserChatSessions();
    } else {
      alert("Could not delete chat. Please try again.");
    }
  } catch (err) {
    console.error("Error deleting session:", err);
  }
}

// Global hooks for Settings Hub to execute safe purges
window.purgeAllUploadedDocuments = function() {
  if (Array.isArray(casesData)) {
    casesData.forEach(c => {
      c.docs = [];
    });
    saveCasesToStorage();
    renderUserVaults();
  }
};

window.clearAllConsultations = function() {
  recentChats = [];
  userChatSessions = [];
  saveRecentChats();
  startNewConsultation();
  loadUserChatSessions();
};

window.purgeAllCasesAndDocs = function() {
  casesData = [];
  activeCaseId = null;
  activeCaseTitle = '';
  saveCasesToStorage();
  renderUserVaults();
};


// ================= THEME TOGGLE =================
if (themeToggleBtn) {
  themeToggleBtn.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
  });
}


// ================= LIVE CHAMBER DATE & TIME =================
function updateHeaderDateTime() {
  const dateEl = document.getElementById('datetime-date-text');
  const timeEl = document.getElementById('datetime-time-text');
  if (!dateEl || !timeEl) return;

  const now = new Date();
  const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'June', 'July', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec'];
  const dayName = weekdays[now.getDay()];
  const dayNum = now.getDate();
  const monthName = months[now.getMonth()];
  const year = now.getFullYear();
  dateEl.textContent = `${dayName}, ${dayNum} ${monthName}, ${year}`;

  const timeOptions = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true };
  timeEl.textContent = now.toLocaleTimeString('en-IN', timeOptions);
}

// ================= USER PROFILE & SESSION VERIFICATION =================
function updateUserProfileUI() {
  const storedName = localStorage.getItem('user_name') || localStorage.getItem('user_email') || 'User';
  const storedEmail = localStorage.getItem('user_email') || '';
  const storedRole = localStorage.getItem('user_role') || 'user';
  const displayRole = storedRole.charAt(0).toUpperCase() + storedRole.slice(1);

  const cleanName = storedName.replace(/^Adv\.?\s+/i, '').trim();
  const parts = cleanName.split(/\s+/).filter(Boolean);
  let initials = 'U';
  if (parts.length >= 2) {
    initials = (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  } else if (parts.length === 1 && parts[0].length >= 2) {
    initials = parts[0].slice(0, 2).toUpperCase();
  } else if (parts.length === 1 && parts[0].length === 1) {
    initials = parts[0].toUpperCase();
  }

  const sidebarName = document.getElementById('sidebar-profile-name');
  const sidebarAvatar = document.getElementById('sidebar-avatar-circle');
  const sidebarRole = document.getElementById('sidebar-profile-role');
  const headerName = document.getElementById('header-user-name');
  const headerAvatar = document.getElementById('header-avatar-circle');
  const headerRole = document.getElementById('header-user-role');
  const greetingTitle = document.getElementById('hero-greeting-title');

  if (sidebarName) sidebarName.textContent = storedName;
  if (sidebarAvatar) sidebarAvatar.textContent = initials;
  if (sidebarRole) sidebarRole.textContent = displayRole;
  if (headerName) headerName.textContent = storedName;
  if (headerAvatar) headerAvatar.textContent = initials;
  if (headerRole) headerRole.textContent = displayRole;
  if (greetingTitle) {
    const firstName = parts[0] ? parts[0].split('@')[0] : 'there';
    greetingTitle.textContent = `Hello ${firstName},`;
  }
}

async function verifySession() {
  const token = localStorage.getItem('access_token');
  if (!token || token === 'session_active' || token.startsWith('mock_')) {
    logoutUser();
    return;
  }
  try {
    const res = await fetch('/api/v1/auth/me', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      const user = await res.json();
      if (user.full_name) localStorage.setItem('user_name', user.full_name);
      if (user.role) localStorage.setItem('user_role', user.role);
      if (user.email) localStorage.setItem('user_email', user.email);
      updateUserProfileUI();
    } else if (res.status === 401) {
      logoutUser();
    }
  } catch (err) {
    console.warn("Backend auth verification unreachable:", err);
  }
}

// ================= CLICK ON NAME TO SHOW/HIDE LOGOUT =================
const userProfileContainer = document.getElementById('header-user-profile');
const logoutBtn = document.getElementById('logout-btn');

if (userProfileContainer && logoutBtn) {
  // When user clicks anywhere on his profile/name at top right
  userProfileContainer.addEventListener('click', (e) => {
    // If the click is on the logout button itself, trigger logout
    if (e.target.closest('#logout-btn')) {
      e.stopPropagation();
      logoutUser();
      return;
    }

    // Toggle logout button visibility
    const isHidden = (logoutBtn.style.display === 'none' || !logoutBtn.style.display);
    if (isHidden) {
      logoutBtn.style.display = 'inline-flex';
      userProfileContainer.classList.add('active');
    } else {
      logoutBtn.style.display = 'none';
      userProfileContainer.classList.remove('active');
    }
  });

  // Hide logout button if user clicks outside the profile area
  document.addEventListener('click', (e) => {
    if (!e.target.closest('#header-user-profile')) {
      logoutBtn.style.display = 'none';
      userProfileContainer.classList.remove('active');
    }
  });
}

// ================= CLICK ON SIDEBAR NAME / ARROW TO SHOW/HIDE LOGOUT =================
const sidebarProfileCard = document.getElementById('sidebar-profile-card');
const sidebarChevron = document.getElementById('sidebar-profile-chevron');
const sidebarLogoutBtn = document.getElementById('sidebar-logout-btn');

if (sidebarProfileCard && sidebarLogoutBtn) {
  // When user clicks on the bottom-left profile card, name, or arrow
  sidebarProfileCard.addEventListener('click', (e) => {
    // If the click is on the logout button itself, trigger logout
    if (e.target.closest('#sidebar-logout-btn')) {
      e.stopPropagation();
      logoutUser();
      return;
    }

    // Toggle sidebar logout button visibility
    const isHidden = (sidebarLogoutBtn.style.display === 'none' || !sidebarLogoutBtn.style.display);
    if (isHidden) {
      sidebarLogoutBtn.style.display = 'inline-flex';
      if (sidebarChevron) sidebarChevron.style.display = 'none';
      sidebarProfileCard.classList.add('active');
    } else {
      sidebarLogoutBtn.style.display = 'none';
      if (sidebarChevron) sidebarChevron.style.display = 'block';
      sidebarProfileCard.classList.remove('active');
    }
  });

  // Hide sidebar logout button when clicking outside the sidebar profile area
  document.addEventListener('click', (e) => {
    if (!e.target.closest('#sidebar-profile-card')) {
      sidebarLogoutBtn.style.display = 'none';
      if (sidebarChevron) sidebarChevron.style.display = 'block';
      sidebarProfileCard.classList.remove('active');
    }
  });
}

// ================= INITIALIZATION =================
updateHeaderDateTime();
setInterval(updateHeaderDateTime, 1000);
// Periodically update relative timestamps ("Just now", "2m ago") in sidebar
setInterval(() => {
  if (typeof userChatSessions !== 'undefined' && userChatSessions.length > 0) {
    renderUserChatSessions();
  }
}, 60000);
updateUserProfileUI();
verifySession();
loadUserChatSessions();
loadUserVaults();
renderLegalCorpus();
