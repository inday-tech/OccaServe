/**
 * Admin Layout v3 - Diamond Standard
 * Sidebar toggle, inactivity logout, desktop collapse
 */
(function () {

    // ─── Element References ───────────────────────────────────────────────────
    const sidebar   = document.getElementById('mainSidebar');
    const overlay   = document.getElementById('sidebarOverlay');
    const burgerBtn = document.getElementById('burgerBtn');
    const collapseBtn = document.getElementById('desktopToggleBtn');
    const htmlEl    = document.documentElement;

    // Search References
    const searchInput = document.getElementById('globalSearchInput');
    const searchPanel = document.getElementById('omniSearchResults');
    const searchScroller = document.getElementById('searchResultsScroller');
    let searchTimeout;

    // ─── Sidebar Scroll Persistence ───────────────────────────────────────────
    if (sidebar) {
        const nav = sidebar.querySelector('.sidebar-nav');
        if (nav) {
            const saved = localStorage.getItem('adminSidebarScrollTop');
            if (saved) nav.scrollTop = parseInt(saved, 10);
            let st;
            nav.addEventListener('scroll', () => {
                clearTimeout(st);
                st = setTimeout(() => localStorage.setItem('adminSidebarScrollTop', nav.scrollTop), 100);
            }, { passive: true });
        }

        // Scroll active nav item into view
        const activeItem = sidebar.querySelector('.nav-item.active');
        if (activeItem) {
            activeItem.scrollIntoView({ behavior: 'auto', block: 'nearest' });
        }
    }

    // ─── Mobile Sidebar: open / close ────────────────────────────────────────
    window.openSidebar = function () {
        if (!sidebar) return;
        sidebar.classList.add('active');
        if (overlay) overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    };

    window.closeSidebar = function () {
        if (!sidebar) return;
        sidebar.classList.remove('active');
        if (overlay) overlay.classList.remove('active');
        document.body.style.overflow = '';
    };

    window.toggleSidebar = function () {
        if (!sidebar) return;
        sidebar.classList.contains('active') ? window.closeSidebar() : window.openSidebar();
    };

    // Burger button click
    if (burgerBtn) {
        burgerBtn.addEventListener('click', window.toggleSidebar);
    }

    // Overlay click closes sidebar
    if (overlay) {
        overlay.addEventListener('click', window.closeSidebar);
    }

    // ─── Desktop Collapse Toggle ──────────────────────────────────────────────
    if (collapseBtn) {
        collapseBtn.addEventListener('click', function () {
            const isCollapsed = htmlEl.classList.toggle('sidebar-icons-only');
            localStorage.setItem('adminSidebarCollapsed', isCollapsed ? 'true' : 'false');
            // Trigger resize so charts re-paint
            window.dispatchEvent(new Event('resize'));
            setTimeout(() => window.dispatchEvent(new Event('resize')), 320);
        });
    }

    // Restore collapse state on load (already done inline, but enforce here too)
    if (localStorage.getItem('adminSidebarCollapsed') === 'true') {
        htmlEl.classList.add('sidebar-icons-only');
    }

    // ─── Logout Confirmation ──────────────────────────────────────────────────
    const logoutLink = document.querySelector('.nav-logout');
    if (logoutLink) {
        logoutLink.addEventListener('click', function (e) {
            e.preventDefault();
            const href = this.getAttribute('href');
            if (window.showConfirm) {
                window.showConfirm(
                    'Are you sure you want to log out of the Admin panel?',
                    () => { window.location.href = href; },
                    'Ready to leave?'
                );
            } else {
                window.location.href = href;
            }
        });
    }

    // ─── Inactivity Auto-Logout ───────────────────────────────────────────────
    const WARN_MS    = 29 * 60 * 1000;  // 29 min
    const LOGOUT_MS  = 30 * 60 * 1000; // 30 min
    const modal      = document.getElementById('inactivityModal');
    const stayBtn    = document.getElementById('stayLoggedInBtn');
    let warnTimer, logoutTimer;

    function resetInactivity() {
        if (modal && modal.style.display === 'flex') return;
        clearTimeout(warnTimer);
        clearTimeout(logoutTimer);
        warnTimer   = setTimeout(() => { if (modal) modal.style.display = 'flex'; }, WARN_MS);
        logoutTimer = setTimeout(() => { window.location.href = '/auth/logout?reason=inactivity'; }, LOGOUT_MS);
    }

    if (stayBtn) {
        stayBtn.addEventListener('click', () => {
            if (modal) modal.style.display = 'none';
            resetInactivity();
        });
    }

    ['mousedown', 'keypress', 'scroll', 'touchstart'].forEach(evt =>
        document.addEventListener(evt, resetInactivity, { passive: true })
    );
    resetInactivity();

    // ─── Header Dropdown Management ───────────────────────────────────────────
    window.toggleHeaderDropdown = function (dropdownId, triggerEl) {
        const dropdown = document.getElementById(dropdownId);
        if (!dropdown) return;

        const isActive = dropdown.classList.contains('active');
        closeAllHeaderDropdowns();

        if (!isActive) {
            dropdown.classList.add('active');
            if (triggerEl) triggerEl.classList.add('active');
            
            // Special cases for loading data
            if (dropdownId === 'notificationsDropdown') {
                fetchRecentNotifications();
            }
        }
    };

    function closeAllHeaderDropdowns() {
        document.querySelectorAll('.premium-dropdown.active').forEach(d => d.classList.remove('active'));
        document.querySelectorAll('.header-icon-btn.active, .header-profile-chip.active').forEach(t => t.classList.remove('active'));
    }

    // Close on outside click
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.header-dropdown-wrapper') && !e.target.closest('.header-profile-section')) {
            closeAllHeaderDropdowns();
        }
        if (searchPanel && !e.target.closest('.command-search-wrap')) {
            searchPanel.classList.remove('active');
        }
    });

    // ─── Operational Clock ────────────────────────────────────────────────────
    function updateOperationalClock() {
        const clockEl = document.getElementById('headerClock');
        if (!clockEl) return;

        const timeEl = clockEl.querySelector('.clock-time');
        const dateEl = clockEl.querySelector('.clock-date');
        
        const now = new Date();
        if (timeEl) timeEl.textContent = now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        if (dateEl) dateEl.textContent = now.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' });
    }
    setInterval(updateOperationalClock, 1000);
    updateOperationalClock();

    // ─── Omni-Search Reactor ──────────────────────────────────────────────────
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const q = e.target.value.trim();
            clearTimeout(searchTimeout);
            
            if (q.length < 2) {
                if (searchPanel) searchPanel.classList.remove('active');
                return;
            }

            searchTimeout = setTimeout(() => executeOmniSearch(q), 300);
        });

        // Focus behavior
        searchInput.addEventListener('focus', () => {
            if (searchInput.value.trim().length >= 2) {
                if (searchPanel) searchPanel.classList.add('active');
            }
        });

        // Ctrl+K Global Shortcut
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                searchInput.focus();
            }
        });
    }

    async function executeOmniSearch(q) {
        if (!searchPanel || !searchScroller) return;
        searchPanel.classList.add('active');
        searchScroller.innerHTML = '<div class="search-loading"><i class="fas fa-spinner fa-spin"></i> Searching platform...</div>';

        try {
            const response = await fetch(`/admin/api/omni-search?q=${encodeURIComponent(q)}`);
            const data = await response.json();

            if (data.success && data.results.length > 0) {
                renderSearchResults(data.results);
            } else {
                searchScroller.innerHTML = '<div class="search-no-results">No matches found for "' + q + '"</div>';
            }
        } catch (err) {
            searchScroller.innerHTML = '<div class="search-error">Search failed. Try again.</div>';
        }
    }

    function renderSearchResults(results) {
        if (!searchScroller) return;
        searchScroller.innerHTML = results.map(res => {
            const typeClass = res.type.toLowerCase().replace(' ', '-');
            return `
                <a href="${res.link}" class="omni-result-item">
                    <div class="omni-result-icon ${typeClass}"><i class="${res.icon}"></i></div>
                    <div class="omni-result-content">
                        <div class="omni-result-header">
                            <span class="omni-result-title">${res.title}</span>
                            <span class="omni-type-tag ${typeClass}">${res.type}</span>
                        </div>
                        <span class="omni-result-subtitle">${res.subtitle}</span>
                    </div>
                    <div class="omni-result-action">
                        <i class="fas fa-chevron-right"></i>
                    </div>
                </a>
            `;
        }).join('');
    }

    // ─── Notification Intelligence ────────────────────────────────────────────
    async function fetchRecentNotifications() {
        const body = document.getElementById('headerNotifBody');
        if (!body) return;

        try {
            const response = await fetch('/admin/api/notifications/recent');
            const data = await response.json();

            if (data.success && data.notifications.length > 0) {
                body.innerHTML = data.notifications.map(n => `
                    <div class="notif-item ${n.is_read ? '' : 'unread'}">
                        <div class="notif-icon ${n.type}"><i class="${getNotifIcon(n.type)}"></i></div>
                        <div class="notif-content">
                            <p class="notif-title">${n.title}</p>
                            <p class="notif-msg">${n.message}</p>
                            <span class="notif-time">${formatTimeAgo(n.created_at)}</span>
                        </div>
                    </div>
                `).join('');
            } else {
                body.innerHTML = '<div class="empty-notif"><i class="fas fa-bell-slash"></i><p>No new alerts</p></div>';
            }
        } catch (err) {
            body.innerHTML = '<div class="empty-notif text-danger"><p>Failed to load</p></div>';
        }
    }

    window.markAllNotificationsRead = async function() {
        try {
            await fetch('/admin/api/notifications/mark-all-read', { method: 'POST' });
            const dot = document.getElementById('headerNotifDot');
            if (dot) dot.style.display = 'none';
            fetchRecentNotifications();
        } catch (err) {
            console.error("Failed to mark all read");
        }
    };

    function getNotifIcon(type) {
        const icons = { 'info': 'fas fa-info-circle', 'success': 'fas fa-check-circle', 'warning': 'fas fa-exclamation-triangle', 'error': 'fas fa-times-circle' };
        return icons[type] || 'fas fa-bell';
    }

    function formatTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);
        if (seconds < 60) return 'Just now';
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m ago`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h ago`;
        return date.toLocaleDateString();
    }

    // ─── Real-Time System Intelligence ────────────────────────────────────────
    async function checkSystemHealth() {
        const heartbeat = document.querySelector('.system-heartbeat');
        const dot = document.querySelector('.pulse-dot');
        const label = document.querySelector('.heartbeat-label');
        if (!heartbeat || !dot || !label) return;

        try {
            const response = await fetch('/admin/api/system-health');
            const data = await response.json();

            if (data.status === 'operational') {
                heartbeat.style.background = '#f0fdf4';
                heartbeat.style.borderColor = '#dcfce7';
                dot.style.background = '#10b981';
                label.textContent = 'Operational';
                label.style.color = '#15803d';
            } else {
                heartbeat.style.background = '#fef2f2';
                heartbeat.style.borderColor = '#fee2e2';
                dot.style.background = '#ef4444';
                label.textContent = 'Degraded';
                label.style.color = '#b91c1c';
            }
        } catch (err) {
            heartbeat.style.background = '#f1f5f9';
            heartbeat.style.borderColor = '#e2e8f0';
            dot.style.background = '#94a3b8';
            label.textContent = 'Offline';
            label.style.color = '#475569';
        }
    }
    setInterval(checkSystemHealth, 30000); // Check every 30 seconds
    checkSystemHealth();

})();