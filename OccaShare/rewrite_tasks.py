import re

with open('app/static/js/caterer/bookings.js', 'r', encoding='utf-8') as f:
    content = f.read()

new_func = \"\"\"async function loadBookingTasks(bookingId) {
    const listContainer = document.getElementById('bookingTasksList');
    const progressText = document.getElementById('checklistProgressText');
    const progressBar = document.getElementById('checklistProgressBar');
    
    if (!listContainer) return;
    
    // Status-dependent checklist titles and static tasks
    let status = window.currentBookingStatus || 'confirmed';
    let checklistTitle = 'Checklist';
    
    const staticChecklists = {
        'inquiry': {
            title: 'Inquiry Checklist',
            tasks: ['Customer details complete', 'Event details complete', 'Availability checked', 'Menu/package discussed', 'Quotation prepared', 'Quotation sent', 'Follow-up scheduled']
        },
        'tentative': {
            title: 'Confirmation Checklist',
            tasks: ['Quote accepted', 'Contract signed', 'Deposit received', 'Hold expiration checked']
        },
        'setup_ongoing': {
            title: 'Setup Checklist',
            tasks: ['Venue Arrival', 'Tables & Chairs', 'Equipment', 'Buffet Area', 'Food Setup']
        },
        'in_progress': {
            title: 'Event Monitoring',
            tasks: ['Event started', 'Issues monitored', 'Special requests handled', 'Completion confirmed']
        },
        'completed': {
            title: 'Post-Event',
            tasks: ['Final payment collected', 'Expenses recorded', 'Completion report', 'Customer feedback']
        }
    };

    if (staticChecklists[status]) {
        // Render static visual checklist
        const cl = staticChecklists[status];
        const titleEl = document.querySelector('#modalChecklistSection').previousElementSibling.querySelector('.exec-title');
        if (titleEl) titleEl.innerText = cl.title;
        
        let checkedCount = 0;
        let html = '';
        cl.tasks.forEach((t, i) => {
            // Mock random or logical checks for visual effect, or leave unchecked
            let isChecked = false;
            if (status === 'completed' || status === 'setup_ongoing' || status === 'in_progress') isChecked = true;
            if (isChecked) checkedCount++;
            html += \
            <div class="task-item-pro \" style="cursor: default;">
                <div class="task-checkbox-pro">
                    \
                </div>
                <div class="task-title" style="flex:1;">\</div>
            </div>\;
        });
        
        const progress = Math.round((checkedCount / cl.tasks.length) * 100);
        if (progressText) progressText.innerText = progress + '%';
        if (progressBar) progressBar.style.width = progress + '%';
        
        listContainer.innerHTML = html;
        return;
    }

    // Default to dynamic API tasks for Confirmed/Preparing
    const titleEl = document.querySelector('#modalChecklistSection').previousElementSibling.querySelector('.exec-title');
    if (titleEl) titleEl.innerText = (status === 'preparing') ? 'Preparation Checklist' : 'Pre-Event Checklist';

    listContainer.innerHTML = '<div style="text-align:center;padding:1rem;color:#94a3b8;"><i class="fas fa-circle-notch fa-spin"></i> Loading tasks...</div>';

    try {
        const res = await fetch(\/caterer/api/bookings/\/tasks\);
        if (!res.ok) throw new Error('Failed to load tasks');
        
        const tasks = await res.json();
        
        if (tasks.length === 0) {
            listContainer.innerHTML = '<p style="text-align:center;color:#94a3b8;font-size:0.85rem;padding:2rem;">No operational tasks found for this booking.</p>';
            if (progressText) progressText.innerText = '0%';
            if (progressBar) progressBar.style.width = '0%';
            return;
        }

        const completedCount = tasks.filter(t => t.is_completed).length;
        const progress = Math.round((completedCount / tasks.length) * 100);

        if (progressText) progressText.innerText = progress + '%';
        if (progressBar) progressBar.style.width = progress + '%';

        listContainer.innerHTML = tasks.map(task => \
            <div class="task-item-pro \" data-task-id="\">
                <div class="task-checkbox-pro" onclick="toggleTaskStatus(\)">
                    \
                </div>
                <div class="task-title" onclick="toggleTaskStatus(\)">\</div>
                <div class="btn-delete-task" onclick="deleteTask(\)">
                    <i class="fas fa-trash-alt"></i>
                </div>
            </div>
        \).join('');

    } catch (err) {
        console.error('Error loading tasks:', err);
        listContainer.innerHTML = '<p style="text-align:center;color:#ef4444;font-size:0.85rem;">Failed to load checklist.</p>';
    }
}\"\"\"

pattern = re.compile(r\"async function loadBookingTasks\(bookingId\) \{.*?\n\}\", re.DOTALL)
content = pattern.sub(new_func, content)

with open('app/static/js/caterer/bookings.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated loadBookingTasks')
