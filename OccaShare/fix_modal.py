import re

with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

add_schedule_modal = '''
<!-- Add Schedule Modal -->
<div id="addScheduleModal" class="modal-overlay" style="display: none; align-items: center; justify-content: center;">
    <div class="modal-content" style="max-width: 500px; width: 90%;">
        <div class="modal-header">
            <h3>Add Internal Schedule</h3>
            <button class="modal-close" onclick="document.getElementById('addScheduleModal').style.display='none'"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body" style="padding: 1.5rem;">
            <form id="addScheduleForm" class="cal-form-stack">
                <div class="form-group-pro">
                    <label class="cal-label">Schedule Type</label>
                    <select id="schedType" class="control-pro" required>
                        <option value="task">Internal Task</option>
                        <option value="preparation">Preparation / Setup</option>
                        <option value="meeting">Supplier / Customer Meeting</option>
                        <option value="personal">Personal / Business</option>
                        <option value="other">Other</option>
                    </select>
                </div>
                <div class="form-group-pro">
                    <label class="cal-label">Title</label>
                    <input type="text" id="schedTitle" class="control-pro" placeholder="e.g. Staff briefing" required>
                </div>
                <div style="display: flex; gap: 1rem;">
                    <div class="form-group-pro" style="flex: 1;">
                        <label class="cal-label">Date</label>
                        <input type="date" id="schedDate" class="control-pro" required>
                    </div>
                    <div class="form-group-pro" style="flex: 1;">
                        <label class="cal-label">Time</label>
                        <input type="time" id="schedTime" class="control-pro">
                    </div>
                </div>
                <div class="form-group-pro" style="display: flex; align-items: center; gap: 8px;">
                    <input type="checkbox" id="schedPin" style="width: 18px; height: 18px; cursor: pointer;">
                    <label for="schedPin" class="cal-label" style="margin-bottom: 0;">? Pin to Dashboard (Important)</label>
                </div>
                <button type="button" onclick="saveSchedule()" class="btn-primary-pro" style="width: 100%; justify-content: center; margin-top: 1rem;">
                    Save Schedule
                </button>
                <div style="text-align: center; margin-top: 10px;">
                    <small style="color: #64748b;">Note: Custom schedules are saved locally for this session while database upgrades are pending.</small>
                </div>
            </form>
        </div>
    </div>
</div>
'''

if 'id="addScheduleModal"' not in html_content:
    html_content = html_content.replace('{% endblock %}', add_schedule_modal + '\n{% endblock %}')

with open('templates/caterer/calendar.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Added modal")
