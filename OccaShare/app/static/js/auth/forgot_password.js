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
                    body: formData
                });

                if (response.ok) {
                    if (window.Swal) {
                        await Swal.fire({
                            icon: 'success',
                            title: 'Email Sent!',
                            text: 'Instructions to reset your password have been sent to your email.',
                            confirmButtonColor: '#FF7B54'
                        });
                    } else {
                        alert('Reset link sent!');
                    }
                    // If in modal, maybe close it or show success state
                    if (typeof closeAuthModal === 'function' && document.getElementById('authModalOverlay')?.classList.contains('active')) {
                        closeAuthModal();
                    } else {
                        window.location.href = '/auth/login';
                    }
                } else {
                    const result = await response.text();
                    if (window.Swal) {
                        Swal.fire({
                            icon: 'error',
                            title: 'Failed',
                            text: 'We couldn\'t find an account with that email.',
                            confirmButtonColor: '#FF7B54'
                        });
                    } else {
                        alert('Email not found.');
                    }
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnText;
                }
            } catch (error) {
                console.error('Forgot password error:', error);
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            }
        });
    }
});
