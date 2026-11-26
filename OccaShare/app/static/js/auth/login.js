(function () {
    const urlParams = new URLSearchParams(window.location.search);
    let shouldCleanUrl = false;

    if (urlParams.get('verified') === 'true' || urlParams.get('verified') === 'success') {
        if (window.showToast) {
            window.showToast('Account verified successfully! You can now log in.', 'success');
        } else if (window.Swal) {
            Swal.mixin({
                toast: true,
                position: 'bottom-end',
                showConfirmButton: false,
                timer: 4000,
                timerProgressBar: true
            }).fire({
                icon: 'success',
                title: 'Account verified successfully! You can now log in.'
            });
        }
        shouldCleanUrl = true;
    }

    if (urlParams.get('success') === 'password_reset') {
        if (window.showToast) {
            window.showToast('Password updated successfully! Please log in.', 'success');
        } else if (window.Swal) {
            Swal.mixin({
                toast: true,
                position: 'bottom-end',
                showConfirmButton: false,
                timer: 4000,
                timerProgressBar: true
            }).fire({
                icon: 'success',
                title: 'Password updated successfully! Please log in.'
            });
        }
        shouldCleanUrl = true;
    }

    // Handle OAuth Errors
    if (urlParams.get('error') === 'oauth_failed') {
        const details = urlParams.get('details') || 'Authentication failed';
        Swal.fire({ 
            icon: 'error', 
            title: 'Login Failed', 
            text: `There was a problem: ${details}. Please try again or use your email.`,
            confirmButtonColor: '#FF7B54' 
        });
        shouldCleanUrl = true;
    }

    if (urlParams.get('error') === 'config_missing') {
        const provider = urlParams.get('provider') || 'This provider';
        Swal.fire({ 
            icon: 'warning', 
            title: 'Not Configured', 
            text: `${provider} login is not yet set up for this environment.`,
            confirmButtonColor: '#FF7B54' 
        });
        shouldCleanUrl = true;
    }

    if (shouldCleanUrl) {
        window.history.replaceState({}, document.title, window.location.pathname);
    }
})();
