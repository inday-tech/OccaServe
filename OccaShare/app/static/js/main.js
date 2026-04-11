// --- 1. Global UI Utilities & Real-Time Feedback ---
document.addEventListener('DOMContentLoaded', function() {
    // A. Smooth Scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    // B. Global Button Loading States
    // Automatically adds a loading spinner to buttons when clicked if they are likely to trigger an action
    document.querySelectorAll('.btn-primary, .btn-secondary, .btn-wizard-next, .package-card-btn').forEach(btn => {
        if (btn.type === 'submit' || btn.classList.contains('js-loading')) {
            btn.addEventListener('click', function(e) {
                const originalContent = this.innerHTML;
                const form = this.closest('form');
                
                // Only show loading if form is valid or no form exists
                if (!form || form.checkValidity()) {
                    // Small delay before disabling to allow the browser to trigger form submission
                    // Disabling immediately can cancel the submit event in some browsers/versions
                    const btnElement = this;
                    
                    setTimeout(() => {
                        btnElement.classList.add('is-loading');
                        btnElement.disabled = true;
                        btnElement.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Processing...`;
                    }, 50);
                    
                    // Cleanup if page doesn't navigate (e.g. AJAX or validation error or slow network)
                    setTimeout(() => {
                        if (btnElement.disabled && btnElement.innerHTML.includes('fa-spinner')) {
                             btnElement.innerHTML = originalContent;
                             btnElement.disabled = false;
                             btnElement.classList.remove('is-loading');
                        }
                    }, 10000); // 10s timeout
                }
            });
        }
    });

    // C. Micro-animations for Hover Elements
    const hoverElements = document.querySelectorAll('.card, .stat-card, .sidebar-link, .package-card');
    hoverElements.forEach(el => {
        el.addEventListener('mouseenter', () => el.classList.add('js-hover-pulse'));
        el.addEventListener('mouseleave', () => el.classList.remove('js-hover-pulse'));
    });

    // D. Navigation Highlight Synchronization
    // Ensures current page link is always active across different browser states
    const normalizePath = (p) => p.replace(/\/$/, '') || '/';
    const currentPath = normalizePath(window.location.pathname);
    
    document.querySelectorAll('.sidebar-menu a').forEach(link => {
        const linkPath = normalizePath(link.getAttribute('href') || '');
        if (linkPath === currentPath) {
            link.classList.add('active');
        } else {
            // Check if it's a sub-path
            if (currentPath.startsWith(linkPath) && linkPath !== '/') {
                link.classList.add('active');
            }
        }
    });
});

// --- 2. Global Event Bus for Real-Time Updates ---
window.OccaEvents = {
    subscribers: {},
    subscribe(event, callback) {
        if (!this.subscribers[event]) this.subscribers[event] = [];
        this.subscribers[event].push(callback);
    },
    publish(event, data) {
        if (!this.subscribers[event]) return;
        this.subscribers[event].forEach(cb => cb(data));
    }
};

// --- 3. Global Toast System (SweetAlert2) ---
window.showToast = function(message, icon = 'info') {
    const Toast = Swal.mixin({
        toast: true,
        position: 'bottom-end', // User requested right bottom
        showConfirmButton: false,
        timer: 3500,
        timerProgressBar: true,
        didOpen: (toast) => {
            toast.addEventListener('mouseenter', Swal.stopTimer)
            toast.addEventListener('mouseleave', Swal.resumeTimer)
        }
    });

    Toast.fire({
        icon: icon,
        title: message
    });
};

// --- 4. Global URL Parameter Listener for Toasts ---
document.addEventListener('DOMContentLoaded', function() {
    // Check both search params and hash (in case params are after the #)
    const getParam = (name) => {
        const searchParams = new URLSearchParams(window.location.search);
        if (searchParams.has(name)) return searchParams.get(name);
        
        const hashParams = new URLSearchParams(window.location.hash.includes('?') ? window.location.hash.split('?')[1] : '');
        return hashParams.get(name);
    };

    let shouldClean = false;
    const loginStatus = getParam('login');
    const logoutStatus = getParam('logout');
    const successMsg = getParam('success_msg');
    const errorMsg = getParam('error_msg');
    const alertMsg = getParam('alert_msg');

    if (loginStatus === 'success') {
        window.showToast('Login Successful! Welcome back.', 'success');
        shouldClean = true;
    } else if (logoutStatus === 'success') {
        window.showToast('Logout Successful! See you soon.', 'success');
        shouldClean = true;
    }

    if (successMsg) {
        window.showToast(decodeURIComponent(successMsg), 'success');
        shouldClean = true;
    }
    
    if (errorMsg) {
        window.showToast(decodeURIComponent(errorMsg), 'error');
        shouldClean = true;
    }

    if (alertMsg && window.showAlert) {
        window.showAlert({
            title: 'Message',
            message: decodeURIComponent(alertMsg),
            type: 'info'
        });
        shouldClean = true;
    }

    // Cleanup URL parameters to prevent toast from showing again on refresh
    if (shouldClean) {
        const url = new URL(window.location.href);
        url.searchParams.delete('login');
        url.searchParams.delete('logout');
        url.searchParams.delete('success_msg');
        url.searchParams.delete('error_msg');
        url.searchParams.delete('alert_msg');
        window.history.replaceState({}, document.title, url.pathname + url.search + url.hash);
    }
});
