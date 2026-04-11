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
            if (modal) modal.style.display = 'flex';
        }, warningLength);

        inactivityTimeout = setTimeout(function () {
            window.location.href = '/auth/logout?reason=inactivity';
        }, timeoutLength);
    }

    if (stayBtn) {
        stayBtn.addEventListener('click', function () {
            modal.style.display = 'none';
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
    const sidebar = document.getElementById('mainSidebar');

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
        if (window.innerWidth > 768) return;
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
        if (window.innerWidth > 768 && sidebar) {
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
                if (window.location.pathname.includes('/caterer/bookings')) {
                    if (typeof window.refreshBookingsTable === 'function') {
                        window.refreshBookingsTable();
                    } else {
                        console.log("Booking update detected. Please refresh the page.");
                    }
                }
                if (window.showToast) {
                    window.showToast(`Booking Update: ${data.message || 'Status changed'}`, "success");
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

    // ─── Logout Confirmation ────────────────────────────────────────────────
    const logoutBtn = document.querySelector('.logout-link');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function (e) {
            e.preventDefault();
            const href = this.getAttribute('href');

            if (window.showConfirm) {
                window.showConfirm(
                    'Are you sure you want to log out of the Caterer panel?',
                    () => { window.location.href = href; },
                    'Ready to leave?',
                    'Yes, log out'
                );
            } else if (confirm('Are you sure you want to log out of the Caterer panel?')) {
                window.location.href = href;
            }
        });
    }
})();
