document.addEventListener('DOMContentLoaded', () => {
    const navNotifBadge = document.getElementById('nav-notif-badge');

    // Polling function (Runs every 30 seconds)
    function pollNotifications() {
        fetchNotifications(true); // silent fetch to update badge
    }

    setInterval(pollNotifications, 30000); // 30 seconds

    // Initial fetch to ensure badge is accurate
    pollNotifications();

    async function fetchNotifications(silent = false) {
        try {
            const response = await fetch('/api/notifications?limit=10');
            const data = await response.json();

            // Update badge
            if (navNotifBadge) {
                if (data.unread_count > 0) {
                    navNotifBadge.style.display = 'flex';
                    navNotifBadge.textContent = data.unread_count > 99 ? '99+' : data.unread_count;
                } else {
                    navNotifBadge.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error fetching notifications:', error);
        }
    }
});
