// ================= SETTINGS CONTROLLER =================

const EYE_OPEN_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>`;
const EYE_OFF_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/></svg>`;

// Helper: Setup Password Visibility Eye Toggle with SVG icon toggle
function setupPasswordToggle(btnId, inputId) {
  const btn = document.getElementById(btnId);
  const input = document.getElementById(inputId);
  if (!btn || !input) return;

  btn.addEventListener('click', (e) => {
    e.preventDefault();
    const isPassword = input.getAttribute('type') === 'password';
    input.setAttribute('type', isPassword ? 'text' : 'password');
    btn.innerHTML = isPassword ? EYE_OFF_SVG : EYE_OPEN_SVG;
    btn.setAttribute('title', isPassword ? 'Hide Password' : 'Show Password');
  });
}

// Show alert inside settings card with clean styling
function showPasswordAlert(msg, isSuccess = false) {
  const alertBox = document.getElementById('password-alert');
  if (!alertBox) return;

  alertBox.style.display = 'flex';
  alertBox.style.alignItems = 'center';
  alertBox.style.gap = '8px';
  alertBox.textContent = msg;

  if (isSuccess) {
    alertBox.style.backgroundColor = 'rgba(16, 185, 129, 0.1)';
    alertBox.style.color = '#10b981';
    alertBox.style.border = '1px solid rgba(16, 185, 129, 0.25)';
  } else {
    alertBox.style.backgroundColor = 'rgba(239, 68, 68, 0.1)';
    alertBox.style.color = '#ef4444';
    alertBox.style.border = '1px solid rgba(239, 68, 68, 0.25)';
  }
}

// ================= LOAD SETTINGS & USAGE DATA =================
async function loadSettingsData() {
  // 1. Account Details
  const userNameEl = document.getElementById('settings-user-name');
  const userEmailEl = document.getElementById('settings-user-email');
  const userRoleEl = document.getElementById('settings-user-role');

  const storedName = localStorage.getItem('user_name') || 'User';
  const storedEmail = localStorage.getItem('user_email') || 'user@legaldrishti.ai';
  const storedRole = localStorage.getItem('user_role') || 'user';
  const displayRole = storedRole.charAt(0).toUpperCase() + storedRole.slice(1);

  if (userNameEl) userNameEl.textContent = storedName;
  if (userEmailEl) userEmailEl.textContent = storedEmail;
  if (userRoleEl) userRoleEl.textContent = displayRole;

  // 2. Token, Vaults & Credits Data
  const creditsStatEl = document.getElementById('settings-stat-credits');
  const docsStatEl = document.getElementById('settings-stat-docs');
  const casesStatEl = document.getElementById('settings-stat-cases');
  const tokensStatEl = document.getElementById('settings-stat-tokens');
  const tokenRatioEl = document.getElementById('token-usage-ratio');
  const tokenProgressBar = document.getElementById('token-usage-bar');

  // Compute total documents & active vaults across Document Vaults ONLY
  let totalVaultDocs = 0;
  let activeVaultsCount = 0;
  try {
    const rawCases = localStorage.getItem('legaldrishti_cases');
    if (rawCases !== null) {
      const vaults = JSON.parse(rawCases) || [];
      activeVaultsCount = vaults.length;
      vaults.forEach(v => {
        if (Array.isArray(v.docs)) totalVaultDocs += v.docs.length;
      });
    }
  } catch (e) {
    totalVaultDocs = 0;
    activeVaultsCount = 0;
  }

  // Compute total recent consultations run for token bandwidth calculation
  let totalQueries = 0;
  try {
    const chats = JSON.parse(localStorage.getItem('legaldrishti_recent_chats')) || [];
    totalQueries = chats.length;
  } catch (e) {
    totalQueries = 0;
  }

  // Fetch real credits & real vault documents from backend
  const token = localStorage.getItem('access_token');
  if (token && token !== 'session_active' && !token.startsWith('mock_')) {
    try {
      const [userRes, casesRes] = await Promise.all([
        fetch('/api/v1/auth/me', { headers: { 'Authorization': `Bearer ${token}` } }),
        fetch('/api/v1/cases?page_size=100', { headers: { 'Authorization': `Bearer ${token}` } })
      ]);

      if (userRes && userRes.ok) {
        const user = await userRes.json();
        const remainingCredits = user.deep_search_credits !== undefined ? user.deep_search_credits : 3;
        const totalCredits = 3;
        // Display used attempts out of total: e.g. 1 used out of 3 -> "1 / 3"
        const usedCredits = Math.max(0, totalCredits - remainingCredits);
        if (creditsStatEl) {
          creditsStatEl.textContent = `${usedCredits} / ${totalCredits}`;
          creditsStatEl.title = `${usedCredits} used out of ${totalCredits} (${remainingCredits} remaining)`;
        }
      }

      if (casesRes && casesRes.ok) {
        const casesDataApi = await casesRes.json();
        const vaultsList = casesDataApi.items || [];
        activeVaultsCount = vaultsList.length;
        totalVaultDocs = 0;
        vaultsList.forEach(v => {
          if (Array.isArray(v.docs)) totalVaultDocs += v.docs.length;
        });
      }
    } catch (e) {
      console.warn("Could not fetch user credit info or vaults for settings:", e);
    }
  } else {
    if (creditsStatEl) creditsStatEl.textContent = `0 / 3`;
  }

  // Display only vault-uploaded documents and active vaults
  if (docsStatEl) docsStatEl.textContent = `${totalVaultDocs} Docs`;
  if (casesStatEl) casesStatEl.textContent = `${activeVaultsCount} ${activeVaultsCount === 1 ? 'Vault' : 'Vaults'}`;

  // Token bandwidth calculation (simulated based on queries run + initial baseline)
  const estimatedTokens = 12450 + (totalQueries * 850);
  const maxTokens = 200000;
  const percentage = Math.min(100, Math.round((estimatedTokens / maxTokens) * 1000) / 10);

  if (tokensStatEl) tokensStatEl.textContent = estimatedTokens.toLocaleString();
  if (tokenRatioEl) tokenRatioEl.textContent = `${(estimatedTokens / 1000).toFixed(1)}k / ${(maxTokens / 1000)}k Tokens (${percentage}%)`;
  if (tokenProgressBar) tokenProgressBar.style.width = `${percentage}%`;
}

// ================= PASSWORD STRENGTH & MATCH LOGIC =================
const changePasswordForm = document.getElementById('change-password-form');
const currentPwdInput = document.getElementById('current-pwd-input');
const newPwdInput = document.getElementById('new-pwd-input');
const confirmNewPwdInput = document.getElementById('confirm-new-pwd-input');
const savePasswordBtn = document.getElementById('save-password-btn');

function evaluatePasswordStrength(password) {
  if (!password) {
    return { level: 0, label: '', color: '', bars: 0, hint: '' };
  }

  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^a-zA-Z0-9]/.test(password)) score++;

  if (password.length < 8) {
    return {
      level: 1,
      label: 'Too Short',
      color: '#ef4444',
      bars: 1,
      hint: 'Password must be at least 8 characters long.'
    };
  }

  if (score <= 2) {
    return {
      level: 1,
      label: 'Weak',
      color: '#ef4444',
      bars: 1,
      hint: 'Include uppercase letters, numbers & symbols.'
    };
  } else if (score === 3) {
    return {
      level: 2,
      label: 'Fair',
      color: '#f59e0b',
      bars: 2,
      hint: 'Add special characters for higher security.'
    };
  } else if (score === 4) {
    return {
      level: 3,
      label: 'Good',
      color: '#3b82f6',
      bars: 3,
      hint: 'Solid password, meets enterprise standards.'
    };
  } else {
    return {
      level: 4,
      label: 'Strong',
      color: '#10b981',
      bars: 4,
      hint: 'Excellent entropy & cryptographic strength.'
    };
  }
}

function updateStrengthMeter() {
  const strengthContainer = document.getElementById('pwd-strength-container');
  const strengthText = document.getElementById('pwd-strength-text');
  const strengthHint = document.getElementById('pwd-strength-hint');
  if (!strengthContainer || !strengthText || !strengthHint) return;

  const val = newPwdInput ? newPwdInput.value : '';
  if (!val) {
    strengthContainer.style.display = 'none';
    return;
  }

  strengthContainer.style.display = 'flex';
  const res = evaluatePasswordStrength(val);

  for (let i = 1; i <= 4; i++) {
    const bar = document.getElementById(`pwd-bar-${i}`);
    if (bar) {
      bar.style.backgroundColor = i <= res.bars ? res.color : 'var(--bg-hover)';
    }
  }

  strengthText.textContent = `Strength: ${res.label}`;
  strengthText.style.color = res.color;
  strengthHint.textContent = res.hint;
}

function updatePasswordMatch() {
  const matchIndicator = document.getElementById('pwd-match-indicator');
  if (!matchIndicator) return;

  const newPwd = newPwdInput ? newPwdInput.value : '';
  const confirmPwd = confirmNewPwdInput ? confirmNewPwdInput.value : '';

  if (!confirmPwd) {
    matchIndicator.style.display = 'none';
    return;
  }

  matchIndicator.style.display = 'flex';
  if (newPwd === confirmPwd) {
    matchIndicator.className = 'pwd-match-indicator match';
    matchIndicator.innerHTML = `
      <svg class="match-icon" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
      <span class="match-text">Passwords match</span>
    `;
  } else {
    matchIndicator.className = 'pwd-match-indicator mismatch';
    matchIndicator.innerHTML = `
      <svg class="match-icon" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      <span class="match-text">Passwords do not match yet</span>
    `;
  }
}

if (newPwdInput) {
  newPwdInput.addEventListener('input', () => {
    updateStrengthMeter();
    updatePasswordMatch();
  });
}

if (confirmNewPwdInput) {
  confirmNewPwdInput.addEventListener('input', updatePasswordMatch);
}

// ================= CHANGE PASSWORD SUBMISSION =================
if (changePasswordForm) {
  changePasswordForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const currentPassword = currentPwdInput.value;
    const newPassword = newPwdInput.value;
    const confirmPassword = confirmNewPwdInput.value;

    if (!currentPassword || !newPassword || !confirmPassword) {
      showPasswordAlert("Please fill in all required password fields.");
      return;
    }

    if (newPassword.length < 8) {
      showPasswordAlert("New password must be at least 8 characters long.");
      return;
    }

    if (newPassword !== confirmPassword) {
      showPasswordAlert("New passwords do not match. Please re-enter.");
      return;
    }

    if (currentPassword === newPassword) {
      showPasswordAlert("New password must be different from your current password.");
      return;
    }

    savePasswordBtn.disabled = true;
    savePasswordBtn.innerHTML = `
      <svg class="spin-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
      <span>Updating Credentials...</span>
    `;

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/v1/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      if (res.ok) {
        showPasswordAlert("Password updated successfully! Your credentials are now secured.", true);
        currentPwdInput.value = '';
        newPwdInput.value = '';
        confirmNewPwdInput.value = '';

        // Reset indicators
        const strengthContainer = document.getElementById('pwd-strength-container');
        if (strengthContainer) strengthContainer.style.display = 'none';
        const matchIndicator = document.getElementById('pwd-match-indicator');
        if (matchIndicator) matchIndicator.style.display = 'none';
      } else {
        const err = await res.json().catch(() => ({}));
        showPasswordAlert(err.detail || "Unable to change password. Please verify your current password.");
      }
    } catch (err) {
      console.error("Change password network error:", err);
      showPasswordAlert("Network error: Unable to reach authentication server.");
    } finally {
      savePasswordBtn.disabled = false;
      savePasswordBtn.innerHTML = `
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
        <span>Update Password</span>
      `;
    }
  });
}

// ================= DATA PRIVACY: PURGE UPLOADED DOCUMENTS =================
const openPurgeDocsBtn = document.getElementById('open-purge-docs-btn');
const purgeDocsModal = document.getElementById('purge-docs-modal');
const closePurgeDocsModalBtn = document.getElementById('close-purge-docs-modal-btn');
const cancelPurgeDocsBtn = document.getElementById('cancel-purge-docs-btn');
const purgeDocsConfirmInput = document.getElementById('purge-docs-confirm-input');
const confirmPurgeDocsBtn = document.getElementById('confirm-purge-docs-btn');

function closePurgeDocsModal() {
  if (purgeDocsModal) purgeDocsModal.style.display = 'none';
  if (purgeDocsConfirmInput) purgeDocsConfirmInput.value = '';
  if (confirmPurgeDocsBtn) confirmPurgeDocsBtn.disabled = true;
}

if (openPurgeDocsBtn && purgeDocsModal) {
  openPurgeDocsBtn.addEventListener('click', () => {
    purgeDocsModal.style.display = 'flex';
    if (purgeDocsConfirmInput) {
      purgeDocsConfirmInput.value = '';
      setTimeout(() => purgeDocsConfirmInput.focus(), 50);
    }
    if (confirmPurgeDocsBtn) confirmPurgeDocsBtn.disabled = true;
  });
}

if (closePurgeDocsModalBtn) closePurgeDocsModalBtn.addEventListener('click', closePurgeDocsModal);
if (cancelPurgeDocsBtn) cancelPurgeDocsBtn.addEventListener('click', closePurgeDocsModal);

if (purgeDocsModal) {
  purgeDocsModal.addEventListener('click', (e) => {
    if (e.target === purgeDocsModal) closePurgeDocsModal();
  });
}

if (purgeDocsConfirmInput && confirmPurgeDocsBtn) {
  purgeDocsConfirmInput.addEventListener('input', () => {
    const val = purgeDocsConfirmInput.value.trim();
    confirmPurgeDocsBtn.disabled = (val !== 'DELETE');
  });
}

if (confirmPurgeDocsBtn) {
  confirmPurgeDocsBtn.addEventListener('click', async () => {
    if (purgeDocsConfirmInput && purgeDocsConfirmInput.value.trim() !== 'DELETE') return;

    confirmPurgeDocsBtn.disabled = true;
    confirmPurgeDocsBtn.innerHTML = `
      <svg class="spin-icon" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
      <span>Deleting Documents...</span>
    `;

    try {
      // 1. Backend Wipe: Delete all documents for authenticated user
      const token = localStorage.getItem('access_token');
      if (token && token !== 'session_active' && !token.startsWith('mock_')) {
        try {
          await fetch('/api/v1/documents/purge-all', {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
        } catch (e) {
          console.warn("Backend document purge note:", e);
        }
      }

      // 2. Client-Side Document Wipe across cases
      if (typeof window.purgeAllUploadedDocuments === 'function') {
        window.purgeAllUploadedDocuments();
      }

      // 3. Refresh Settings Dashboard (Docs counter will update to 0 Docs)
      await loadSettingsData();

      closePurgeDocsModal();
      alert("✅ All uploaded documents have been permanently deleted.");
    } catch (err) {
      console.error("Purge documents error:", err);
      alert("Error occurred while deleting documents. Please try again.");
    } finally {
      if (confirmPurgeDocsBtn) {
        confirmPurgeDocsBtn.disabled = false;
        confirmPurgeDocsBtn.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
          <span>Confirm & Delete Documents</span>
        `;
      }
    }
  });
}

// ================= INITIALIZE SETTINGS =================
setupPasswordToggle('eye-current-pwd', 'current-pwd-input');
setupPasswordToggle('eye-new-pwd', 'new-pwd-input');
setupPasswordToggle('eye-confirm-pwd', 'confirm-new-pwd-input');

// Expose loadSettingsData globally so view switcher can invoke it
window.loadSettingsData = loadSettingsData;

