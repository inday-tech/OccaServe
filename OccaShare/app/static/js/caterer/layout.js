(function () {
        // ─── Inactivity Auto-Logout ──────────────────────────────────────────────
    const LIMIT = 15 * 60 * 1000; // 15 mins total
    const WARN = 60 * 1000;       // 1 min countdown
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

        const activityEvents = ['mousedown','mousemove','keypress','scroll','touchstart','click'];
        activityEvents.forEach(ev => document.addEventListener(ev, reset, { passive: true }));
        const stayBtn = document.getElementById('stayLoggedInBtn');
        if(stayBtn) stayBtn.addEventListener('click', reset);
        reset();
    }
    initInactivityTimer();

    // ─── Sidebar Scroll Persistence ─────────────────────────────────────────
    const sidebar = document.getElementById('sidebar');

    function restoreSidebarScroll() {
        if (!sidebar) return;
        const scrollPos = sessionStorage.getItem('sidebar-scroll');
        if (scrollPos) sidebar.scrollTop = parseInt(scrollPos, 10);

        const activeLink = sidebar.querySelector('a.active');
        if (activeLink) {
            const rect = activeLink.getBoundingClientRect();
            const sidebarRect = sidebar.getBoundingClientRect();
            if (rect.top < sidebarRect.top || rect.bottom > sidebarRect.bottom) {
                activeLink.scrollIntoView({ block: 'nearest' });
            }
        }
    }

    // Set scroll capture once
    if (sidebar) {
        sidebar.addEventListener('scroll', function () {
            sessionStorage.setItem('sidebar-scroll', sidebar.scrollTop);
        }, { passive: true });
    }

    window.addEventListener('load', restoreSidebarScroll);

    // ─── Mobile Burger Menu ──────────────────────────────────────────────────
    const overlay = document.getElementById('sidebarOverlay');
    const burgerBtn = document.getElementById('burgerBtn');
    const topbar = document.getElementById('mobileTopbar');

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
        document.body.style.overflow = 'hidden'; // Prevent background scroll
    };

    window.closeSidebar = function () {
        if (!sidebar) return;
        // Check window width - logic for mobile
        if (window.innerWidth > 1024) return;
        sidebar.classList.remove('sidebar-open');
        if (overlay) overlay.classList.remove('active');
        if (topbar) topbar.classList.remove('burger-open');
        document.body.style.overflow = '';
    };

    // Close sidebar on Escape key
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeSidebar();
    });

    // On resize: if switching to desktop, clean up mobile state
    window.addEventListener('resize', function () {
        if (window.innerWidth > 1024 && sidebar) {
            sidebar.classList.remove('sidebar-open');
            if (overlay) overlay.classList.remove('active');
            if (topbar) topbar.classList.remove('burger-open');
            document.body.style.overflow = '';
        }
    });


    // ─── Header Dropdowns (Profile, Messages, Notifications) ───────────────────
    window.toggleHeaderDropdown = function (dropdownId, triggerEl) {
        const dropdown = document.getElementById(dropdownId);
        if (!dropdown) return;

        const isActive = dropdown.classList.contains('active');
        
        // Close other dropdowns if any
        closeAllDropdowns();

        if (!isActive) {
            dropdown.style.display = 'block';
            setTimeout(() => {
                dropdown.classList.add('active');
                if (triggerEl) triggerEl.classList.add('active');
            }, 10);

            // Load content if it's messages
            if (dropdownId === 'messagesDropdown') {
                if (typeof window.loadHeaderMessages === 'function') {
                    window.loadHeaderMessages();
                }
            }
        }
    };

    window.toggleProfileDropdown = function () {
        const trigger = document.querySelector('.profile-trigger');
        window.toggleHeaderDropdown('profileDropdown', trigger);
    };

    function closeAllDropdowns() {
        const dropdowns = document.querySelectorAll('.premium-dropdown, .profile-dropdown');
        const triggers = document.querySelectorAll('.profile-trigger, .header-action-btn, .hdr-btn');
        dropdowns.forEach(d => {
            d.classList.remove('active');
            setTimeout(() => {
                if (!d.classList.contains('active')) d.style.display = 'none';
            }, 300);
        });
        triggers.forEach(t => t.classList.remove('active'));
    }

    // Close dropdowns on outside click
    document.addEventListener('click', function (e) {
        if (!e.target.closest('.header-profile-section') && !e.target.closest('.header-dropdown-wrapper')) {
            closeAllDropdowns();
        }
    });

    // ─── Global Search Logic ────────────────────────────────────────────────
    const globalSearchInput = document.getElementById('globalSearchInput');
    if (globalSearchInput) {
        globalSearchInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                const query = this.value.trim();
                if (query) {
                    // Example: Redirect to a search page or filter current view
                    // For now, let's just log or implement a simple redirect if needed
                    console.log("Global search for:", query);
                    // window.location.href = `/caterer/search?q=${encodeURIComponent(query)}`;
                }
            }
        });
    }

    // ─── Real-Time WebSocket Client ──────────────────────────────────────────

    if (window.catererConfig && window.catererConfig.userId) {
        let socket;
        let reconnectAttempts = 0;
        const maxReconnectAttempts = 5;
        const reconnectDelay = 3000;

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const clientId = `user_${window.catererConfig.userId}_${Math.random().toString(36).substr(2, 9)}`;
            const wsUrl = `${protocol}//${window.location.host}/ws/${clientId}`;

            socket = new WebSocket(wsUrl);

            socket.onopen = function () {
                console.log("WebSocket connected as", clientId);
                reconnectAttempts = 0;
            };

            socket.onmessage = function (event) {
                try {
                    const data = JSON.parse(event.data);
                    handleRealTimeMessage(data);
                } catch (e) {
                    console.error("Failed to parse WebSocket message:", e);
                }
            };

            socket.onclose = function () {
                console.log("WebSocket closed");
                if (reconnectAttempts < maxReconnectAttempts) {
                    reconnectAttempts++;
                    setTimeout(connectWebSocket, reconnectDelay * reconnectAttempts);
                }
            };

            socket.onerror = function (err) {
                console.error("WebSocket error:", err);
                socket.close();
            };
        }

        function handleRealTimeMessage(data) {
            console.log("Real-time update received:", data);

            if (data.type === 'new_notification') {
                updateNotificationBadge(data.count);
                if (window.showToast) {
                    window.showToast(data.message || "New notification received", "info");
                }
            } else if (data.type === 'booking_update') {
                // If on dashboard, refresh stats
                if (typeof window.refreshDashboardData === 'function') {
                    window.refreshDashboardData();
                }

                if (window.location.pathname.includes('/caterer/bookings')) {
                    if (typeof window.refreshBookingsTable === 'function') {
                        window.refreshBookingsTable();
                    } else {
                        setTimeout(() => window.location.reload(), 1000);
                    }
                }

                if (window.showToast) {
                    window.showToast(`Booking Update: ${data.message || 'Status changed'}`, "success");
                }
            } else if (data.type === 'booking_archived' || data.type === 'package_archived' || data.type === 'menu_archived') {
                const idMap = {
                    'booking_archived': `booking-row-${data.booking_id}`,
                    'package_archived': `package-card-${data.package_id}`,
                    'menu_archived': `menu-item-row-${data.item_id}`
                };
                const elementId = idMap[data.type];
                const el = document.getElementById(elementId);
                if (el) {
                    el.classList.add('fade-out-archive');
                    setTimeout(() => el.remove(), 500);
                }
                if (window.showToast) {
                    window.showToast(data.message, "info");
                }
            } else if (data.type === 'status_update') {
                if (window.showToast) {
                    window.showToast(data.message || "Your account status has been updated", "success");
                }
                if (data.status === 'Verified' || data.status === 'approved') {
                    // Update any status badges on the page if they exist
                    const statusBadge = document.querySelector('.status-badge-fancy');
                    if (statusBadge) {
                        statusBadge.innerHTML = '<i class="fas fa-check-circle"></i> Approved';
                        statusBadge.className = 'status-badge-fancy approved';
                    }

                    // Reload after a short delay for a smooth transition
                    setTimeout(() => {
                        window.location.reload();
                    }, 2500);
                }
            } else if (data.type === 'payout_update' || data.type === 'payout_completed') {
                if (window.showToast) {
                    window.showToast(data.message || "Payout status updated", "success");
                }
                // Dispatch event for payments.js to handle
                window.dispatchEvent(new CustomEvent('payoutUpdate', { detail: data }));
            } else if (data.type === 'chat_message') {
                updateChatBadge();
                const msgDropdown = document.getElementById('messagesDropdown');
                if (msgDropdown && msgDropdown.classList.contains('active')) {
                    loadHeaderMessages();
                }
                if (window.location.pathname !== '/caterer/messages' && window.showToast) {
                    window.showToast(`New message from ${data.sender_name}`, "info");
                }
            }
        }

        function updateChatBadge() {
            fetch('/api/chat/unread-count')
                .then(r => r.json())
                .then(data => {
                    const badge = document.getElementById('nav-chat-badge');
                    if (badge) {
                        badge.innerText = data.count;
                        badge.style.display = data.count > 0 ? 'flex' : 'none';
                    }
                });
        }

        function loadHeaderMessages() {
            const container = document.getElementById('headerChatContainer');
            if (!container) return;

            fetch('/api/chat/conversations')
                .then(r => r.json())
                .then(conversations => {
                    if (!conversations || conversations.length === 0) {
                        container.innerHTML = `
                            <div style="text-align: center; padding: 2rem 1rem;">
                                <div style="background: #f8fafc; width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 10px;">
                                    <i class="fas fa-comments" style="color: #cbd5e1; font-size: 1.25rem;"></i>
                                </div>
                                <p style="margin: 0; font-size: 0.85rem; color: #64748b;">No messages yet.</p>
                            </div>
                        `;
                        return;
                    }

                    // Only show last 5 conversations
                    const displayList = conversations.slice(0, 5);
                    container.innerHTML = displayList.map(conv => {
                        const lastMsg = conv.last_message;
                        const isUnread = conv.unread_count > 0;
                        const peer = conv.peer;
                        const initials = peer.name ? peer.name.charAt(0) : '?';
                        const time = lastMsg.created_at ? new Date(lastMsg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
                        
                        return `
                            <a href="/caterer/messages?peer_id=${peer.id}" style="display: flex; gap: 12px; padding: 12px 16px; text-decoration: none; border-bottom: 1px solid #f1f5f9; background: ${isUnread ? '#f0f9ff' : 'transparent'}; transition: background 0.2s;">
                                <div style="width: 40px; height: 40px; border-radius: 50%; background: #e2e8f0; display: flex; align-items: center; justify-content: center; flex-shrink: 0; overflow: hidden;">
                                    ${peer.logo || peer.profile_image ? `<img src="${peer.logo || peer.profile_image}" style="width: 100%; height: 100%; object-fit: cover;">` : `<span style="font-weight: 700; color: #64748b; font-size: 0.85rem;">${initials}</span>`}
                                </div>
                                <div style="flex: 1; min-width: 0;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                                        <p style="margin: 0; font-size: 0.85rem; color: #1e293b; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${peer.name}</p>
                                        <span style="font-size: 0.6rem; color: #94a3b8;">${time}</span>
                                    </div>
                                    <p style="margin: 0; font-size: 0.75rem; color: ${isUnread ? '#0284c7' : '#64748b'}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: ${isUnread ? '600' : '400'};">
                                        ${lastMsg.sender_id === window.catererConfig.userId ? 'You: ' : ''}${lastMsg.content || 'Sent a file'}
                                    </p>
                                </div>
                                ${isUnread ? `<div style="width: 8px; height: 8px; border-radius: 50%; background: #0ea5e9; align-self: center; margin-left: 4px;"></div>` : ''}
                            </a>
                        `;
                    }).join('');
                })
                .catch(err => {
                    console.error("Error loading header messages:", err);
                    container.innerHTML = '<p style="text-align: center; padding: 1rem; color: #ef4444; font-size: 0.8rem;">Failed to load messages.</p>';
                });
        }

        window.loadHeaderMessages = loadHeaderMessages;

        // Initial check
        updateChatBadge();

        function updateNotificationBadge(count) {
            const badge = document.getElementById('nav-notif-badge');
            if (badge) {
                badge.innerText = count;
                badge.style.display = count > 0 ? 'flex' : 'none';

                // Animate badge
                badge.style.transform = 'scale(1.2)';
                setTimeout(() => {
                    badge.style.transform = 'scale(1)';
                }, 200);
            }
        }

        connectWebSocket();
    }

    // ─── End of Layout Logic ────────────────────────────────────────────────
})();

/**
 * ValidationManager - Handles real-time validation for caterer forms
 * Globally available for Package and Menu modules
 */
window.ValidationManager = class ValidationManager {
    constructor(formId, config) {
        this.form = document.getElementById(formId);
        if (!this.form) return;
        
        this.config = config;
        this.timer = null;
        this.errors = new Set();
        this.init();
    }

    init() {
        this.form.querySelectorAll('input, select, textarea').forEach(input => {
            const rules = this.config[input.name];
            if (rules) {
                // Reactive Validation
                input.addEventListener('input', () => this.validateField(input, rules));
                input.addEventListener('blur', () => this.validateField(input, rules, true));

                // Proactive Blocking (Hard Stop)
                if (rules.maxLength) {
                    input.addEventListener('keydown', (e) => {
                        const allowedKeys = ['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Tab', 'Enter'];
                        if (input.value.length >= rules.maxLength && !allowedKeys.includes(e.key) && !e.ctrlKey) {
                            e.preventDefault();
                        }
                    });
                }
            }
        });
        this.updateSubmitButton();
        this.form.addEventListener('input', () => this.updateSubmitButton());
    }

    validateField(input, rules, isBlur = false) {
        let value = input.value;
        const feedback = input.nextElementSibling;
        let error = null;

        if (rules.numericOnly && value) {
            const clean = value.replace(/[^0-9,]/g, '');
            if (value !== clean) {
                input.value = clean;
                value = clean;
            }
        }

        const numericValue = parseFloat(value.replace(/,/g, '')) || 0;

        if (rules.max && numericValue > rules.max) {
            if (rules.autoStop) {
                const capped = rules.max.toLocaleString();
                input.value = capped;
                value = capped;
                error = `Maximum limit of ₱${rules.max.toLocaleString()} reached.`;
            } else {
                error = `Value exceeds maximum limit of ₱${rules.max.toLocaleString()}`;
            }
        }

        if (rules.phMobile && value && !error) {
            const valClean = value.replace(/\D/g, '');
            if (!/^09\d{9}$/.test(valClean)) {
                error = 'Mobile number must be 11 digits starting with 09';
            }
        }

        if (rules.noRepetitive && value && !error) {
            const valClean = value.replace(/\D/g, '');
            if (/(\d)\1{4,}/.test(valClean)) {
                error = 'Invalid number: Too many repetitive digits.';
            }
        }

        if (input.name === 'service_duration' && value) {
            if (numericValue < 8 || numericValue > 12) {
                error = 'Service duration must be between 8 and 12 hours';
            }
        }

        if (rules.unique && value.length >= 2 && !error) {
            clearTimeout(this.timer);
            this.timer = setTimeout(async () => {
                const isUnique = await this.checkUnique(input.name, value, rules.uniqueApi);
                if (!isUnique) {
                    this.setError(input, 'This name is already used by another ' + (rules.label || 'item'));
                } else {
                    this.clearError(input);
                }
            }, 600);
            return;
        }


        if (rules.noSameParts && value.includes(' ')) {
            const parts = value.trim().toLowerCase().split(/\s+/).filter(p => p.length > 1);
            const uniqueParts = new Set(parts);
            if (uniqueParts.size < parts.length) {
                error = 'Name contains repetitive parts (e.g. "John John"). Please enter a valid name.';
            }
        }

        if (rules.custom && value && !error) {
            const customResult = rules.custom(value);
            if (customResult !== true) {
                error = customResult;
            }
        }

        if (!error && !input.checkValidity()) {
            error = input.validationMessage;
        }

        if (error) {
            this.setError(input, error);
        } else {
            this.clearError(input);
        }
    }

    setError(input, msg) {
        input.classList.add('is-invalid');
        // Robust search: check next sibling OR search within parent
        let feedback = input.nextElementSibling;
        if (!feedback || !feedback.classList.contains('invalid-feedback')) {
            feedback = input.parentElement.querySelector('.invalid-feedback');
        }
        
        if (feedback && feedback.classList.contains('invalid-feedback')) {
            feedback.innerText = msg;
            feedback.style.display = 'block'; // Force visibility
        }
        this.errors.add(input.name);
        this.updateSubmitButton();
    }

    clearError(input) {
        input.classList.remove('is-invalid');
        let feedback = input.nextElementSibling;
        if (!feedback || !feedback.classList.contains('invalid-feedback')) {
            feedback = input.parentElement.querySelector('.invalid-feedback');
        }
        if (feedback) {
            feedback.style.display = 'none';
        }
        this.errors.delete(input.name);
        this.updateSubmitButton();
    }

    async checkUnique(field, value, apiPath) {
        try {
            let excludeId = null;
            const formAction = this.form.getAttribute('action');
            const match = formAction.match(/\/(?:packages|menu)\/(\d+)\/update/);
            if (match) excludeId = match[1];

            const response = await fetch(apiPath, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: value, exclude_id: excludeId })
            });
            const data = await response.json();
            return !data.exists;
        } catch (e) {
            return true;
        }
    }

    updateSubmitButton() {
        const submitBtn = this.form.querySelector('button[type="submit"]');
        if (!submitBtn) return;
        const isValid = this.form.checkValidity() && this.errors.size === 0;
        submitBtn.disabled = !isValid;
        submitBtn.style.opacity = isValid ? '1' : '0.5';
        submitBtn.style.cursor = isValid ? 'pointer' : 'not-allowed';
    }
};

/**
 * Global AJAX Action Helper
 * Handles button loading states, fetch execution, and Toast notification
 */
window.apiAction = async function(url, options = {}, btn = null) {
    const originalBtnContent = btn ? btn.innerHTML : null;
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    }

    try {
        const headers = {
            'X-Requested-With': 'XMLHttpRequest',
            ...options.headers
        };

        if (options.body && typeof options.body === 'string' && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        }

        const response = await fetch(url, {
            ...options,
            headers: headers
        });

        const data = await response.json();
        if (response.ok) {
            if (window.showToast && !options.muteToast) window.showToast(data.message || "Action completed", "success");
            return data;
        } else {
            let errorMsg = "Request failed";
            if (data.detail) {
                if (Array.isArray(data.detail)) {
                    errorMsg = data.detail.map(err => `${err.loc.join('.')}: ${err.msg}`).join('\n');
                } else if (typeof data.detail === 'string') {
                    errorMsg = data.detail;
                } else {
                    errorMsg = JSON.stringify(data.detail);
                }
            }
            if (window.showError) window.showError(errorMsg);
            return null;
        }
    } catch (error) {
        console.error("API Action Error:", error);
        if (window.showError) window.showError("An unexpected error occurred.");
        return null;
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalBtnContent;
        }
    }
};

/* ===================================================
   PREMIUM GLOBAL MODAL ENGINE v1.5
   window.openModal(id)   — opens overlay by ID
   window.closeModal(id)  — closes overlay by ID
   window.closeAllModals()— closes every open overlay
   =================================================== */
window.openModal = function(id) {
    const overlay = document.getElementById(id);
    if (!overlay) { console.warn('[Modal] No element found with id:', id); return; }
    // Close all others first to prevent stacking
    document.querySelectorAll('.occ-modal-overlay.active').forEach(el => {
        if (el.id !== id) _dismissModal(el);
    });
    overlay.style.display = 'flex';
    // Force reflow so CSS transition fires
    void overlay.offsetHeight;
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
};

window.closeModal = function(id) {
    const overlay = id ? document.getElementById(id) : null;
    if (overlay) {
        _dismissModal(overlay);
    } else {
        // If no id given, close the topmost active modal
        const active = document.querySelector('.occ-modal-overlay.active');
        if (active) _dismissModal(active);
    }
};

window.closeAllModals = function() {
    document.querySelectorAll('.occ-modal-overlay.active').forEach(_dismissModal);
};

function _dismissModal(overlay) {
    overlay.classList.remove('active');
    // Safe dismissal
    setTimeout(() => {
        if (!overlay.classList.contains('active')) {
            overlay.style.display = 'none';
        }
    }, 450);
    // Restore scroll if no other modals are open
    const stillOpen = document.querySelectorAll('.occ-modal-overlay.active');
    if (stillOpen.length === 0) {
        document.body.style.overflow = '';
    }
}

// Close on overlay backdrop click
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('occ-modal-overlay')) {
        window.closeModal(e.target.id);
    }
});

// Close on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') window.closeModal();
});

/* ===================================================
   UPGRADED ACTION MENU DROPDOWN (3 dots)
   Uses .menu-open class for smooth CSS transitions
   =================================================== */
window.toggleActionMenu = function(id) {
    const target = document.getElementById('actionMenu-' + id);
    if (!target) return;

    const isOpen = target.classList.contains('menu-open');

    // Close all open menus first
    document.querySelectorAll('.action-dropdown-menu.menu-open').forEach(el => {
        el.classList.remove('menu-open');
    });

    // If it was closed, open it
    if (!isOpen) {
        target.classList.add('menu-open');
    }
};

// Close dropdown on outside click
document.addEventListener('click', function(e) {
    if (!e.target.closest('.action-dropdown-container')) {
        document.querySelectorAll('.action-dropdown-menu.menu-open').forEach(el => {
            el.classList.remove('menu-open');
        });
    }
});

// ─── Global Logout Handler is now managed directly by confirmLogout() in layout.html ───
