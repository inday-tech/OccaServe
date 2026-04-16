document.addEventListener('DOMContentLoaded', function () {
    console.log('Dashboard Layout JS Loaded');
    
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarOverlay = document.getElementById('sidebarOverlay');

    function toggleSidebar() {
        console.log('Toggling Sidebar');
        if (sidebar && sidebarOverlay) {
            sidebar.classList.toggle('active');
            sidebarOverlay.classList.toggle('active');

            // Prevent scrolling on body when sidebar is open (mainly for mobile)
            if (sidebar.classList.contains('active')) {
                document.body.style.overflow = 'hidden';
            } else {
                document.body.style.overflow = '';
            }
        }
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            toggleSidebar();
        });
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', toggleSidebar);
    }

    // ─── Real-Time Notifications (WebSockets) ────────────────────────────────
    // Simplified WebSocket logic for global layout
    if (window.location.protocol === 'https:') {
        var ws_scheme = "wss://";
    } else {
        var ws_scheme = "ws://";
    }
    
    // Only connect if user is authenticated (can check data attribute on body)
    const clientId = document.body.dataset.clientId;
    if (clientId) {
        const ws = new WebSocket(ws_scheme + window.location.host + "/ws/" + clientId);
        

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

    function showChatNotification(data) {
        if (window.Swal) {
             Swal.fire({
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 4000,
                timerProgressBar: true,
                icon: 'info',
                title: `Message from ${data.sender_name}`,
                text: data.content.substring(0, 50) + (data.content.length > 50 ? '...' : ''),
                didClick: () => {
                    window.location.href = `/customer/messages?caterer=${data.sender_id}`;
                }
            });
        }
    }

    function showToast(data) {
        const container = document.getElementById('toast-container');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = 'toast-notification';
        toast.innerHTML = `
            <div class="toast-icon">
                <i class="fas fa-utensils"></i>
            </div>
            <div style="flex: 1;">
                <div style="font-weight: 700; margin-bottom: 0.25rem;">New Package Added!</div>
                <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 0.5rem;">
                    <strong>${data.caterer_name}</strong> just added <em>"${data.package_name}"</em>
                </div>
                <a href="/caterers/${data.caterer_id}" style="color: var(--primary-color); font-weight: 600; font-size: 0.8rem; text-decoration: none;">
                    View Package <i class="fas fa-arrow-right" style="font-size: 0.7rem; margin-left: 0.25rem;"></i>
                </a>
            </div>
            <button onclick="this.parentElement.remove()" style="background: none; border: none; color: #cbd5e1; cursor: pointer;">
                <i class="fas fa-times"></i>
            </button>
        `;
        container.appendChild(toast);

        // Auto-dismiss after 8 seconds
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 500);
        }, 8000);
    }

    // Handle logout link specifically if needed
    const logoutBtn = document.querySelector('.logout-link');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function (e) {
            // Let it proceed to /auth/logout
        });
    }
});
