import re

with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    js = f.read()

# 1. Replace openManualBookingModal()
js = js.replace('openManualBookingModal();', 'openExternalBookingModal();')

# 2. Add InternalSchedule hooks
old_hook_1 = """                if (info.event.extendedProps.type === 'BLOCKED') {
                    showBlockedDetails(info.event);
                } else {
                    showEventDetails(info.event);
                }"""
new_hook_1 = """                if (info.event.extendedProps.type === 'BLOCKED') {
                    showBlockedDetails(info.event);
                } else if (info.event.extendedProps.customer === 'Internal') {
                    window.showInternalScheduleDetails(info.event);
                } else {
                    showEventDetails(info.event);
                }"""
js = js.replace(old_hook_1, new_hook_1)

old_hook_2 = """                if (event.title === 'BLOCKED') {
                    showBlockedDetails(event);
                } else {
                    showEventDetails(event);
                }"""
new_hook_2 = """                if (event.title === 'BLOCKED') {
                    showBlockedDetails(event);
                } else if (event.extendedProps.customer === 'Internal') {
                    window.showInternalScheduleDetails(event);
                } else {
                    showEventDetails(event);
                }"""
js = js.replace(old_hook_2, new_hook_2)

# 3. Append the correct Schedule Modal JS
new_schedule_logic = """
window.openAddScheduleModal = function() {
    document.getElementById('addScheduleForm').reset();
    document.getElementById('schedId').value = '';
    
    const titleEl = document.querySelector('#addScheduleModal .occ-modal-title');
    if (titleEl) titleEl.innerHTML = '<i class="fas fa-calendar-plus" style="margin-right: 8px;"></i> Add Internal Schedule';
    
    document.getElementById('schedOtherContainer').style.display = 'none';
    
    const modal = document.getElementById('addScheduleModal');
    if (modal) {
        modal.style.display = 'flex';
        setTimeout(() => modal.classList.add('active'), 10);
    }
};

window.submitAddSchedule = async function(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSubmitSchedule');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    }
    
    let schedType = document.getElementById('schedType').value;
    if (schedType === 'other') {
        schedType = document.getElementById('schedOtherType').value || 'Other';
    }
    
    const data = {
        id: document.getElementById('schedId') ? document.getElementById('schedId').value : '',
        type: schedType,
        title: document.getElementById('schedTitle').value,
        date: document.getElementById('schedDate').value,
        time: document.getElementById('schedTime').value,
        pin: document.getElementById('schedPin') ? document.getElementById('schedPin').checked : false
    };
    
    try {
        const res = await fetch('/caterer/api/schedule/add', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        const result = await res.json();
        
        if (res.ok) {
            if (window.showToast) {
                window.showToast(result.message || 'Schedule saved successfully.', 'success');
            } else {
                alert(result.message || 'Schedule saved successfully.');
            }
            closeModal('addScheduleModal');
            closeModal('internalScheduleViewModal');
            if (window.fullCalendarInstance) {
                window.fullCalendarInstance.refetchEvents();
            }
            if (typeof refreshUpcomingBookings === 'function') refreshUpcomingBookings();
        } else {
            if (window.showToast) {
                window.showToast(result.detail || 'Error saving schedule', 'error');
            } else {
                alert(result.detail || 'Error saving schedule');
            }
        }
    } catch(err) {
        alert("Connection error: " + err);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-save"></i> Save Schedule';
        }
    }
};

window.showInternalScheduleDetails = function(event) {
    const modal = document.getElementById('internalScheduleViewModal');
    if (!modal) return;
    
    document.getElementById('viewScheduleTitle').innerText = event.title;
    document.getElementById('viewScheduleDate').innerText = event.start.toLocaleDateString('en-US', {weekday:'short', year:'numeric', month:'short', day:'numeric'});
    if (event.start.getHours() || event.start.getMinutes()) {
        document.getElementById('viewScheduleTime').innerText = event.start.toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit'});
        document.getElementById('viewScheduleTimeContainer').style.display = 'block';
    } else {
        document.getElementById('viewScheduleTimeContainer').style.display = 'none';
    }
    document.getElementById('viewScheduleType').innerText = event.extendedProps.eventType;
    document.getElementById('viewSchedulePin').innerText = event.extendedProps.isPinned ? "Pinned to Dashboard" : "Not Pinned";
    
    // Store data for editing
    document.getElementById('editScheduleBtn').onclick = function() {
        if (document.getElementById('schedId')) document.getElementById('schedId').value = event.extendedProps.internalId;
        
        // Try to match dropdown type
        const sType = event.extendedProps.eventType;
        const select = document.getElementById('schedType');
        let matched = false;
        if (select) {
            for (let i = 0; i < select.options.length; i++) {
                if (select.options[i].value === sType) {
                    select.value = sType;
                    matched = true;
                    break;
                }
            }
            if (!matched) {
                select.value = 'other';
                document.getElementById('schedOtherContainer').style.display = 'block';
                document.getElementById('schedOtherType').value = sType;
            } else {
                document.getElementById('schedOtherContainer').style.display = 'none';
            }
        }
        
        let titleOnly = event.title;
        if (titleOnly.includes(' (')) titleOnly = titleOnly.substring(0, titleOnly.lastIndexOf(' ('));
        document.getElementById('schedTitle').value = titleOnly;
        
        const offsetDate = new Date(event.start.getTime() - (event.start.getTimezoneOffset() * 60000));
        document.getElementById('schedDate').value = offsetDate.toISOString().split('T')[0];
        
        if (event.start.getHours() || event.start.getMinutes()) {
            document.getElementById('schedTime').value = event.start.toTimeString().substring(0,5);
        } else {
            document.getElementById('schedTime').value = '';
        }
        
        if (document.getElementById('schedPin')) document.getElementById('schedPin').checked = event.extendedProps.isPinned;
        
        const titleEl = document.querySelector('#addScheduleModal .occ-modal-title');
        if (titleEl) titleEl.innerHTML = '<i class="fas fa-edit" style="margin-right: 8px;"></i> Edit Internal Schedule';
        
        closeModal('internalScheduleViewModal');
        const m = document.getElementById('addScheduleModal');
        if (m) {
            m.style.display = 'flex';
            setTimeout(() => m.classList.add('active'), 10);
        }
    };
    
    modal.style.display = 'flex';
    setTimeout(() => modal.classList.add('active'), 10);
};
"""

js += new_schedule_logic

with open('app/static/js/caterer/calendar.js', 'w', encoding='utf-8') as f:
    f.write(js)
print("Successfully modified calendar.js")
