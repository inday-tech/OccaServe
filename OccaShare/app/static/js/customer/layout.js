/**
 * OccaServe Customer Portal — Layout JS v3.1
 * Clean, functional, real-time. No jargon.
 */

document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
    initSearch();
    initInactivityTimer();
    initHeartbeat();
    initWebSocket();
    initDropdownClose();

    // Ctrl+K shortcut
    document.addEventListener('keydown', e => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            document.getElementById('globalSearchInput')?.focus();
        }
        if (e.key === 'Escape') {
            closeAllDropdowns();
            closeSearch();
        }
    });
});

/* ============================================================
   SIDEBAR
   ============================================================ */
function initSidebar() {
    const toggleBtn = document.getElementById('desktopToggleBtn');
    const html      = document.documentElement;

    // Restore collapsed state
    if (localStorage.getItem('customerSidebarCollapsed') === 'true') {
        html.classList.add('sidebar-icons-only');
    }

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            if (window.innerWidth <= 1024) {
                window.closeSidebar();
            } else {
                const collapsed = html.classList.toggle('sidebar-icons-only');
                localStorage.setItem('customerSidebarCollapsed', collapsed);
            }
        });
    }
}

window.toggleSidebar = function () {
    const sidebar  = document.getElementById('mainSidebar');
    const overlay  = document.getElementById('sidebarOverlay');
    if (!sidebar) return;
    const isOpen = sidebar.classList.toggle('active');
    if (overlay) overlay.classList.toggle('active', isOpen);
    // Prevent body scroll when sidebar is open on mobile
    document.body.style.overflow = isOpen ? 'hidden' : '';
};

window.closeSidebar = function () {
    const sidebar = document.getElementById('mainSidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (sidebar) sidebar.classList.remove('active');
    if (overlay) overlay.classList.remove('active');
    document.body.style.overflow = '';
};

/* ============================================================
   GLOBAL SEARCH — Real-time, accurate, debounced
   ============================================================ */
function initSearch() {
    const input      = document.getElementById('globalSearchInput');
    const panel      = document.getElementById('omniSearchResults');
    const scroller   = document.getElementById('searchResultsScroller');
    if (!input || !panel || !scroller) return;

    let timer       = null;
    let lastQuery   = '';
    let highlighted = -1;

    input.addEventListener('input', () => {
        const q = input.value.trim();
        clearTimeout(timer);

        if (q.length < 2) { closeSearch(); return; }
        if (q === lastQuery) return;

        // Show loading state immediately
        scroller.innerHTML = renderLoading();
        openPanel();

        timer = setTimeout(() => runSearch(q), 200);
    });

    input.addEventListener('keydown', e => {
        if (!panel.classList.contains('open')) return;
        const items = panel.querySelectorAll('.search-result-item');
        if (!items.length) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            highlighted = Math.min(highlighted + 1, items.length - 1);
            updateHighlight(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            highlighted = Math.max(highlighted - 1, 0);
            updateHighlight(items);
        } else if (e.key === 'Enter' && highlighted >= 0) {
            e.preventDefault();
            items[highlighted].click();
        }
    });

    // Close on outside click
    document.addEventListener('click', e => {
        if (!input.contains(e.target) && !panel.contains(e.target)) closeSearch();
    });

    async function runSearch(q) {
        lastQuery   = q;
        highlighted = -1;
        try {
            const res  = await fetch(`/customer/api/omni-search?q=${encodeURIComponent(q)}`);
            const data = await res.json();
            renderResults(data, q);
        } catch {
            scroller.innerHTML = `<div class="search-no-results">
                <i class="fas fa-triangle-exclamation"></i>
                <p>Could not reach server. Please try again.</p>
            </div>`;
        }
    }

    function renderResults(results, q) {
        if (!results || results.length === 0) {
            scroller.innerHTML = `<div class="search-no-results">
                <i class="fas fa-magnifying-glass"></i>
                <p>No results for "<strong>${escHtml(q)}</strong>"</p>
            </div>`;
            return;
        }

        // Group by type
        const caterers = results.filter(r => r.type === 'caterer');
        const bookings = results.filter(r => r.type === 'booking');
        let html = '';

        if (caterers.length) {
            html += `<div class="search-section-label">Caterers</div>`;
            html += caterers.map(r => resultItem(r, 'sri-caterer', 'fas fa-utensils')).join('');
        }
        if (bookings.length) {
            html += `<div class="search-section-label">My Bookings</div>`;
            html += bookings.map(r => resultItem(r, 'sri-booking', 'fas fa-calendar-check')).join('');
        }

        scroller.innerHTML = html;

        // Attach click
        panel.querySelectorAll('.search-result-item').forEach(el => {
            el.addEventListener('click', () => {
                closeSearch();
                window.location.href = el.dataset.href;
            });
        });
    }

    function resultItem(r, iconClass, defaultIcon) {
        return `
        <div class="search-result-item" data-href="${escHtml(r.link)}">
            <div class="sri-icon ${iconClass}"><i class="${r.icon || defaultIcon}"></i></div>
            <div class="sri-info">
                <h4>${escHtml(r.title)}</h4>
                <p>${escHtml(r.subtitle)}</p>
            </div>
            <i class="fas fa-arrow-right sri-arrow"></i>
        </div>`;
    }

    function renderLoading() {
        return `<div class="search-no-results">
            <i class="fas fa-circle-notch fa-spin" style="color:var(--primary-color);font-size:1.5rem;"></i>
            <p style="margin-top:0.5rem;">Searching…</p>
        </div>`;
    }

    function updateHighlight(items) {
        items.forEach((el, i) => el.classList.toggle('highlighted', i === highlighted));
        if (highlighted >= 0) items[highlighted].scrollIntoView({ block: 'nearest' });
    }

    function openPanel() { panel.classList.add('open'); }
    window.closeSearch = function () { panel.classList.remove('open'); highlighted = -1; };
}

function closeSearch() { document.getElementById('omniSearchResults')?.classList.remove('open'); }

/* ============================================================
   DROPDOWN TOGGLE (Messages / Notifications / Profile)
   ============================================================ */
// window.toggleHeaderDropdown is centralized in main.js

// closeAllDropdowns handled by main.js

function initDropdownClose() {
    // Handled by main.js
}

/* ============================================================
   HEARTBEAT — Fetch notifications & messages every 30s
   ============================================================ */
function initHeartbeat() {
    fetchIntelligence();
    setInterval(fetchIntelligence, 30000);
}

async function fetchIntelligence() {
    if (window.customerConfig && window.customerConfig.userRole && window.customerConfig.userRole !== 'customer') return;
    try {
        const msgRes = await fetch('/customer/api/messages/recent');
        const msgs   = await msgRes.json();
        renderMessages(msgs);
    } catch (e) {
        console.warn('[Heartbeat] Could not sync messages:', e.message);
    }
}

// renderNotifications handled by main.js

function renderMessages(data) {
    const body  = document.getElementById('headerMsgBody');
    const badge = document.getElementById('headerMsgBadge');
    const label = document.getElementById('msgUnreadLabel');
    if (!body) return;

    const unread = data.filter(m => !m.is_read).length;

    if (badge) {
        if (unread > 0) {
            badge.textContent = unread < 10 ? unread : '9+';
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    }
    if (label) label.textContent = unread > 0 ? `${unread} new` : '';

    if (!data.length) {
        body.innerHTML = `<div class="hdr-empty"><i class="fas fa-comment-slash"></i><p>No messages yet</p></div>`;
        return;
    }

    body.innerHTML = data.slice(0, 6).map(m => `
        <a href="/customer/messages" class="hdr-msg-item">
            <div class="hmi-avatar">${escHtml(m.sender_name[0] || '?')}</div>
            <div style="flex:1;min-width:0;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span class="hmi-name">${escHtml(m.sender_name)}</span>
                    <span class="hmi-time">${m.time_ago}</span>
                </div>
                <div class="hmi-text">${escHtml(m.message)}</div>
            </div>
            ${!m.is_read ? '<div class="hmi-unread-dot"></div>' : ''}
        </a>
    `).join('');
}

// markAllNotificationsRead centralized in main.js

/* ============================================================
   INACTIVITY TIMER
   ============================================================ */
function initInactivityTimer() {
    const LIMIT = 15 * 60 * 1000;
    const WARN = 60 * 1000;
    let idle, countdown;

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

/* ============================================================
   WEBSOCKET — Live push
   ============================================================ */
function initWebSocket() {
    if (!window.customerConfig || !window.customerConfig.userId) return;
    if (window.customerConfig.userRole && window.customerConfig.userRole !== 'customer') return;
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const clientId = `user_${window.customerConfig.userId}_${Math.random().toString(36).substr(2, 9)}`;
    const ws = new WebSocket(`${proto}//${location.host}/ws/${clientId}`);

    ws.onmessage = ({ data }) => {
        try {
            const d = JSON.parse(data);

            // 1. Messages — instantly refresh message badge + dropdown + active chat
            if (['message', 'chat_message', 'new_booking_message'].includes(d.type)) {
                fetchIntelligence();
                if (d.type === 'new_booking_message') {
                    const senderLabel = d.sender_name || 'Your caterer';
                    const bookingLabel = d.booking_id ? ` (Booking #${d.booking_id})` : '';
                    if (window.showToast) window.showToast(`💬 New message from ${senderLabel}${bookingLabel}`, 'info');
                    // Also bump the notification bell so the persistent DB notif shows
                    if (window.fetchGlobalNotifications) window.fetchGlobalNotifications(true);
                    if (typeof window.onNewBookingMessage === 'function') {
                        window.onNewBookingMessage(d);
                    }
                }
            }

            // 2. Any notification-class event — instantly refresh notification badge + panel
            const notifTypes = ['notification', 'new_notification', 'Booking', 'Payment',
                                'booking_update', 'payment_update', 'status_update',
                                'booking_rejected', 'booking_cancelled', 'payment_rejected', 'kyc_update'];
            if (notifTypes.includes(d.type)) {
                if (window.fetchGlobalNotifications) window.fetchGlobalNotifications(true);
            }

            // 3. Per-event toasts and soft DOM refresh (no full page reload)
            const refresh = () => setTimeout(() => {
                if (window.softRefresh) window.softRefresh();
            }, 900);

            if (d.type === 'kyc_update') {
                if (window.showToast)
                    window.showToast(d.message || 'Your identity verification status was updated.', d.status === 'verified' ? 'success' : 'warning');
                refresh();
            }
            if (d.type === 'booking_update' || d.type === 'status_update') {
                if (window.showToast)
                    window.showToast(d.message || 'Your booking status has been updated.', 'info');
                refresh();
            }
            if (d.type === 'payment_update') {
                if (window.showToast)
                    window.showToast(d.message || 'Your payment has been verified.', 'success');
                refresh();
            }
            if (d.type === 'payment_rejected') {
                if (window.showToast)
                    window.showToast(d.message || 'Your payment proof was rejected. Please re-upload.', 'warning');
                refresh();
            }
            if (d.type === 'booking_rejected') {
                if (window.showToast)
                    window.showToast(d.message || 'Your booking request has been declined.', 'error');
                refresh();
            }
            if (d.type === 'booking_cancelled') {
                if (window.showToast)
                    window.showToast(d.message || 'Your booking has been cancelled.', 'warning');
                refresh();
            }
        } catch {}
    };
    ws.onerror = () => {};
    ws.onclose = () => setTimeout(initWebSocket, 5000);
}

/* ============================================================
   CONFIRM LOGOUT
   ============================================================ */
window.confirmLogout = function (e) {
    if(e) e.preventDefault();
    const modal = document.getElementById('univLogoutModal');
    if (modal) modal.classList.add('active');
    else window.location.href = '/auth/logout';
};

/* ============================================================
   HELPERS
   ============================================================ */
function escHtml(s) {
    if (!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function getNotifIcon(type) {
    const map = { booking:'fas fa-calendar-check', payment:'fas fa-wallet', security:'fas fa-shield-check', system:'fas fa-bell', message:'fas fa-comment-dots' };
    return map[type] || 'fas fa-bell';
}
function getNotifBg(type) {
    const map = { booking:'rgba(16,185,129,0.1)', payment:'rgba(249,115,22,0.1)', security:'rgba(59,130,246,0.1)', message:'rgba(255,123,84,0.1)' };
    return map[type] || 'var(--dm-slate-50)';
}
function getNotifColor(type) {
    const map = { booking:'#10b981', payment:'#f97316', security:'#3b82f6', message:'var(--primary-color)' };
    return map[type] || 'var(--dm-slate-400)';
}
