/**
 * Admin Layout Functionality
 * Handles sidebar interactions and inactivity auto-logout
 */
(function () {
    // ─── Inactivity Auto-Logout ──────────────────────────────────────────────
    let timeoutLength = 30 * 60 * 1000; // 30 minutes for Admin
    let warningLength = 29 * 60 * 1000; // 29 minutes
    let inactivityTimeout;
    let warningTimeout;

    const modal = document.getElementById('inactivityModal');
    const stayBtn = document.getElementById('stayLoggedInBtn');

    function resetTimer() {
        if (modal && modal.style.display === 'flex') return;

        clearTimeout(inactivityTimeout);
        clearTimeout(warningTimeout);

        warningTimeout = setTimeout(function () {
            if (modal) modal.style.display = 'flex';
        }, warningLength);

        inactivityTimeout = setTimeout(function () {
            window.location.href = "/auth/logout?reason=inactivity";
        }, timeoutLength);
    }

    if (stayBtn) {
        stayBtn.addEventListener('click', function () {
            if (modal) modal.style.display = 'none';
            resetTimer();
        });
    }

    // Start timer on load and reset on activity
    ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(evt => {
        document.addEventListener(evt, resetTimer, { passive: true });
    });
    resetTimer();


    // ─── Sidebar Toggle Functionality ─────────────────────────────────────────
    const sidebar = document.getElementById('mainSidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const burgerBtn = document.getElementById('burgerBtn');
    const topbar = document.getElementById('mobileTopbar');

    // ─── Sidebar Scroll Persistence & Visibility ──────────────────────────────
    if (sidebar) {
        // Restore scroll position
        const savedScrollPos = localStorage.getItem('adminSidebarScrollTop');
        if (savedScrollPos) {
            sidebar.scrollTop = parseInt(savedScrollPos, 10);
        }

        // Capture scroll events to save position (debounced for performance)
        let scrollTimeout;
        sidebar.addEventListener('scroll', function() {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                localStorage.setItem('adminSidebarScrollTop', sidebar.scrollTop);
            }, 100);
        }, { passive: true });

        // Ensure active item is visible on load
        const activeItem = sidebar.querySelector('.sidebar-menu a.active');
        if (activeItem) {
            // Only scroll into view if not already visible
            const rect = activeItem.getBoundingClientRect();
            const sidebarRect = sidebar.getBoundingClientRect();
            if (rect.bottom > sidebarRect.bottom || rect.top < sidebarRect.top) {
                activeItem.scrollIntoView({ behavior: 'auto', block: 'nearest' });
            }
        }
    }

    window.toggleSidebar = function () {
        if (!sidebar) return;
        const isOpen = sidebar.classList.contains('sidebar-open');
        if (isOpen) {
            closeSidebar();
        } else {
            openSidebar();
        }
    };

    window.openSidebar = function () {
        if (!sidebar) return;
        sidebar.classList.add('sidebar-open');
        if (overlay) overlay.classList.add('active');
        if (topbar) topbar.classList.add('burger-open');
        document.body.style.overflow = 'hidden'; 
    };

    window.closeSidebar = function () {
        if (!sidebar) return;
        if (window.innerWidth > 768) return;
        sidebar.classList.remove('sidebar-open');
        if (overlay) overlay.classList.remove('active');
        if (topbar) topbar.classList.remove('burger-open');
        document.body.style.overflow = '';
    };

    const desktopToggleBtn = document.getElementById('desktopToggleBtn');
    if (desktopToggleBtn) {
        desktopToggleBtn.addEventListener('click', function () {
            const wrapper = document.querySelector('.dashboard-wrapper');
            if (wrapper) {
                wrapper.classList.toggle('sidebar-icons-only');
                const isCollapsed = wrapper.classList.contains('sidebar-icons-only');
                localStorage.setItem('adminSidebarCollapsed', isCollapsed ? 'true' : 'false');
                window.dispatchEvent(new Event('resize'));
                setTimeout(() => window.dispatchEvent(new Event('resize')), 310);
            }
        });
    }

    // ─── SweetAlert2 Interceptors ─────────────────────────────────────────────
    const actionForms = document.querySelectorAll('form[action*="/status"]:not([onsubmit]), form[action*="/delete"]:not([onsubmit])');
    actionForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();

            const isDelete = this.action.includes('/delete');
            const isActivate = this.querySelector('.activate') !== null;

            let title = 'Are you sure?';
            let text = 'You are about to change this account\'s status.';
            let confirmButtonColor = '#FF7B54'; // Brand Orange
            let confirmText = 'Yes, proceed';

            if (isDelete) {
                title = 'Permanently Delete Account?';
                text = 'This action CANNOT be undone. All data will be lost forever.';
                confirmText = 'Yes, Delete it!';
            } else if (isActivate) {
                title = 'Activate Account?';
                text = 'This user will regain access to the platform.';
                confirmText = 'Yes, Activate';
            }

            if (window.showConfirm) {
                window.showConfirm(text, () => this.submit(), title, confirmText);
            } else {
                this.submit();
            }
        });
    });

    const logoutBtn = document.querySelector('.logout-link');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function (e) {
            e.preventDefault();
            const href = this.getAttribute('href');

            if (window.showConfirm) {
                window.showConfirm(
                    'Are you sure you want to log out of the Admin panel?',
                    () => { window.location.href = href; },
                    'Ready to leave?',
                    'Yes, log out'
                );
            } else {
                window.location.href = href;
            }
        });
    }
})();
