with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the function boundaries
fn_start = content.find('function updateSidebarForDate(dateStr)')
fn_end_marker = '\n}\n'
fn_end = content.find(fn_end_marker, fn_start) + len(fn_end_marker)

old_fn = content[fn_start:fn_end]
print(f"Found function at {fn_start}-{fn_end}, length: {len(old_fn)}")

new_fn = '''function updateSidebarForDate(dateStr) {
    var dateObj = new Date(dateStr + 'T00:00:00');
    var options = { weekday: 'long', month: 'long', day: 'numeric' };
    var dateFormatted = dateObj.toLocaleDateString('en-US', options);

    var labelEl = document.getElementById('sidebarSelectedDateStr');
    if (labelEl) labelEl.innerText = dateFormatted;

    var events = [];
    if (window.fullCalendarInstance) {
        events = window.fullCalendarInstance.getEvents().filter(function(e) {
            if (!e.start) return false;
            var eDateStr = new Date(e.start.getTime() - (e.start.getTimezoneOffset() * 60000)).toISOString().split('T')[0];
            return eDateStr === dateStr;
        });
    }

    var sidebarDayEvents = document.getElementById('sidebarDayEvents');
    if (!sidebarDayEvents) return;
    sidebarDayEvents.innerHTML = '';

    if (events.length === 0) {
        sidebarDayEvents.innerHTML = '<div class="empty-state"><i class="fas fa-calendar-day"></i><span>No events on this date.</span></div>';
    } else {
        events.forEach(function(e) {
            var timeStr = 'All Day';
            try {
                if (!e.allDay && e.start) {
                    timeStr = e.start.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                }
            } catch(err) {}

            var color = '#3b82f6';
            var icon = 'fa-calendar-day';
            var rType = (e.extendedProps && e.extendedProps.recordType) ? e.extendedProps.recordType : 'booking';

            if (e.title === 'BLOCKED') { icon = 'fa-ban'; color = '#ef4444'; }
            else if (rType === 'preparation') { icon = 'fa-utensils'; color = '#0ea5e9'; }
            else if (rType === 'task') { icon = 'fa-tasks'; color = '#8b5cf6'; }
            else if (rType === 'reminder') { icon = 'fa-bell'; color = '#f59e0b'; }
            else { color = e.backgroundColor || '#10b981'; }

            var item = document.createElement('div');
            item.className = 'sidebar-event-item';
            item.innerHTML =
                '<span class="sidebar-event-dot" style="background:' + color + ';"></span>' +
                '<span class="sidebar-event-name"><i class="fas ' + icon + '" style="color:' + color + '; margin-right:4px; font-size:0.75rem;"></i>' + (e.title || 'Event') + '</span>' +
                '<span class="sidebar-event-time">' + timeStr + '</span>';

            item.addEventListener('click', function() {
                if (typeof showEventDetails === 'function') showEventDetails(e);
            });
            sidebarDayEvents.appendChild(item);
        });
    }

    var blockInput = document.getElementById('blockDate');
    if (blockInput) {
        blockInput.value = dateStr;
        if (typeof checkAvailabilityStatus === 'function') checkAvailabilityStatus(dateStr);
    }

    var maxCap = parseInt(((document.getElementById('capMaxBookings') || {}).value) || '5');
    var bookingCount = events.filter(function(e) {
        return e.title !== 'BLOCKED' &&
               e.extendedProps && e.extendedProps.recordType !== 'task' &&
               e.extendedProps.recordType !== 'reminder' &&
               e.extendedProps.recordType !== 'preparation';
    }).length;
    var isBlocked = events.some(function(e) { return e.title === 'BLOCKED'; });

    var statusBox = document.getElementById('sidebarAvailabilityStatus');
    if (statusBox) {
        if (isBlocked) {
            statusBox.innerHTML = '<i class="fas fa-times-circle"></i> Blocked';
            statusBox.style.color = '#ef4444';
        } else if (bookingCount >= maxCap) {
            statusBox.innerHTML = '<i class="fas fa-exclamation-circle"></i> Fully Booked (' + bookingCount + '/' + maxCap + ')';
            statusBox.style.color = '#f59e0b';
        } else {
            statusBox.innerHTML = '<i class="fas fa-check-circle"></i> Available (' + bookingCount + '/' + maxCap + ' Bookings)';
            statusBox.style.color = '#10b981';
        }
    }
}
'''

new_content = content[:fn_start] + new_fn + content[fn_end:]

with open('app/static/js/caterer/calendar.js', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Fixed updateSidebarForDate!")
print(f"New file length: {len(new_content)}")
