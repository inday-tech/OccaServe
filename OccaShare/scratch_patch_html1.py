import re

with open('templates/caterer/bookings.html', 'r', encoding='utf-8') as f:
    html = f.read()

edit_modal_html = """
<!-- Edit Booking Modal -->
<div id="editBookingModal" class="occ-modal-overlay" style="z-index: 1200;">
    <div class="occ-modal-box sz-md occ-content-pop">
        <div class="occ-modal-header glass-header">
            <h3 class="occ-modal-title"><i class="fas fa-edit" style="margin-right: 8px;"></i> Edit Booking Details</h3>
            <button class="occ-modal-close" onclick="closeModal('editBookingModal')"><i class="fas fa-times"></i></button>
        </div>
        <div class="occ-modal-body" style="padding: 1.5rem;">
            <form id="editBookingForm" onsubmit="submitEditBooking(event)">
                <input type="hidden" id="editBookingId">
                <input type="hidden" id="editBookingOriginalStatus">
                
                <div class="form-group-pro">
                    <label class="cal-label">Customer Name</label>
                    <input type="text" id="editCustomerName" class="control-pro" required>
                </div>
                
                <div style="display: flex; gap: 1rem;">
                    <div class="form-group-pro" style="flex: 1;">
                        <label class="cal-label">Event Date</label>
                        <input type="date" id="editEventDate" class="control-pro" required>
                    </div>
                    <div class="form-group-pro" style="flex: 1;">
                        <label class="cal-label">Event Time</label>
                        <input type="time" id="editEventTime" class="control-pro" required>
                    </div>
                </div>
                
                <div class="form-group-pro">
                    <label class="cal-label">Venue Location</label>
                    <input type="text" id="editVenue" class="control-pro" required>
                </div>
                
                <div class="form-group-pro">
                    <label class="cal-label">Guest Count</label>
                    <input type="number" id="editGuestCount" class="control-pro" min="1" required>
                </div>
                
                <!-- Reason for Modification (required if confirmed) -->
                <div id="editReasonContainer" class="form-group-pro" style="display: none; background: #fffbeb; padding: 1rem; border-radius: 8px; border: 1px solid #fde68a;">
                    <label class="cal-label" style="color: #92400e;"><i class="fas fa-exclamation-circle"></i> Reason for Modification (Required for confirmed bookings)</label>
                    <textarea id="editModificationReason" class="control-pro" style="min-height: 80px;" placeholder="e.g. Customer requested a change of venue"></textarea>
                </div>
                
                <button type="submit" class="btn-primary-pro" id="btnSubmitEdit" style="width: 100%; justify-content: center; margin-top: 1rem;">
                    Save Changes
                </button>
            </form>
        </div>
    </div>
</div>
"""

if "editBookingModal" not in html:
    idx = html.find('{% endblock %}')
    html = html[:idx] + edit_modal_html + "\n" + html[idx:]
    with open('templates/caterer/bookings.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Injected editBookingModal into bookings.html")
else:
    print("editBookingModal already exists in bookings.html")
