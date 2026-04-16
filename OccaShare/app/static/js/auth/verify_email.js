// Countdown Timer Logic
let timeLeft = 180; // 3 minutes
const timerElement = document.getElementById('timer');
const resendBtn = document.getElementById('resendBtn');
let timerId;

function startTimer() {
    timeLeft = 60;
    if (resendBtn) {
        resendBtn.classList.add('disabled');
        resendBtn.textContent = "Resend Code";
    }

    clearInterval(timerId);
    timerId = setInterval(() => {
        if (timeLeft <= 0) {
            clearInterval(timerId);
            if (timerElement) timerElement.textContent = "00:00";
            if (resendBtn) resendBtn.classList.remove('disabled');
        } else {
            timeLeft--;
            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;
            if (timerElement) {
                timerElement.textContent = `${minutes < 10 ? '0' : ''}${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
            }
        }
    }, 1000);
}

function resetTimer() {
    timeLeft = 180;
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
                const nextUrl = document.querySelector('input[name="next_url"]')?.value || '/customer/dashboard';
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
    if (!resendBtn || resendBtn.classList.contains('disabled')) return;

    const email = document.getElementById('emailField')?.value;
    if (!email) return;

    resendBtn.textContent = "Sending...";
    resendBtn.classList.add('disabled');

    try {
        const formData = new FormData();
        formData.append('email', email);

        const response = await fetch('/auth/resend-code', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

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
                    title: 'Oops...',
                    text: result.message || 'Failed to resend code.',
                    confirmButtonColor: '#FF7B54'
                });
            }
            resendBtn.classList.remove('disabled');
            resendBtn.textContent = "Resend Code";
        }
    } catch (error) {
        console.error('Error:', error);
        if (resendBtn) {
            resendBtn.classList.remove('disabled');
            resendBtn.textContent = "Resend Code";
        }
    }
}

// Handle Form Submit for Floating Success
document.addEventListener('DOMContentLoaded', () => {
    const verifyForm = document.getElementById('verifyForm');
    if (verifyForm) {
        verifyForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const form = this;
            const formData = new FormData(form);

            try {
                const response = await fetch('/auth/verify', {
                    method: 'POST',
                    body: formData
                });

                if (response.redirected) {
                    if (response.url.includes('verified=true')) {
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
                    }
                    window.location.href = response.url;
                } else {
                    const text = await response.text();
                    const textLower = text.toLowerCase();
                    if (textLower.includes('expired')) {
                        if (window.Swal) {
                            Swal.fire({ icon: 'error', title: 'Code Expired', text: 'Please request a new one.', confirmButtonColor: '#FF7B54' });
                        }
                    } else if (textLower.includes('invalid')) {
                        if (window.Swal) {
                            Swal.fire({ icon: 'error', title: 'Invalid Code', text: 'Please check and try again.', confirmButtonColor: '#FF7B54' });
                        }
                    } else {
                        form.submit();
                    }
                }
            } catch (error) {
                form.submit();
            }
        });
    }
});

// Export for global use
window.startTimer = startTimer;
window.resendCode = resendCode;
window.initVerifyPolling = initVerifyPolling;

