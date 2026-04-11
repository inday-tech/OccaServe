// Dashboard-specific WebSocket client for booking updates
document.addEventListener('DOMContentLoaded', function () {
    const dashboardClientId = document.body.dataset.clientId;
    if (dashboardClientId) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const dashWs = new WebSocket(`${protocol}//${window.location.host}/ws/${dashboardClientId}`);

        dashWs.onmessage = function (event) {
            const data = JSON.parse(event.data);
            if (data.type === 'booking_update') {
                if (window.showToast) window.showToast("Real-time Update: " + data.message, "info"); else alert("Real-time Update: " + data.message);
                setTimeout(() => window.location.reload(), 2000);
            }
        };
    }
});
