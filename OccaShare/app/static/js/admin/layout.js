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

    // ─── Mobile Sidebar Swipe Gestures ───────────────────────────────────────
    let touchStartX = 0;
    let touchStartY = 0;
    const SWIPE_THRESHOLD = 60; // Min swipe distance in pixels

    document.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
    }, { passive: true });

    document.addEventListener('touchend', function(e) {
        if (window.innerWidth > 1024) return; // Only apply to mobile/tablet view
        
        const touchEndX = e.changedTouches[0].screenX;
        const touchEndY = e.changedTouches[0].screenY;
        
        const deltaX = touchEndX - touchStartX;
        const deltaY = touchEndY - touchStartY;
        
        // Ensure it's a horizontal swipe (not scrolling up/down)
        if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > SWIPE_THRESHOLD) {
            const isOpen = sidebar && sidebar.classList.contains('active');
            
            if (deltaX > 0) {
                // Swiped Right -> Open Sidebar
                if (!isOpen && touchStartX < 40) {
                    window.openSidebar();
                }
            } else {
                // Swiped Left -> Close Sidebar
                if (isOpen) {
                    window.closeSidebar();
                }
            }
        }
    }, { passive: true });

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
                // Trigger reflow to animate
                requestAnimationFrame(() => requestAnimationFrame(() => m.classList.add('active')));
            }
            
            const cdEl = document.getElementById('inactivityCountdown');
            const endTime = Date.now() + 60000;
            
            if(cdEl) cdEl.innerText = '60';
            
            countdown = setInterval(() => { 
                const s = Math.round((endTime - Date.now()) / 1000);
                if(cdEl) cdEl.innerText = Math.max(0, s);
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
    const desktopSearchInput = document.getElementById('globalSearchInput');
    const mobileSearchInput = document.getElementById('mobileSearchInput');
    const desktopSearchPanel = document.getElementById('omniSearchResults');
    const mobileSearchPanel = document.getElementById('omniSearchResultsMobile');
    const desktopSearchScroller = document.getElementById('searchResultsScroller');
    const mobileSearchScroller = document.getElementById('searchResultsScrollerMobile');
    const mobileSearchToggle = document.getElementById('mobileSearchToggle');
    const mobileSearchWrap = document.querySelector('.mobile-search-wrap');
    const mobileSearchPopover = document.getElementById('mobileSearchPanel');
    const searchInputs = [desktopSearchInput, mobileSearchInput].filter(Boolean);
    let searchTimeout;
    let searchController;
    let searchRequestId = 0;
    let syncingSearchInputs = false;

    if (desktopSearchInput?.value.trim().length >= 2) {
        [desktopSearchScroller, mobileSearchScroller].forEach(scroller => {
            if (scroller) scroller.replaceChildren();
        });
    }

    function hideSearchResults() {
        [desktopSearchPanel, mobileSearchPanel].forEach(panel => {
            if (panel) panel.classList.remove('active');
        });
    }

    function showFocusedSearchResults() {
        desktopSearchPanel?.classList.toggle('active', document.activeElement === desktopSearchInput);
        mobileSearchPanel?.classList.toggle(
            'active',
            document.activeElement === mobileSearchInput && mobileSearchPopover?.classList.contains('open')
        );
    }

    function setSearchMessage(scroller, message, iconClass) {
        if (!scroller) return;
        const container = document.createElement('div');
        container.className = 'search-feedback';
        if (iconClass) {
            const icon = document.createElement('i');
            icon.className = iconClass;
            container.appendChild(icon);
        }
        const text = document.createElement('span');
        text.textContent = message;
        container.appendChild(text);
        scroller.replaceChildren(container);
    }

    function renderSearchResults(scroller, results) {
        if (!scroller) return;
        const fragment = document.createDocumentFragment();
        results.forEach(result => {
            const link = document.createElement('a');
            link.className = 'omni-result-item';
            link.href = result.link;

            const iconBox = document.createElement('div');
            iconBox.className = `omni-result-icon ${(result.type || '').toLowerCase().replace(/\s+/g, '-')}`;
            const icon = document.createElement('i');
            icon.className = result.icon;
            iconBox.appendChild(icon);

            const content = document.createElement('div');
            content.className = 'omni-result-content';
            const header = document.createElement('div');
            header.className = 'omni-result-header';

            const title = document.createElement('span');
            title.className = 'omni-result-title';
            title.textContent = result.title;
            const type = document.createElement('span');
            type.className = 'omni-type-tag';
            type.textContent = result.type;
            header.append(title, type);

            const subtitle = document.createElement('span');
            subtitle.className = 'omni-result-subtitle';
            subtitle.textContent = result.subtitle;
            content.append(header, subtitle);

            const action = document.createElement('div');
            action.className = 'omni-result-action';
            const arrow = document.createElement('i');
            arrow.className = 'fas fa-chevron-right';
            action.appendChild(arrow);

            link.append(iconBox, content, action);
            fragment.appendChild(link);
        });
        scroller.replaceChildren(fragment);
    }

    async function executeOmniSearch(query, requestId) {
        if (searchController) searchController.abort();
        searchController = new AbortController();
        [desktopSearchScroller, mobileSearchScroller].forEach(scroller => {
            setSearchMessage(scroller, 'Searching platform...', 'fas fa-spinner fa-spin');
        });
        showFocusedSearchResults();

        try {
            const response = await fetch(`/admin/api/omni-search?q=${encodeURIComponent(query)}`, {
                signal: searchController.signal
            });
            if (!response.ok) throw new Error(`Search request failed (${response.status})`);
            const data = await response.json();
            if (requestId !== searchRequestId) return;

            if (data.success && data.results.length) {
                renderSearchResults(desktopSearchScroller, data.results);
                renderSearchResults(mobileSearchScroller, data.results);
            } else {
                setSearchMessage(desktopSearchScroller, `No matches found for "${query}"`, 'fas fa-search');
                setSearchMessage(mobileSearchScroller, `No matches found for "${query}"`, 'fas fa-search');
            }
            showFocusedSearchResults();
        } catch (error) {
            if (error.name === 'AbortError' || requestId !== searchRequestId) return;
            setSearchMessage(desktopSearchScroller, 'Search failed. Try again.', 'fas fa-triangle-exclamation');
            setSearchMessage(mobileSearchScroller, 'Search failed. Try again.', 'fas fa-triangle-exclamation');
            console.error('Admin search failed:', error);
        }
    }

    searchInputs.forEach(input => {
        input.addEventListener('input', () => {
            if (syncingSearchInputs) return;
            const query = input.value.trim();
            syncingSearchInputs = true;
            searchInputs.forEach(otherInput => {
                if (otherInput !== input) otherInput.value = input.value;
            });
            if (input === mobileSearchInput && desktopSearchInput) {
                desktopSearchInput.dispatchEvent(new Event('input', { bubbles: true }));
            }
            syncingSearchInputs = false;

            clearTimeout(searchTimeout);
            searchRequestId += 1;
            if (searchController) searchController.abort();
            if (query.length < 2) {
                hideSearchResults();
                [desktopSearchScroller, mobileSearchScroller].forEach(scroller => {
                    if (scroller) scroller.replaceChildren();
                });
                return;
            }

            const requestId = searchRequestId;
            searchTimeout = setTimeout(() => executeOmniSearch(query, requestId), 250);
        });

        input.addEventListener('focus', () => {
            if (input.value.trim().length >= 2 && (desktopSearchScroller?.childElementCount || mobileSearchScroller?.childElementCount)) {
                (input === mobileSearchInput ? mobileSearchPanel : desktopSearchPanel)?.classList.add('active');
            }
        });
    });

    if (mobileSearchToggle && mobileSearchPopover) {
        mobileSearchToggle.addEventListener('click', () => {
            const isOpen = mobileSearchPopover.classList.toggle('open');
            mobileSearchToggle.setAttribute('aria-expanded', String(isOpen));
            if (isOpen) mobileSearchInput?.focus();
            else mobileSearchPanel?.classList.remove('active');
        });
    }

    document.addEventListener('click', event => {
        if (desktopSearchPanel && !event.target.closest('.command-search-wrap')) {
            desktopSearchPanel.classList.remove('active');
        }
        if (mobileSearchWrap && !mobileSearchWrap.contains(event.target)) {
            mobileSearchPopover?.classList.remove('open');
            mobileSearchPanel?.classList.remove('active');
            mobileSearchToggle?.setAttribute('aria-expanded', 'false');
        }
    });

    document.addEventListener('keydown', event => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
            event.preventDefault();
            const desktopSearchWrap = desktopSearchInput?.closest('.command-search-wrap');
            if (desktopSearchInput && desktopSearchWrap && window.getComputedStyle(desktopSearchWrap).display !== 'none') {
                desktopSearchInput.focus();
                desktopSearchInput.select();
            } else {
                mobileSearchPopover?.classList.add('open');
                mobileSearchToggle?.setAttribute('aria-expanded', 'true');
                mobileSearchInput?.focus();
            }
        }
        if (event.key === 'Escape') {
            hideSearchResults();
            mobileSearchPopover?.classList.remove('open');
            mobileSearchToggle?.setAttribute('aria-expanded', 'false');
            searchInputs.forEach(input => input.blur());
        }
    });

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
