document.addEventListener('DOMContentLoaded', function () {
    var calendarEl = document.getElementById('bookingCalendar');
    var selectedDateInput = document.getElementById('selectedDate');
    var blockedDates = [];

    // The caterer_id is passed from the template
    const catererId = window.catererId || document.querySelector('[data-caterer-id]')?.dataset.catererId;

    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: ''
        },
        selectable: true,
        unselectAuto: false,
        events: `/caterer/api/events?caterer_id=${catererId}`,
        validRange: {
            start: new Date().toISOString().split('T')[0]
        },
        dateClick: function (info) {
            // Check if date is blocked
            const isBlocked = blockedDates.some(d => d === info.dateStr);
            if (isBlocked) {
                if (window.showError) window.showError('This date is unfortunately already booked or unavailable.', 'Date Unavailable'); else alert('This date is unfortunately already booked or unavailable.');
                return;
            }

            // Highlight selection
            document.querySelectorAll('.fc-daygrid-day').forEach(el => {
                el.style.backgroundColor = '';
            });
            info.dayEl.style.backgroundColor = '#e0e7ff';

            selectedDateInput.value = info.dateStr;
        },
        eventDidMount: function (info) {
            if (info.event.title === 'BLOCKED' || info.event.title === 'BOOKED') {
                blockedDates.push(info.event.startStr.split('T')[0]);
                info.el.classList.add('blocked-date');
            }
        }
    });
    calendar.render();
});
