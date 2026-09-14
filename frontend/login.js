// ================= SESSION CHECK =================
(function checkExistingSession() {
  const token = localStorage.getItem('access_token');
  if (token && token !== 'session_active' && !token.startsWith('mock_')) {
    window.location.replace('index.html');
  }
})();

// ================= LOGIN CONTROLLER =================
const loginForm = document.getElementById('login-form');
const emailInput = document.getElementById('email-input');
const passwordInput = document.getElementById('password-input');
const submitBtn = document.getElementById('submit-btn');
const eyeToggle = document.getElementById('eye-toggle');
const googleSsoBtn = document.getElementById('google-sso-btn');
const outlookSsoBtn = document.getElementById('outlook-sso-btn');

// Toggle Password Visibility
eyeToggle.addEventListener('click', () => {
  const currentType = passwordInput.getAttribute('type');
  if (currentType === 'password') {
    passwordInput.setAttribute('type', 'text');
    eyeToggle.style.color = '#111827';
  } else {
    passwordInput.setAttribute('type', 'password');
    eyeToggle.style.color = '#9ca3af';
  }
});

// Social SSO buttons - deactivated (clicking does nothing)
if (googleSsoBtn) {
  googleSsoBtn.addEventListener('click', (e) => {
    e.preventDefault();
  });
}

if (outlookSsoBtn) {
  outlookSsoBtn.addEventListener('click', (e) => {
    e.preventDefault();
  });
}

// Form Submission & API Integration
loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  const email = emailInput.value.trim().toLowerCase();
  const password = passwordInput.value;

  if (!email || !password) return;

  submitBtn.disabled = true;
  submitBtn.textContent = "Authenticating...";

  try {
    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (response.ok) {
      const data = await response.json();
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      localStorage.setItem('user_email', email);

      // Fetch user profile to get real full_name and role
      try {
        const meRes = await fetch('/api/v1/auth/me', {
          headers: { 'Authorization': `Bearer ${data.access_token}` },
        });
        if (meRes.ok) {
          const profile = await meRes.json();
          if (profile.full_name) {
            localStorage.setItem('user_name', profile.full_name);
          }
          if (profile.role) {
            localStorage.setItem('user_role', profile.role);
          }
        }
      } catch (e) {
        console.warn("Could not fetch user profile:", e);
      }

      submitBtn.textContent = "Success! Redirecting...";
      setTimeout(() => {
        window.location.href = 'index.html';
      }, 400);
    } else {
      const err = await response.json().catch(() => ({}));
      alert(`⚠️ Authentication Notice: ${err.detail || 'Invalid email or password.'}`);
      submitBtn.disabled = false;
      submitBtn.textContent = "Sign In";
    }
  } catch (error) {
    console.error("Backend authentication unreachable:", error);
    alert("⚠️ Unable to connect to the authentication server. Please verify your connection or ensure the server is running.");
    submitBtn.disabled = false;
    submitBtn.textContent = "Sign In";
  }
});
