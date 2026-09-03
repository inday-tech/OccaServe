import re

# 1. Add CSS for filter-btn in calendar.css
with open('app/static/css/caterer/calendar.css', 'r', encoding='utf-8') as f:
    css_content = f.read()

new_css = '''
/* Filter Buttons */
.cal-legend-bar {
    display: flex;
    gap: 0.75rem;
    padding: 0.75rem 1.25rem;
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    border: 1px solid #e2e8f0;
    align-items: center;
    overflow-x: auto;
    white-space: nowrap;
}

.filter-btn {
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #475569;
    cursor: pointer;
    transition: all 0.2s ease;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.filter-btn:hover {
    background: #e2e8f0;
}

.filter-btn.active {
    background: var(--caterer-primary-light, #eff6ff);
    border-color: var(--primary-color, #3b82f6);
    color: var(--primary-color, #3b82f6);
}

.filter-btn .pill-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
}
'''
if '.filter-btn' not in css_content:
    css_content += '\n' + new_css

with open('app/static/css/caterer/calendar.css', 'w', encoding='utf-8') as f:
    f.write(css_content)

# 2. Add 'Add Schedule' Modal to calendar.html
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
    html_content = html_content.replace('<!-- Calendar Event Details Modal -->', add_schedule_modal + '\n<!-- Calendar Event Details Modal -->')

# Update CSS version
html_content = re.sub(r'/css/caterer/calendar\.css\'\)\s*\}\}\?v=[0-9.]+', "/css/caterer/calendar.css') }}?v=12.6", html_content)

with open('templates/caterer/calendar.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Added UI and Modal")
