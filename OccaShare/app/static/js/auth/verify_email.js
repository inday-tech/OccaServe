// Countdown Timer Logic (5 Minutes = 300 Seconds)
let timerId;
let timeLeft = 300;

function startTimer() {
    timeLeft = 300; // 5 minutes
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

    clearInterval(timerId);
    timerId = setInterval(() => {
        timeLeft--;
        const curTimer = document.getElementById('timer');
        const curBtn = document.getElementById('resendBtn');
        const curTimerContainer = document.getElementById('timerContainer');

        if (timeLeft <= 0) {
            clearInterval(timerId);
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
            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;
            if (curTimer) {
                curTimer.textContent = `${minutes < 10 ? '0' : ''}${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
            }
        }
    }, 1000);
}

function resetTimer() {
    startTimer();
}

// REMOVED automatic window.onload Swal alert to prevent premature alerts.
// Alerts are now triggered explicitly by the registration components.

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
    const emailField = document.getElementById('emailField');
    if (!emailField) return;
    const email = emailField.value;
    if (!email) return;

    let pollingId = setInterval(async () => {
        try {
            const response = await fetch(`/auth/verify-status?email=${encodeURIComponent(email)}`);
            const result = await response.json();
            if (result.verified) {
                clearInterval(pollingId);
                if (window.Swal) {
                    await Swal.fire({
                        icon: 'success',
                        title: 'Email successfully verified!',
                        text: 'You will be redirected shortly.',
                        timer: 2000,
                        showConfirmButton: false,
                        confirmButtonColor: '#FF7B54'
                    });
                }
                const roleBasedFallback = (result && result.role === 'caterer') ? '/caterer/dashboard' : '/customer/dashboard';
                const nextUrl = (result && result.redirect) || document.querySelector('input[name="next_url"]')?.value || roleBasedFallback;
                window.location.href = nextUrl;
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
            if (window.Swal) {
                Swal.fire({
                    icon: 'success',
                    title: 'Email Sent!',
                    text: 'A new verification code has been sent to your inbox.',
                    timer: 2000,
                    showConfirmButton: false,
                    confirmButtonColor: '#FF7B54'
                });
            }
            resetTimer();
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
    const otpBoxes = document.querySelectorAll('.otp-box');
    const hiddenCode = document.getElementById('code');
    const verifyForm = document.getElementById('verifyForm');
    if (!otpBoxes.length || !hiddenCode || !verifyForm) return;

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
    if (!verifyForm || verifyForm.dataset.submitting === 'true') return;

    const hiddenCode = document.getElementById('code');
    if (!hiddenCode || !hiddenCode.value || hiddenCode.value.length < 6) {
        if (window.Swal) {
            Swal.fire({
                icon: 'warning',
                title: 'Incomplete OTP',
                text: 'Please enter all 6 digits of the verification code.',
                confirmButtonColor: '#FF7B54'
            });
        }
        return;
    }

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
            if (window.Swal) {
                await Swal.fire({
                    icon: 'success',
                    title: 'Verification Successful!',
                    text: data.message || 'Identity verified! Redirecting to your dashboard...',
                    timer: 1200,
                    showConfirmButton: false,
                    confirmButtonColor: '#FF7B54'
                });
            }
            const roleBasedFallback = (data && data.role === 'caterer') ? '/caterer/dashboard' : '/customer/dashboard';
            const targetUrl = (data && data.redirect) || document.querySelector('input[name="next_url"]')?.value || roleBasedFallback;
            window.location.href = targetUrl;
        } else {
            verifyForm.dataset.submitting = 'false';
            const defaultErr = (!response.ok && response.status >= 500) ? 'Server error occurred during verification. Please try again.' : 'Invalid verification code. Please check and try again.';
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
            // Clear boxes on error
            const otpBoxes = document.querySelectorAll('.otp-box');
            otpBoxes.forEach(b => b.value = '');
            if (hiddenCode) hiddenCode.value = '';
            otpBoxes[0]?.focus();
        }
    } catch (error) {
        console.error('Error verifying OTP:', error);
        verifyForm.dataset.submitting = 'false';
        if (window.Swal) {
            Swal.fire({
                icon: 'error',
                title: 'Connection Error',
                text: 'An unexpected connection error occurred. Please try again.',
                confirmButtonColor: '#FF7B54'
            });
        }
    }
}

// Handle Form Submit
document.addEventListener('DOMContentLoaded', () => {
    setupOtpInputListeners();

    const verifyForm = document.getElementById('verifyForm');
    if (verifyForm) {
        verifyForm.addEventListener('submit', function (e) {
            e.preventDefault();
            submitOtpForm();
        });
    }
});

// Export for global use
window.startTimer = startTimer;
window.resendCode = resendCode;
window.initVerifyPolling = initVerifyPolling;
window.submitOtpForm = submitOtpForm;
window.setupOtpInputListeners = setupOtpInputListeners;

