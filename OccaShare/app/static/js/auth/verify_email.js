// Countdown Timer & Polling Logic (5 Minutes = 300 Seconds)
window.verifyEmailTimerId = window.verifyEmailTimerId || null;
window.verifyEmailTimeLeft = window.verifyEmailTimeLeft || 300;
window.verifyPollingId = window.verifyPollingId || null;
window.isOtpSubmitting = false;
window.isOtpVerified = false;

function stopTimer() {
    if (window.verifyEmailTimerId) {
        clearInterval(window.verifyEmailTimerId);
        window.verifyEmailTimerId = null;
    }
}

function stopVerifyPolling() {
    if (window.verifyPollingId) {
        clearInterval(window.verifyPollingId);
        window.verifyPollingId = null;
    }
}

function startTimer() {
    window.verifyEmailTimeLeft = 300; // 5 minutes
    const btn = document.getElementById('resendBtn');
    const timer = document.getElementById('timer');
    const timerContainer = document.getElementById('timerContainer');

    // Hide the resend button while the countdown is running
    if (btn) {
        btn.style.display = 'none';
        btn.classList.add('disabled');
    }
    if (timer) {
        timer.textContent = "05:00";
    }
    if (timerContainer) {
        timerContainer.style.display = 'block';
    }

    stopTimer();
    window.verifyEmailTimerId = setInterval(() => {
        window.verifyEmailTimeLeft--;
        const curTimer = document.getElementById('timer');
        const curBtn = document.getElementById('resendBtn');
        const curTimerContainer = document.getElementById('timerContainer');

        if (window.verifyEmailTimeLeft <= 0) {
            stopTimer();
            // Time is up: hide countdown text and show clickable resend button
            if (curTimerContainer) {
                curTimerContainer.style.display = 'none';
            }
            if (curBtn) {
                curBtn.style.display = 'inline-block';
                curBtn.classList.remove('disabled');
                curBtn.textContent = "Resend Code";
            }
        } else {
            const minutes = Math.floor(window.verifyEmailTimeLeft / 60);
            const seconds = window.verifyEmailTimeLeft % 60;
            if (curTimer) {
                curTimer.textContent = `${minutes < 10 ? '0' : ''}${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
            }
        }
    }, 1000);
}

function resetTimer() {
    startTimer();
}

// Initial setup for standalone page only
document.addEventListener('DOMContentLoaded', () => {
    // Only run on the standalone page, not in the modal
    if (document.getElementById('verifyForm') && !document.getElementById('authModalOverlay')) {
        startTimer();
        initVerifyPolling();
    }
});

// Real-time Polling for Verification Status
async function initVerifyPolling() {
    stopVerifyPolling(); // Always clear previous polling to avoid duplicate intervals
    if (window.isOtpVerified) return;

    const emailField = document.getElementById('emailField');
    if (!emailField) return;
    const email = emailField.value;
    if (!email) return;

    window.verifyPollingId = setInterval(async () => {
        // Skip polling iteration if manual submit is currently in flight or completed
        if (window.isOtpSubmitting || window.isOtpVerified) return;

        try {
            const response = await fetch(`/auth/verify-status?email=${encodeURIComponent(email)}`);
            const result = await response.json();
            if (result.verified && !window.isOtpVerified) {
                window.isOtpVerified = true;
                stopVerifyPolling();
                stopTimer();

                if (window.showToast) {
                    window.showToast('Account Verified Successfully! Redirecting...', 'success');
                } else if (window.Swal) {
                    Swal.mixin({
                        toast: true,
                        position: 'bottom-end',
                        showConfirmButton: false,
                        timer: 1800,
                        timerProgressBar: true
                    }).fire({
                        icon: 'success',
                        title: 'Account Verified Successfully!'
                    });
                }
                const roleBasedFallback = (result && result.role === 'caterer') ? '/caterer/dashboard' : '/customer/dashboard';
                const nextUrl = (result && result.redirect) || document.querySelector('input[name="next_url"]')?.value || roleBasedFallback;
                setTimeout(() => { window.location.href = nextUrl; }, 1200);
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 3000);
}

// Resend Code Logic
async function resendCode(e) {
    if (e) e.preventDefault();
    const btn = document.getElementById('resendBtn');
    if (!btn || btn.classList.contains('disabled')) return;

    const email = document.getElementById('emailField')?.value;
    if (!email) {
        if (window.Swal) Swal.fire({ icon: 'error', title: 'Error', text: 'Email not found. Please register again.', confirmButtonColor: '#FF7B54' });
        return;
    }

    btn.textContent = "Sending...";
    btn.classList.add('disabled');

    try {
        const formData = new FormData();
        formData.append('email', email);

        const response = await fetch('/auth/resend-code', {
            method: 'POST',
            body: formData
        });

        let result;
        try {
            result = await response.json();
        } catch (_) {
            // Server returned a non-JSON response (e.g. 500 HTML page)
            throw new Error(`Server error (${response.status}). Please restart the server and try again.`);
        }

        if (result.success) {
            if (window.showToast) {
                window.showToast('A fresh verification code has been sent to your email.', 'success');
            } else if (window.Swal) {
                Swal.mixin({
                    toast: true,
                    position: 'bottom-end',
                    showConfirmButton: false,
                    timer: 2500,
                    timerProgressBar: true
                }).fire({
                    icon: 'success',
                    title: 'New Code Sent to your inbox!'
                });
            }
            // Clear boxes and focus first
            const otpBoxes = document.querySelectorAll('.otp-box');
            otpBoxes.forEach(b => {
                b.value = '';
                b.style.borderColor = '';
            });
            const hiddenCode = document.getElementById('code');
            if (hiddenCode) hiddenCode.value = '';
            otpBoxes[0]?.focus();

            window.isOtpSubmitting = false;
            window.isOtpVerified = false;
            const verifyForm = document.getElementById('verifyForm');
            if (verifyForm) verifyForm.dataset.submitting = 'false';

            resetTimer();
            initVerifyPolling();
        } else {
            if (window.Swal) {
                Swal.fire({
                    icon: 'error',
                    title: 'Failed to Send',
                    text: result.message || 'Failed to resend code. Please try again.',
                    confirmButtonColor: '#FF7B54'
                });
            }
            btn.classList.remove('disabled');
            btn.textContent = "Resend Code";
        }
    } catch (error) {
        console.error('Resend error:', error);
        if (window.Swal) {
            Swal.fire({
                icon: 'error',
                title: 'Connection Error',
                text: error.message || 'Could not reach the server. Please check your connection and try again.',
                confirmButtonColor: '#FF7B54'
            });
        }
        if (btn) {
            btn.classList.remove('disabled');
            btn.textContent = "Resend Code";
        }
    }
}

// Auto-submit OTP form when 6 digits are typed or pasted
function setupOtpInputListeners() {
    const verifyForm = document.getElementById('verifyForm');
    if (!verifyForm) return;
    if (verifyForm.dataset.otpListenersBound === 'true') return;
    verifyForm.dataset.otpListenersBound = 'true';

    const otpBoxes = document.querySelectorAll('.otp-box');
    const hiddenCode = document.getElementById('code');
    if (!otpBoxes.length || !hiddenCode) return;

    function updateCodeAndCheckAutoSubmit() {
        let code = '';
        otpBoxes.forEach(b => code += b.value.trim());
        hiddenCode.value = code;

        if (code.length === 6 && /^\d{6}$/.test(code)) {
            submitOtpForm();
        }
    }

    otpBoxes[0]?.focus();

    otpBoxes.forEach((box, index) => {
        box.addEventListener('input', (e) => {
            const val = e.target.value;
            if (val.length === 1 && index < otpBoxes.length - 1) {
                otpBoxes[index + 1].focus();
            }
            updateCodeAndCheckAutoSubmit();
        });

        box.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' && !e.target.value && index > 0) {
                otpBoxes[index - 1].focus();
            }
        });

        box.addEventListener('paste', (e) => {
            e.preventDefault();
            const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
            if (pastedData) {
                pastedData.split('').forEach((char, i) => {
                    if (otpBoxes[i]) {
                        otpBoxes[i].value = char;
                        if (i < otpBoxes.length - 1) otpBoxes[i + 1].focus();
                    }
                });
                updateCodeAndCheckAutoSubmit();
            }
        });
    });
}

async function submitOtpForm() {
    const verifyForm = document.getElementById('verifyForm');
    if (!verifyForm || window.isOtpSubmitting || window.isOtpVerified) return;

    const hiddenCode = document.getElementById('code');
    if (!hiddenCode || !hiddenCode.value || hiddenCode.value.length < 6) {
        if (window.Swal) {
            Swal.fire({
                icon: 'warning',
                title: 'Incomplete Code',
                text: 'Please enter all 6 digits of the verification code.',
                confirmButtonColor: '#FF7B54'
            });
        }
        return;
    }

    // Immediately stop background polling to prevent race conditions
    stopVerifyPolling();
    window.isOtpSubmitting = true;
    verifyForm.dataset.submitting = 'true';

    // Real-time animated loading popup
    if (window.Swal) {
        Swal.fire({
            title: 'Verifying Security Code...',
            html: '<div style="margin-top: 10px; color: #64748b; font-size: 0.95rem;">Authenticating your session & logging you in...</div>',
            allowOutsideClick: false,
            allowEscapeKey: false,
            showConfirmButton: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });
    }

    const formData = new FormData(verifyForm);

    try {
        const response = await fetch('/auth/verify', {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            },
            body: formData
        });

        const data = await response.json().catch(() => null);

        if (response.ok && data && data.success) {
            window.isOtpVerified = true;
            stopTimer();

            if (window.Swal && Swal.isVisible()) {
                Swal.close();
            }

            if (window.showToast) {
                window.showToast(data.message || 'Verification Successful! Redirecting...', 'success');
            } else if (window.Swal) {
                Swal.mixin({
                    toast: true,
                    position: 'bottom-end',
                    showConfirmButton: false,
                    timer: 1800,
                    timerProgressBar: true
                }).fire({
                    icon: 'success',
                    title: 'Verification Successful!'
                });
            }
            const roleBasedFallback = (data && data.role === 'caterer') ? '/caterer/dashboard' : '/customer/dashboard';
            const targetUrl = (data && data.redirect) || document.querySelector('input[name="next_url"]')?.value || roleBasedFallback;
            setTimeout(() => { window.location.href = targetUrl; }, 1200);
        } else {
            window.isOtpSubmitting = false;
            verifyForm.dataset.submitting = 'false';

            const defaultErr = (!response.ok && response.status >= 500)
                ? 'Server error occurred during verification. Please try again.'
                : 'Invalid verification code. Please check and try again.';
            const errMsg = (data && (data.message || data.detail)) || defaultErr;

            if (window.Swal) {
                Swal.fire({
                    icon: 'error',
                    title: 'Verification Failed',
                    text: errMsg,
                    confirmButtonColor: '#FF7B54'
                });
            } else {
                alert(errMsg);
            }

            // Highlight error and clear inputs
            const otpBoxes = document.querySelectorAll('.otp-box');
            otpBoxes.forEach(b => {
                b.value = '';
                b.style.borderColor = '#ef4444';
                setTimeout(() => { b.style.borderColor = ''; }, 2000);
            });
            if (hiddenCode) hiddenCode.value = '';
            otpBoxes[0]?.focus();

            // Resume polling in case user verifies through a different tab
            initVerifyPolling();
        }
    } catch (error) {
        console.error('Error verifying OTP:', error);
        window.isOtpSubmitting = false;
        verifyForm.dataset.submitting = 'false';

        if (window.Swal) {
            Swal.fire({
                icon: 'error',
                title: 'Connection Error',
                text: 'An unexpected connection error occurred. Please check your connection and try again.',
                confirmButtonColor: '#FF7B54'
            });
        }
        initVerifyPolling();
    }
}

// Handle Form Submit
document.addEventListener('DOMContentLoaded', () => {
    setupOtpInputListeners();

    const verifyForm = document.getElementById('verifyForm');
    if (verifyForm && verifyForm.dataset.formSubmitBound !== 'true') {
        verifyForm.dataset.formSubmitBound = 'true';
        verifyForm.addEventListener('submit', function (e) {
            e.preventDefault();
            submitOtpForm();
        });
    }
});

// Export for global use
window.startTimer = startTimer;
window.resetTimer = resetTimer;
window.stopTimer = stopTimer;
window.resendCode = resendCode;
window.initVerifyPolling = initVerifyPolling;
window.stopVerifyPolling = stopVerifyPolling;
window.submitOtpForm = submitOtpForm;
window.setupOtpInputListeners = setupOtpInputListeners;

