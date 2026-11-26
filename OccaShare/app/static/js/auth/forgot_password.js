/**
 * Forgot Password Logic
 */
document.addEventListener('DOMContentLoaded', () => {
    const forgotForm = document.getElementById('forgotForm');
    if (forgotForm) {
        forgotForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const form = this;
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';

            const formData = new FormData(form);

            try {
                const response = await fetch('/auth/forgot-password', {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': 'application/json'
                    },
                    body: formData
                });

                const data = await response.json().catch(() => null);

                if (response.ok && (!data || data.success !== false)) {
                    const msg = (data && data.message) || 'Instructions to reset your password have been sent to your email.';
                    // If in modal, close it immediately
                    if (typeof closeAuthModal === 'function' && document.getElementById('authModalOverlay')?.classList.contains('active')) {
                        closeAuthModal();
                    }
                    if (window.showToast) {
                        window.showToast(msg, 'success');
                    } else if (window.Swal) {
                        Swal.mixin({
                            toast: true,
                            position: 'bottom-end',
                            showConfirmButton: false,
                            timer: 4000,
                            timerProgressBar: true
                        }).fire({
                            icon: 'success',
                            title: msg
                        });
                    }
                    if (!document.getElementById('authModalOverlay')) {
                        setTimeout(() => { window.location.href = '/auth/login'; }, 1500);
                    }
                } else {
                    const errMsg = (data && (data.error || data.message)) || 'We couldn\'t find an account with that email.';
                    if (window.Swal) {
                        Swal.fire({
                            icon: 'error',
                            title: 'Failed to Send',
                            text: errMsg,
                            confirmButtonColor: '#FF7B54'
                        });
                    } else {
                        alert(errMsg);
                    }
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnText;
                }
            } catch (error) {
                console.error('Forgot password error:', error);
                if (window.Swal) {
                    Swal.fire({
                        icon: 'error',
                        title: 'Connection Error',
                        text: 'Could not connect to the server. Please check your internet connection and try again.',
                        confirmButtonColor: '#FF7B54'
                    });
                }
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            }
        });
    }
});
