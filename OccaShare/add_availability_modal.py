import re

with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

modal_html = '''
<!-- Availability Settings Modal -->
<div id="availabilitySettingsModal" class="modal-overlay" style="display: none; align-items: center; justify-content: center;">
    <div class="modal-content" style="max-width: 500px; width: 90%;">
        <div class="modal-header">
            <h3>Manage Availability & Capacity</h3>
            <button class="modal-close" onclick="document.getElementById('availabilitySettingsModal').style.display='none'"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body" style="padding: 1.5rem;">
            <!-- Block Date Section -->
            <div style="margin-bottom: 2rem;">
                <h4 style="font-size: 1rem; color: #1e293b; margin-bottom: 1rem; font-weight: 700;">Block a Date</h4>
                <form id="availabilityForm" class="cal-form-stack">
                    <div class="form-group-pro">
                        <label class="cal-label">Target Date</label>
                        <input type="date" id="blockDate" class="control-pro" required
                            min="{{ current_date.strftime('%Y-%m-%d') }}"
                            onchange="checkAvailabilityStatus(this.value)">
                    </div>

                    <div class="form-group-pro" id="blockReasonDiv" style="display: none; margin-top: -0.5rem; margin-bottom: 1rem;">
                        <label class="cal-label">Reason for Blocking</label>
                        <input type="text" id="blockReason" class="control-pro" placeholder="e.g. Fully Booked, Venue Maintenance">
                    </div>

                    <div id="availabilityStatusBox"
                        style="display: none; padding: 1rem; border-radius: var(--border-radius, 8px); margin-bottom: 1rem; font-size: 0.85rem; font-weight: 600; border: 1px solid;">
                        <i id="availabilityStatusIcon" class="fas" style="margin-right: 8px;"></i>
                        <span id="availabilityStatusText">Checking status...</span>
                    </div>

                    <div style="display: flex; gap: 10px;">
                        <button type="button" id="btnBlockDate" onclick="toggleDateAvailability(false)"
                            class="btn-primary-pro" style="flex: 1; background: var(--color-danger); display: none;">
                            Block Date
                        </button>
                        <button type="button" id="btnOpenDate" onclick="toggleDateAvailability(true)"
                            class="btn-secondary-pro" style="flex: 1; display: none;">
                            Unblock
                        </button>
                    </div>
                </form>
            </div>
            
            <hr style="border:0; border-top: 1px solid #e2e8f0; margin-bottom: 2rem;">
            
            <!-- Capacity Settings -->
            <div>
                <h4 style="font-size: 1rem; color: #1e293b; margin-bottom: 1rem; font-weight: 700;">Daily Capacity Settings</h4>
                <div class="cal-form-stack">
                    <div class="form-group-pro">
                        <label class="cal-label">Max Bookings Per Day</label>
                        <input type="number" id="capMaxBookings" class="control-pro" min="1" max="10"
                            value="{{ max_bookings_per_day }}">
                        <small style="color: #6b7280; font-size: 0.8rem;">Limit daily event capacity</small>
                    </div>
                    <div class="form-group-pro" style="display: flex; align-items: center; gap: 8px; margin-bottom: 0;">
                        <input type="checkbox" id="capAutoBlock" {% if auto_block_enabled %}checked{% endif %}
                            style="width: 18px; height: 18px; cursor: pointer;">
                        <label for="capAutoBlock" class="cal-label" style="margin-bottom: 0;">Auto-block when
                            full</label>
                    </div>
                    <button type="button" onclick="updateCapacitySettings()" class="btn-primary-pro"
                        style="width: 100%; justify-content: center; margin-top: 1.5rem;">
                        Save Capacity Settings
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>
'''

content = re.sub(r'<!-- Calendar Event Details Modal -->', modal_html + '\n<!-- Calendar Event Details Modal -->', content)

with open('templates/caterer/calendar.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Added availability modal")
