(function () {
    const urlParams = new URLSearchParams(window.location.search);

    if (urlParams.get('verified') === 'true') {
        Swal.fire({ icon: 'success', title: 'Email successfully verified!', text: 'You can now log in to your account.', confirmButtonColor: '#FF7B54' });
    }

    if (urlParams.get('success') === 'password_reset') {
        Swal.fire({ icon: 'success', title: 'Password Updated!', text: 'Your password has been reset successfully. Please log in with your new password.', confirmButtonColor: '#FF7B54' });
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
    }

    if (urlParams.get('error') === 'config_missing') {
        const provider = urlParams.get('provider') || 'This provider';
        Swal.fire({ 
            icon: 'warning', 
            title: 'Not Configured', 
            text: `${provider} login is not yet set up for this environment.`,
            confirmButtonColor: '#FF7B54' 
        });
    }

    }
})();
