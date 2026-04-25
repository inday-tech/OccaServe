(function () {
    // ─── Inactivity Auto-Logout ──────────────────────────────────────────────
    let timeoutLength = 15 * 60 * 1000; // 15 minutes
    let warningLength = 14 * 60 * 1000; // 14 minutes
    let inactivityTimeout;
    let warningTimeout;
    const modal = document.getElementById('inactivityModal');
    const stayBtn = document.getElementById('stayLoggedInBtn');

    function resetTimer() {
        if (modal && modal.style.display === 'flex') return;
        clearTimeout(inactivityTimeout);
        clearTimeout(warningTimeout);

        warningTimeout = setTimeout(function () {
            if (modal) {
                modal.style.display = 'flex';
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        modal.classList.add('active');
                    });
                });
            }
        }, warningLength);

        inactivityTimeout = setTimeout(function () {
            window.location.href = '/auth/logout?reason=inactivity';
        }, timeoutLength);
    }

    if (stayBtn) {
        stayBtn.addEventListener('click', function () {
            if (modal) {
                modal.classList.remove('active');
                setTimeout(() => {
                    if (!modal.classList.contains('active')) {
                        modal.style.display = 'none';
                    }
                }, 400);
            }
            resetTimer();
        });
    }

    // Initialize timer only once
    const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
    activityEvents.forEach(evt => {
        document.addEventListener(evt, resetTimer, { passive: true });
    });
    resetTimer();

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

    // ─── Desktop Sidebar Toggle ──────────────────────────────────────────────
    const desktopToggleBtn = document.getElementById('desktopToggleBtn');
    if (desktopToggleBtn) {
        desktopToggleBtn.addEventListener('click', function () {
            const wrapper = document.querySelector('.dashboard-wrapper');
            if (wrapper) {
                wrapper.classList.toggle('sidebar-icons-only');

                // Save mode to backend
                const isIconsOnly = wrapper.classList.contains('sidebar-icons-only');
                const newMode = isIconsOnly ? 'icons' : 'full';

                fetch('/caterer/api/sidebar-mode', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ mode: newMode })
                }).catch(err => {
                    console.error("Failed to save sidebar mode:", err);
                });

                // Dispatch resize event immediately so charts start adjusting
                window.dispatchEvent(new Event('resize'));

                // Dispatch resize event again after CSS transition completes
                setTimeout(() => {
                    window.dispatchEvent(new Event('resize'));
                }, 310); // wait for CSS transition (300ms) + small buffer
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
                    const row = document.getElementById(`booking-row-${data.booking_id}`);
                    if (row) {
                        // Update status badge in table
                        const badge = row.querySelector('.premium-status-badge');
                        if (badge && data.new_status) {
                            badge.innerText = data.status_label || (data.new_status.charAt(0).toUpperCase() + data.new_status.slice(1));
                            // Remove old status classes and add new one
                            badge.className = 'premium-status-badge ' + (data.status_class || '');
                        }
                    }
                }
                
                // Update Modal if open
                const modal = document.getElementById('bookingDetailModal');
                const modalIdEl = document.getElementById('modalBookingId');
                if (modal && modal.style.display === 'flex' && modalIdEl && modalIdEl.innerText.includes(data.booking_id)) {
                    const modalBadge = document.getElementById('modalStatus');
                    if (modalBadge && data.new_status) {
                        modalBadge.innerText = data.status_label || data.new_status;
                        modalBadge.className = 'premium-status-badge ' + (data.status_class || '');
                        
                        // If the status changed, we might need to refresh action buttons
                        if (typeof window.showBookingDetails === 'function') {
                            window.showBookingDetails(data.booking_id);
                        }
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
            } else if (data.type === 'chat_message') {
                updateChatBadge();
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
            const parts = value.trim().split(/\s+/);
            if (parts.length >= 2) {
                const first = parts[0].toLowerCase();
                const last = parts[parts.length - 1].toLowerCase();
                if (first === last && first.length > 2) {
                    error = 'First name and surname cannot be identical.';
                }
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
            if (window.showToast) window.showToast(data.message || "Action completed", "success");
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

// ─── Global Logout Handler ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
    const logoutLinks = document.querySelectorAll('.logout-link');
    logoutLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const logoutUrl = this.getAttribute('href') || '/auth/logout';
            
            const doLogout = () => {
                window.location.href = logoutUrl;
            };

            if (typeof window.showConfirm === 'function') {
                window.showConfirm('Are you sure you want to log out?', doLogout, 'Logout', 'Yes, Logout');
            } else if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: 'Logout',
                    text: 'Are you sure you want to log out?',
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonColor: 'var(--primary-color, #f97316)',
                    cancelButtonColor: '#94a3b8',
                    confirmButtonText: 'Yes, Logout'
                }).then((result) => {
                    if (result.isConfirmed) doLogout();
                });
            } else {
                if (confirm('Are you sure you want to log out?')) doLogout();
            }
        });
    });
});
