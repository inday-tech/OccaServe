with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

new_funcs = '''
window.openAddScheduleModal = function() {
    document.getElementById('addScheduleModal').style.display = 'flex';
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('schedDate').value = today;
};

window.saveSchedule = function() {
    const type = document.getElementById('schedType').value;
    const title = document.getElementById('schedTitle').value;
    const date = document.getElementById('schedDate').value;
    
    if(!title || !date) {
        showNotification('Error', 'Title and Date are required.', 'error');
        return;
    }
    
    // Add event to calendar memory
    if(window.fullCalendarInstance) {
        let color = '#3b82f6';
        if(type === 'preparation') color = '#0ea5e9';
        if(type === 'task') color = '#8b5cf6';
        if(type === 'meeting') color = '#f59e0b';
        
        window.fullCalendarInstance.addEvent({
            id: 'mock-' + Date.now(),
            title: title,
            start: date,
            backgroundColor: color,
            borderColor: color,
            extendedProps: {
                recordType: type === 'preparation' ? 'preparation' : 'task',
                customer: 'Internal'
            }
        });
        
        showNotification('Success', 'Internal schedule added successfully.', 'success');
        document.getElementById('addScheduleModal').style.display = 'none';
        document.getElementById('schedTitle').value = '';
        
        // Update sidebar
        if(typeof updateSidebarForDate === 'function') {
            updateSidebarForDate(date);
        }
    }
};

window.openManualBookingModal = function() {
    window.location.href = '/caterer/bookings?new=walkin';
};
'''

if 'openAddScheduleModal' not in js_content:
    js_content += '\n' + new_funcs

with open('app/static/js/caterer/calendar.js', 'w', encoding='utf-8') as f:
    f.write(js_content)
print("Added calendar JS functions")
