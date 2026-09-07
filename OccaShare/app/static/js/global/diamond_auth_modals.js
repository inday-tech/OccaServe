/**
 * Auth Modal Controller
 */

function openAuthModal(type, targetEmail = null) {
    const overlay = document.getElementById('authModalOverlay');
    const container = overlay ? overlay.querySelector('.auth-modal-container') : null;
    const loginContent = document.getElementById('authModalLogin');
    const signupContent = document.getElementById('authModalSignup');
    const forgotContent = document.getElementById('authModalForgot');
    const verifyContent = document.getElementById('authModalVerify');
    const catererContent = document.getElementById('authModalCaterer');

    if (!overlay || !loginContent || !signupContent || !forgotContent || !verifyContent) return;

    // Reset all
    loginContent.classList.remove('active');
    signupContent.classList.remove('active');
    forgotContent.classList.remove('active');
    verifyContent.classList.remove('active');
    if (catererContent) catererContent.classList.remove('active');
    if (container) container.classList.remove('wide');

    if (type === 'login') {
        loginContent.classList.add('active');
    } else if (type === 'signup') {
        signupContent.classList.add('active');
    } else if (type === 'forgot') {
        forgotContent.classList.add('active');
        const forgotErr = document.getElementById('forgotErrorContainer');
        const forgotSucc = document.getElementById('forgotSuccessContainer');
        if (forgotErr) forgotErr.style.display = 'none';
        if (forgotSucc) forgotSucc.style.display = 'none';
    } else if (type === 'verify') {
        verifyContent.classList.add('active');
        if (targetEmail) {
            const emailDisplay = document.getElementById('email-display');
            const emailHidden = document.getElementById('emailField');
            if (emailDisplay) emailDisplay.innerText = targetEmail;
            if (emailHidden) emailHidden.value = targetEmail;
        }
        if (typeof window.startTimer === 'function') window.startTimer();
        if (typeof window.setupOtpInputListeners === 'function') window.setupOtpInputListeners();
        if (typeof window.initVerifyPolling === 'function') window.initVerifyPolling();
    } else if (type === 'caterer-signup' && catererContent) {
        catererContent.classList.add('active');
        if (container) container.classList.add('wide');
    }

    // Show overlay
    overlay.classList.add('active');
    document.body.classList.add('modal-open');
}

function closeAuthModal() {
    const overlay = document.getElementById('authModalOverlay');
    if (!overlay) return;

    overlay.classList.remove('active');
    document.body.classList.remove('modal-open');

    // Optional: Clean up URL hash
    if (window.location.hash.includes('#login') || window.location.hash.includes('#signup')) {
        history.pushState("", document.title, window.location.pathname + window.location.search);
    }
}

// Global initialization
document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.getElementById('authModalOverlay');

    // Close on background click
    if (overlay) {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeAuthModal();
        });
    }

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeAuthModal();
    });

    // Intercept navbar buttons
    const loginLink = document.getElementById('navLoginBtn');
    const signupLink = document.getElementById('navSignupBtn');

    if (loginLink) {
        loginLink.addEventListener('click', (e) => {
            e.preventDefault();
            openAuthModal('login');
        });
    }

    if (signupLink) {
        signupLink.addEventListener('click', (e) => {
            e.preventDefault();
            openAuthModal('signup');
        });
    }

    // --- GLOBAL AUTH LINK INTERCEPTION ---
    // This allows ANY link on the page (footer, navbar, etc) to open the modal
    // instead of a full page reload if it points to an auth route.
    function attachGlobalAuthInterceptors() {
        document.addEventListener('click', function(e) {
            const link = e.target.closest('a');
            if (!link || !link.href) return;

            try {
                const url = new URL(link.href);
                // Only intercept internal links
                if (url.origin !== window.location.origin) return;

                const path = url.pathname;
                
                // Route mapping
                if (path === '/auth/login') {
                    e.preventDefault();
                    openAuthModal('login');
                } else if (path === '/auth/register/caterer') {
                    e.preventDefault();
                    openAuthModal('caterer-signup');
                } else if (path === '/auth/register') {
                    e.preventDefault();
                    openAuthModal('signup');
                } else if (path === '/auth/forgot-password') {
                    e.preventDefault();
                    openAuthModal('forgot');
                }
            } catch (err) {
                // Not a valid URL or other issue, ignore
            }
        });
    }

    // Modal internal link interception (for links ALREADY inside modals)
    function attachModalInternalInterceptors() {
        const modalContents = document.querySelectorAll('.auth-modal-content');
        modalContents.forEach(content => {
            const links = content.querySelectorAll('a');
            links.forEach(link => {
                // If the link is just a "#" but has internal logic, skip
                if (link.getAttribute('onclick') || link.getAttribute('href') === '#') return;
                
                link.addEventListener('click', (e) => {
                    const href = link.getAttribute('href') || '';
                    if (href === '/auth/login') {
                        e.preventDefault();
                        openAuthModal('login');
                    } else if (href === '/auth/register') {
                        e.preventDefault();
                        openAuthModal('signup');
                    } else if (href === '/auth/register/caterer') {
                        e.preventDefault();
                        openAuthModal('caterer-signup');
                    } else if (href === '/auth/forgot-password') {
                        e.preventDefault();
                        openAuthModal('forgot');
                    }
                });
            });
        });
    }

    // --- AJAX LOGIN HANDLER (Event Delegation) ---
    document.addEventListener('submit', async (e) => {
        // Find if the submission is from a login form
        const loginForm = e.target.closest('#loginForm');
        if (!loginForm) return;

        // Prevent normal form submission
        e.preventDefault();

        const submitBtn = loginForm.querySelector('.btn-primary-action');
        const errorContainer = document.getElementById('loginErrorContainer');
        const errorText = errorContainer ? errorContainer.querySelector('.error-message') : null;

        if (submitBtn) {
            submitBtn.disabled = true;
            const originalContent = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> <span>Logging in...</span>';
            submitBtn.dataset.originalContent = originalContent;
        }

        if (errorContainer) errorContainer.style.display = 'none';

        const formData = new FormData(loginForm);
        
        try {
            const response = await fetch('/auth/login', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                }
            });

            // Handle non-JSON responses (security/server errors)
            const contentType = response.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                throw new Error("Server returned non-JSON response");
            }

            const result = await response.json();

            if (response.ok && result.success) {
                // Success! Redirect to the dashboard
                window.location.href = result.redirect_url;
            } else {
                // Error! Show in modal
                if (errorContainer && errorText) {
                    errorText.textContent = result.error || 'An unexpected error occurred.';
                    errorContainer.style.display = 'block';
                    
                    // Simple show/hide for cleaner UX
                    errorContainer.style.animation = 'none';
                    errorContainer.offsetHeight; // trigger reflow
                    errorContainer.style.animation = 'fadeInError 0.3s ease';
                } else {
                    alert(result.error || 'Login failed');
                }
            }
        } catch (err) {
            console.error('Login error:', err);
            if (errorContainer && errorText) {
                errorText.textContent = 'Connection error or server issue. Please try again.';
                errorContainer.style.display = 'block';
            }
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = submitBtn.dataset.originalContent || 'Login';
            }
        }
    });

    // --- AJAX FORGOT PASSWORD HANDLER (Event Delegation) ---
    document.addEventListener('submit', async (e) => {
        const forgotForm = e.target.closest('#forgotForm');
        if (!forgotForm) return;

        e.preventDefault();

        const submitBtn = forgotForm.querySelector('button[type="submit"]');
        const successContainer = document.getElementById('forgotSuccessContainer');
        const successText = successContainer ? successContainer.querySelector('.success-message') : null;
        const errorContainer = document.getElementById('forgotErrorContainer');
        const errorText = errorContainer ? errorContainer.querySelector('.error-message') : null;

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.dataset.originalContent = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> <span>Sending link...</span>';
        }

        if (successContainer) successContainer.style.display = 'none';
        if (errorContainer) errorContainer.style.display = 'none';

        const formData = new FormData(forgotForm);

        try {
            const response = await fetch('/auth/forgot-password', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                }
            });

            const contentType = response.headers.get("content-type");
            let result = {};
            if (contentType && contentType.includes("application/json")) {
                result = await response.json();
            } else {
                result = { success: response.ok, message: "If your email is registered, you will receive a reset link shortly." };
            }

            if (response.ok && result.success) {
                const message = result.message || 'If your email is registered, you will receive a reset link shortly.';
                if (successContainer && successText) {
                    successText.textContent = message;
                    successContainer.style.display = 'flex';
                    successContainer.style.animation = 'none';
                    successContainer.offsetHeight; // trigger reflow
                    successContainer.style.animation = 'fadeInError 0.3s ease';
                }
                if (window.Swal) {
                    Swal.fire({
                        icon: 'success',
                        title: 'Email Sent!',
                        text: message,
                        confirmButtonColor: '#FF7B54'
                    });
                }
                const emailInput = forgotForm.querySelector('input[name="email"]');
                if (emailInput) emailInput.value = '';
            } else {
                const errMsg = result.error || result.message || 'Failed to send reset link. Please check your email.';
                if (errorContainer && errorText) {
                    errorText.textContent = errMsg;
                    errorContainer.style.display = 'flex';
                    errorContainer.style.animation = 'none';
                    errorContainer.offsetHeight; // trigger reflow
                    errorContainer.style.animation = 'fadeInError 0.3s ease';
                } else if (window.Swal) {
                    Swal.fire({
                        icon: 'error',
                        title: 'Error',
                        text: errMsg,
                        confirmButtonColor: '#FF7B54'
                    });
                } else {
                    alert(errMsg);
                }
            }
        } catch (err) {
            console.error('Forgot password error:', err);
            if (errorContainer && errorText) {
                errorText.textContent = 'Connection error or server issue. Please try again.';
                errorContainer.style.display = 'flex';
            }
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = submitBtn.dataset.originalContent || '<span>Send Reset Link</span> <i class="fas fa-paper-plane"></i>';
            }
        }
    });

    // Initialize Global interceptors
    attachGlobalAuthInterceptors();
    attachModalInternalInterceptors();

    // Auto-open from query parameter (New standard for redirects)
    const urlParams = new URLSearchParams(window.location.search);
    const authModalParam = urlParams.get('auth_modal');
    if (authModalParam) {
        const emailParam = urlParams.get('email');
        openAuthModal(authModalParam, emailParam);

        if (authModalParam === 'forgot') {
            if (urlParams.get('success')) {
                const sc = document.getElementById('forgotSuccessContainer');
                const st = sc ? sc.querySelector('.success-message') : null;
                if (sc && st) {
                    st.textContent = 'If your email is registered, you will receive a reset link shortly.';
                    sc.style.display = 'flex';
                }
            }
            if (urlParams.get('error')) {
                const ec = document.getElementById('forgotErrorContainer');
                const et = ec ? ec.querySelector('.error-message') : null;
                if (ec && et) {
                    et.textContent = 'Unable to send reset link. Please check your email address.';
                    ec.style.display = 'flex';
                }
            }
        }

        // Clear param from URL without refreshing to keep it clean
        const newUrl = window.location.pathname + window.location.hash;
        window.history.replaceState({}, document.title, newUrl);
    } else {
        // Fallback: Auto-open from hash (Legacy)
        if (window.location.hash === '#login') openAuthModal('login');
        else if (window.location.hash === '#signup') openAuthModal('signup');
        else if (window.location.hash === '#forgot') openAuthModal('forgot');
        else if (window.location.hash === '#verify') openAuthModal('verify');
        else if (window.location.hash === '#caterer-signup') openAuthModal('caterer-signup');
    }
});

// Export for global use
window.openAuthModal = openAuthModal;
window.closeAuthModal = closeAuthModal;

// --- DIAMOND STANDARD: SOCIAL LOGIN HANDLER ---
let isSocialLoggingIn = false;
window.handleSocialLogin = function (provider) {
    if (isSocialLoggingIn) return;
    isSocialLoggingIn = true;

    // Support both standard and premium button classes
    const btn = document.querySelector(`.btn-${provider}`) || document.querySelector(`.btn-${provider}-premium`);
    
    if (btn) {
        btn.style.opacity = '0.7';
        btn.style.cursor = 'wait';
        btn.style.pointerEvents = 'none';

        // Replace content with a loading spinner (works for both <i> and <svg> setups)
        btn.innerHTML = `<i class="fas fa-circle-notch fa-spin"></i> <span>Processing...</span>`;
    }

    // Direct redirection to backend OAuth route (Using /social prefix to avoid auth router conflicts)
    window.location.href = `/social/login/${provider}`;
};


window.togglePasswordVisibility = function (button) {
    const wrapper = button.parentElement;
    const input = wrapper.querySelector('input');
    const icon = button.querySelector('i');

    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
};
