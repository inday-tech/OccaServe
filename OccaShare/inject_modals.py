with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Load eventModal from extracted_modals.html
with open('extracted_modals.html', 'r', encoding='utf-8') as f:
    modals = f.read()

# get only eventModal
end_idx = modals.find('<!-- WALK-IN BOOKING MODAL -->')
if end_idx != -1:
    event_modal = modals[:end_idx]
else:
    event_modal = modals

availability_modal = '''
<!-- Manage Availability Modal -->
<div id="availabilityModal" class="occ-modal-overlay">
    <div class="occ-modal-box sz-sm occ-content-pop">
        <div class="occ-modal-header glass-header">
            <h3 class="occ-modal-title"><i class="fas fa-cog" style="margin-right: 8px;"></i> Availability Settings</h3>
            <button class="occ-modal-close" onclick="closeModal('availabilityModal')"><i class="fas fa-times"></i></button>
        </div>
        <div class="occ-modal-body" style="padding: 1.5rem;">
            <div class="cal-form-stack">
                <div class="form-group-pro">
                    <label class="cal-label">Selected Date</label>
                    <input type="date" id="blockDate" class="control-pro" readonly>
                </div>
                
                <h4 style="font-size: 0.95rem; font-weight: 700; margin: 1rem 0 0.5rem 0; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem;">Block / Unblock Date</h4>
                <div class="form-group-pro">
                    <label class="cal-label">Reason (if blocking)</label>
                    <input type="text" id="blockReason" class="control-pro" placeholder="e.g. Venue maintenance">
                </div>
                <div style="display: flex; gap: 0.5rem; margin-bottom: 1.5rem;">
                    <button onclick="toggleDateAvailability(false)" class="btn-primary-pro" style="flex:1; background: #ef4444; border-color: #ef4444; justify-content:center;">Block Date</button>
                    <button onclick="toggleDateAvailability(true)" class="btn-secondary-pro" style="flex:1; justify-content:center;">Unblock Date</button>
                </div>

                <h4 style="font-size: 0.95rem; font-weight: 700; margin: 1rem 0 0.5rem 0; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem;">Global Capacity Settings</h4>
                <div class="form-group-pro">
                    <label class="cal-label">Max Bookings Per Day</label>
                    <input type="number" id="capMaxBookings" class="control-pro" value="5" min="1">
                </div>
                <div class="form-group-pro" style="display: flex; align-items: center; gap: 8px;">
                    <input type="checkbox" id="capAutoBlock" style="width: 18px; height: 18px; cursor: pointer;" checked>
                    <label for="capAutoBlock" class="cal-label" style="margin-bottom: 0;">Auto-block when capacity reached</label>
                </div>
                <button onclick="updateCapacitySettings()" class="btn-primary-pro" style="width: 100%; justify-content:center; margin-top: 0.5rem;">Save Capacity Limits</button>
            </div>
        </div>
    </div>
</div>
'''

insert_idx = html.find('<!-- Add Schedule Modal -->')
if insert_idx != -1:
    new_html = html[:insert_idx] + event_modal + '\n' + availability_modal + '\n' + html[insert_idx:]
    with open('templates/caterer/calendar.html', 'w', encoding='utf-8') as f:
        f.write(new_html)
    print("Injected successfully.")
else:
    print("Could not find insertion point.")
