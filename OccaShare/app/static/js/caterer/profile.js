document.addEventListener('DOMContentLoaded', function () {
    const calendarEl = document.getElementById('availabilityCalendar');
    if (calendarEl) {
        const catererId = calendarEl.dataset.catererId;
        const calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: ''
            },
            events: `/caterer/api/events?caterer_id=${catererId}`,
            height: 'auto',
            dayMaxEvents: true,
            themeSystem: 'standard',
            eventDidMount: function (info) {
                if (info.event.title === 'BLOCKED') {
                    info.el.classList.add('blocked-date');
                }
            }
        });
        calendar.render();
    }
});

function startBooking(catererId, packageId = null) {
    let url = `/bookings/start/${catererId}`;
    if (packageId) {
        url += `?package_id=${packageId}`;
    }
    window.location.href = url;
}

// Global exposure
window.startBooking = startBooking;
