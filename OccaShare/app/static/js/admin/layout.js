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
            if (window.innerWidth <= 1024) {
                if (sidebar.classList.contains('active')) {
                    window.closeSidebar();
                } else {
                    window.openSidebar();
                }
            } else {
                const isCollapsed = htmlEl.classList.toggle('sidebar-icons-only');
                localStorage.setItem('adminSidebarCollapsed', isCollapsed ? 'true' : 'false');
                window.dispatchEvent(new Event('resize'));
                setTimeout(() => window.dispatchEvent(new Event('resize')), 320);
            }
        });
    }

    // Restore collapse state on load (already done inline, but enforce here too)
    if (localStorage.getItem('adminSidebarCollapsed') === 'true') {
        htmlEl.classList.add('sidebar-icons-only');
    }

    // ─── Logout Confirmation is handled by layout.html's confirmLogout() ──

        // ─── Inactivity Auto-Logout ───────────────────────────────────────────────
    const LIMIT = 15 * 60 * 1000;
    const WARN = 60 * 1000;
    let idle, countdown;
    
    function initInactivityTimer() {
        const reset = () => {
            clearTimeout(idle); clearInterval(countdown);
            const m = document.getElementById('inactivityModal');
            if (m) {
                m.classList.remove('active');
                setTimeout(() => { if (!m.classList.contains('active')) m.style.display = 'none'; }, 400);
            }
            idle = setTimeout(warn, LIMIT - WARN);
        };

        const warn = () => {
            const m = document.getElementById('inactivityModal');
            if (m) {
                m.style.display = 'flex';
                requestAnimationFrame(() => requestAnimationFrame(() => m.classList.add('active')));
            }
            let s = 60;
            const cdEl = document.getElementById('inactivityCountdown');
            if(cdEl) cdEl.innerText = s;
            
            countdown = setInterval(() => { 
                s--;
                if(cdEl) cdEl.innerText = s;
                if (s <= 0) { 
                    clearInterval(countdown); 
                    window.location.href = '/auth/logout?reason=inactivity'; 
                } 
            }, 1000);
        };

        ['mousedown','mousemove','keypress','scroll','touchstart','click'].forEach(ev => document.addEventListener(ev, reset, { passive: true }));
        const stayBtn = document.getElementById('stayLoggedInBtn');
        if(stayBtn) stayBtn.addEventListener('click', reset);
        reset();
    }
    initInactivityTimer();

    // Close on outside click
    document.addEventListener('click', (e) => {
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
        if (timeEl) timeEl.textContent = now.toLocaleTimeString('en-US', { hour12: true, hour: 'numeric', minute: '2-digit', second: '2-digit' });
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

    // ─── Notification Intelligence Centralized in main.js ──────────────────────
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
