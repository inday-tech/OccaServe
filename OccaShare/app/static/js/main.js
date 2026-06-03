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
        position: 'bottom-end',
        showConfirmButton: false,
        timer: 3500,
        timerProgressBar: true,
        background: '#ffffff',
        color: '#1e293b',
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

// --- 3.5 Global Alert Modals (Premium Design) ---
window.showError = function(message, title = 'Error') {
    Swal.fire({
        title: title,
        html: message,
        icon: 'error',
        confirmButtonText: 'Understood',
        confirmButtonColor: '#1e293b',
        customClass: {
            popup: 'premium-swal-popup',
            confirmButton: 'premium-swal-btn'
        }
    });
};

window.showAlert = function(options) {
    Swal.fire({
        title: options.title || 'Message',
        html: options.message,
        icon: options.type || 'info',
        confirmButtonText: 'OK',
        confirmButtonColor: 'var(--primary-color, #10b981)',
        customClass: {
            popup: 'premium-swal-popup',
            confirmButton: 'premium-swal-btn'
        }
    });
};

window.showConfirm = function(message, onConfirm, title = 'Are you sure?', confirmText = 'Yes', type = 'danger') {
    const theme = {
        danger:  { bg: '#ef4444', icon: 'fa-exclamation-triangle', tint: '#fef2f2', border: '#fecaca', text: '#7f1d1d' },
        success: { bg: '#10b981', icon: 'fa-check-circle',        tint: '#ecfdf5', border: '#a7f3d0', text: '#064e3b' },
        warning: { bg: '#f59e0b', icon: 'fa-exclamation-circle',  tint: '#fffbeb', border: '#fde68a', text: '#78350f' },
        primary: { bg: '#3b82f6', icon: 'fa-info-circle',         tint: '#eff6ff', border: '#bfdbfe', text: '#1e3a8a' }
    }[type] || { bg: '#ef4444', icon: 'fa-exclamation-triangle', tint: '#fef2f2', border: '#fecaca', text: '#7f1d1d' };

    let overlay = document.getElementById('globalConfirmModalOverlay');
    if (overlay) { overlay.remove(); }

    const html = `
    <div id="globalConfirmModalOverlay" class="occ-modal-overlay active" style="z-index: 99999; animation: fadeIn 0.2s ease-out; position: fixed; inset: 0; background: rgba(15,23,42,0.6); display: flex; align-items: center; justify-content: center; backdrop-filter: blur(4px);">
        <div class="occ-modal-box sz-sm occ-content-pop" style="font-family: 'Poppins', sans-serif; border-radius: 12px; overflow: hidden; max-width: 450px; width: 90%; background: white; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.2); transform: scale(1); transition: all 0.2s;">
            <div class="occ-modal-header" style="background: ${theme.bg}; padding: 1.5rem; color: white !important; display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h3 class="occ-modal-title" style="margin: 0; font-size: 1.25rem; font-weight: 700; color: white !important;">${title}</h3>
                    <div class="occ-modal-subtitle" style="font-size: 0.85rem; opacity: 0.9; margin-top: 0.25rem; color: white !important;">Please confirm this action.</div>
                </div>
                <button onclick="document.getElementById('globalConfirmModalOverlay').remove()" class="occ-modal-close" style="background: rgba(255,255,255,0.2); border: none; color: white; width: 32px; height: 32px; border-radius: 50%; cursor: pointer;">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="compact-body" style="padding: 1.5rem; background: white;">
                <div style="display: flex; gap: 1rem; align-items: flex-start; padding: 1rem; background: ${theme.tint}; border: 1px solid ${theme.border}; border-radius: 8px;">
                    <div style="color: ${theme.bg}; font-size: 1.5rem; margin-top: 2px;"><i class="fas ${theme.icon}"></i></div>
                    <div style="flex: 1;">
                        <p style="margin: 0; color: ${theme.text}; font-size: 0.9rem; line-height: 1.5;">
                            ${message}
                        </p>
                    </div>
                </div>
            </div>
            <div class="occ-modal-footer" style="padding: 1.25rem 1.5rem; background: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end; gap: 12px;">
                <button type="button" class="btn-secondary" onclick="document.getElementById('globalConfirmModalOverlay').remove()" style="background: #e2e8f0; color: #475569; border: none; padding: 0.75rem 1.5rem; border-radius: 8px; font-weight: 700; cursor: pointer; font-family: 'Poppins', sans-serif;">Cancel</button>
                <button type="button" class="btn-primary" id="globalConfirmConfirmBtn" style="background: ${theme.bg}; border: none; color: white; padding: 0.75rem 1.5rem; border-radius: 8px; font-weight: 700; cursor: pointer; font-family: 'Poppins', sans-serif; box-shadow: 0 4px 12px rgba(0,0,0,0.1); transition: transform 0.1s;">${confirmText}</button>
            </div>
        </div>
    </div>`;
    
    document.body.insertAdjacentHTML('beforeend', html);
    let newOverlay = document.getElementById('globalConfirmModalOverlay');

    document.getElementById('globalConfirmConfirmBtn').onclick = function () {
        this.style.transform = 'scale(0.95)';
        setTimeout(() => {
            newOverlay.remove();
            if (onConfirm) onConfirm();
        }, 100);
    };
};

// --- 4. Global URL Parameter Listener for Toasts ---
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const hashParams = new URLSearchParams(window.location.hash.includes('?') ? window.location.hash.split('?')[1] : '');
    
    const getParam = (name) => urlParams.get(name) || hashParams.get(name);

    const loginStatus = getParam('login');
    const verifiedStatus = getParam('verified');
    const logoutStatus = getParam('logout');
    const successMsg = getParam('success_msg');
    const errorMsg = getParam('error_msg');
    const alertMsg = getParam('alert_msg');

    let shouldClean = false;

    // A. Login & Verification Success
    if (loginStatus === 'success' || verifiedStatus === 'success') {
        window.showToast('Login Successful! Welcome back.', 'success');
        shouldClean = true;
    } 
    // B. Logout Success
    else if (logoutStatus === 'success') {
        window.showToast('Logout Successful! See you soon.', 'success');
        shouldClean = true;
    }

    // C. Generic Success Messages
    if (successMsg) {
        window.showToast(decodeURIComponent(successMsg), 'success');
        shouldClean = true;
    }
    
    // D. Generic Error Messages
    if (errorMsg) {
        window.showToast(decodeURIComponent(errorMsg), 'error');
        shouldClean = true;
    }

    // E. Generic Info Alerts (Modal)
    if (alertMsg && window.showAlert) {
        window.showAlert({
            title: 'Message',
            message: decodeURIComponent(alertMsg),
            type: 'info'
        });
        shouldClean = true;
    }

    // F. Platform Feedback Success
    if (getParam('feedback') === 'success') {
        window.showToast('Thank you for your feedback!', 'success');
        shouldClean = true;
    }

    // Cleanup URL parameters to prevent toast from showing again on refresh
    if (shouldClean) {
        const url = new URL(window.location.href);
        const paramsToRemove = ['login', 'logout', 'success_msg', 'error_msg', 'alert_msg', 'verified', 'feedback'];
        paramsToRemove.forEach(p => {
            url.searchParams.delete(p);
            // Also handle hash if needed (less common for cleaning)
        });
        window.history.replaceState({}, document.title, url.pathname + url.search + url.hash);
    }
});

// ========================================== 
// GLOBAL NOTIFICATION ENGINE 
// ========================================== 
window.knownGlobalNotifIds = new Set();
let globalNotifTimer = null;

window.fetchGlobalNotifications = async function(isForced = false) {
    try {
        const response = await fetch('/api/notifications?limit=20');
        if (!response.ok) return;
        const data = await response.json();

        // 1. Update UI Badges
        const badge = document.getElementById('nav-notif-badge');
        const dropBadge = document.getElementById('dropdown-notif-badge');
        if (badge) {
            badge.style.display = data.unread_count > 0 ? 'flex' : 'none';
            badge.textContent = data.unread_count > 99 ? '99+' : data.unread_count;
        }
        if (dropBadge) {
            dropBadge.style.display = data.unread_count > 0 ? 'inline-block' : 'none';
            dropBadge.textContent = data.unread_count > 99 ? '99+ NEW' : data.unread_count + ' NEW';
        }

        // 2. Render Dropdown Container
        const container = document.getElementById('headerNotifContainer');
        if (!container) return;

        if (data.notifications.length === 0) {
            container.innerHTML = `<div style="text-align: center; padding: 2.5rem 1rem;"><div style="background: #f1f5f9; width: 56px; height: 56px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 12px;"><i class="fas fa-check-double" style="color: #94a3b8; font-size: 1.5rem;"></i></div><p style="margin: 0; font-size: 0.9rem; font-weight: 600; color: #1e293b;">You're all caught up!</p><p style="margin: 4px 0 0; font-size: 0.75rem; color: #64748b;">No new notifications</p></div>`;
        } else {
            let htmlString = '';
            const topNotifs = data.notifications.slice(0, 5);
            topNotifs.forEach(notif => {
                const iconMap = {
                    'Booking': { i: 'fa-calendar-check', c: '#10b981', bg: '#d1fae5' },
                    'Payment': { i: 'fa-wallet', c: '#0ea5e9', bg: '#e0f2fe' },
                    'Review': { i: 'fa-star', c: '#f59e0b', bg: '#fef3c7' },
                    'Verification': { i: 'fa-shield-check', c: '#8b5cf6', bg: '#ede9fe' },
                    'Customer': { i: 'fa-user-plus', c: '#ec4899', bg: '#fce7f3' }
                };
                const info = iconMap[notif.type] || { i: 'fa-bell', c: '#64748b', bg: '#f1f5f9' };
                const isUnread = !notif.is_read;
                const timeStr = new Date(notif.created_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
                htmlString += `<a href="javascript:void(0)" onclick="handleGlobalNotifClick(${notif.id}, '${notif.link || ''}', ${isUnread})" style="display: flex; gap: 12px; padding: 16px; text-decoration: none; border-bottom: 1px solid #e2e8f0; background: ${isUnread ? '#f8fafc' : 'white'}; transition: all 0.2s; align-items: flex-start; position: relative;"><div style="background: ${info.bg}; color: ${info.c}; width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 1rem; box-shadow: ${isUnread ? '0 4px 12px rgba(0,0,0,0.05)' : 'none'};"><i class="fas ${info.i}"></i></div><div style="flex: 1; overflow: hidden; padding-top: 2px;"><p style="margin: 0 0 4px 0; font-size: 0.85rem; color: #0f172a; font-weight: ${isUnread ? '700' : '500'}; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${notif.message}</p><p style="margin: 0; font-size: 0.7rem; color: #64748b; font-weight: 600;"><i class="far fa-clock" style="margin-right: 4px;"></i>${timeStr}</p></div>${isUnread ? '<div style="width: 8px; height: 8px; background: #ef4444; border-radius: 50%; position: absolute; top: 16px; right: 16px; box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.1);"></div>' : ''}</a>`;
            });
            container.innerHTML = htmlString;
        }

        // 3. Broadcast to Notifications Page if it exists
        if (window.syncLocalNotificationsPage) {
            window.syncLocalNotificationsPage(data.notifications, data.unread_count);
        }
    } catch (err) {
        console.error("Global Notif Error:", err);
    }
}

window.handleGlobalNotifClick = async function(id, link, isUnread) {
    if (isUnread) {
        try {
            await fetch(`/api/notifications/${id}/read`, { method: 'POST' });
            window.fetchGlobalNotifications(true);
        } catch(e) {}
    }
    if (link) window.location.href = link;
}


window.markAllAsReadGlobal = async function() {
    try {
        await fetch('/api/notifications/read-all', { method: 'POST' });
        window.fetchGlobalNotifications(true);
    } catch(e) {}
}

window.addEventListener('load', () => {
    if (document.getElementById('headerNotifContainer')) {
        window.fetchGlobalNotifications();
        globalNotifTimer = setInterval(() => window.fetchGlobalNotifications(), 15000);
    }
});


// ========================================== 
// GLOBAL DROPDOWN TOGGLE ENGINE 
// ========================================== 
window.toggleHeaderDropdown = function(dropdownId, triggerEl) {
    const dropdown = document.getElementById(dropdownId);
    if (!dropdown) return;
    
    const isActive = dropdown.classList.contains('active');
    
    // Close all other dropdowns
    document.querySelectorAll('.premium-dropdown, .profile-dropdown, .hdr-dropdown').forEach(d => {
        d.classList.remove('active');
        d.style.display = 'none';
    });
    document.querySelectorAll('.hdr-btn, .header-action-btn, .profile-trigger, .header-profile-chip, .hdr-profile-chip').forEach(t => {
        t.classList.remove('active');
    });

    if (!isActive) {
        dropdown.style.display = 'block';
        setTimeout(() => {
            dropdown.classList.add('active');
            if (triggerEl) triggerEl.classList.add('active');
        }, 10);
        
        if (dropdownId === 'notificationsDropdown' && window.fetchGlobalNotifications) {
            window.fetchGlobalNotifications();
        }
    }
};

window.addEventListener('click', function(e) {
    if (!e.target.closest('.header-dropdown-wrapper') && !e.target.closest('.header-profile-section')) {
        document.querySelectorAll('.premium-dropdown, .profile-dropdown, .hdr-dropdown').forEach(d => {
            d.classList.remove('active');
            setTimeout(() => {
                if (!d.classList.contains('active')) d.style.display = 'none';
            }, 300);
        });
        document.querySelectorAll('.hdr-btn, .header-action-btn, .profile-trigger, .header-profile-chip, .hdr-profile-chip').forEach(t => {
            t.classList.remove('active');
        });
    }
});

