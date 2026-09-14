// ================= SESSION CHECK =================
(function checkExistingSession() {
  const token = localStorage.getItem('access_token');
  if (token && token !== 'session_active' && !token.startsWith('mock_')) {
    window.location.replace('index.html');
  }
})();

// ================= SIGNUP CONTROLLER =================
const signupForm = document.getElementById('signup-form');
const fullnameInput = document.getElementById('fullname-input');
const emailInput = document.getElementById('email-input');
const passwordInput = document.getElementById('password-input');
const confirmPasswordInput = document.getElementById('confirm-password-input');
const signupSubmitBtn = document.getElementById('signup-submit-btn');
const signupAlert = document.getElementById('signup-alert');

const eyeToggle1 = document.getElementById('eye-toggle-1');
const eyeToggle2 = document.getElementById('eye-toggle-2');

// Password Visibility Toggles
function setupEyeToggle(toggleBtn, inputEl) {
  if (!toggleBtn || !inputEl) return;
  toggleBtn.addEventListener('click', () => {
    const isPassword = inputEl.getAttribute('type') === 'password';
    inputEl.setAttribute('type', isPassword ? 'text' : 'password');
    toggleBtn.style.color = isPassword ? '#111827' : '#9ca3af';
  });
}

setupEyeToggle(eyeToggle1, passwordInput);
setupEyeToggle(eyeToggle2, confirmPasswordInput);

function showAlert(msg, isError = true) {
  if (!signupAlert) return;
  signupAlert.style.display = 'block';
  signupAlert.textContent = msg;
  if (isError) {
    signupAlert.style.background = '#fef2f2';
    signupAlert.style.color = '#b91c1c';
    signupAlert.style.border = '1px solid #fecaca';
  } else {
    signupAlert.style.background = '#f0fdf4';
    signupAlert.style.color = '#15803d';
    signupAlert.style.border = '1px solid #bbf7d0';
  }
}

signupForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  const fullName = fullnameInput.value.trim();
  const email = emailInput.value.trim().toLowerCase();
  const role = 'user'; // Default persona per system design
  const password = passwordInput.value;
  const confirmPassword = confirmPasswordInput.value;

  if (!fullName || !email || !password) {
    showAlert("Please complete all required fields.");
    return;
  }

  // Basic email pattern verification
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    showAlert("Please enter a valid email address.");
    return;
  }

  if (password.length < 8) {
    showAlert("Password must be at least 8 characters long.");
    return;
  }

  if (password !== confirmPassword) {
    showAlert("Passwords do not match. Please re-enter.");
    return;
  }

  signupSubmitBtn.disabled = true;
  signupSubmitBtn.textContent = "Creating Account...";

  try {
    const res = await fetch('/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: email,
        password: password,
        full_name: fullName,
        role: role
      }),
    });

    if (res.ok) {
      showAlert("Account registered successfully! Signing you in...", false);

      // Automatically authenticate to obtain JWT tokens
      try {
        const loginRes = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: email, password: password }),
        });

        if (loginRes.ok) {
          const tokenData = await loginRes.json();
          localStorage.setItem('access_token', tokenData.access_token);
          localStorage.setItem('refresh_token', tokenData.refresh_token);
          localStorage.setItem('user_email', email);
          localStorage.setItem('user_name', fullName);
          localStorage.setItem('user_role', role);

          setTimeout(() => {
            window.location.href = 'index.html';
          }, 600);
          return;
        }
      } catch (loginErr) {
        console.warn("Auto-login request failed:", loginErr);
      }

      // If auto-login didn't complete, redirect to login page for manual entry
      setTimeout(() => {
        window.location.href = 'login.html';
      }, 1000);

    } else {
      const err = await res.json().catch(() => ({}));
      showAlert(err.detail || "Could not register account. Please verify your details.");
      signupSubmitBtn.disabled = false;
      signupSubmitBtn.textContent = "Create Account";
    }
  } catch (err) {
    console.error("Sign up network error:", err);
    showAlert("⚠️ Unable to reach the registration server. Please verify your connection or try again later.");
    signupSubmitBtn.disabled = false;
    signupSubmitBtn.textContent = "Create Account";
  }
});
