with open('app/static/js/caterer/bookings.js', 'r', encoding='utf-8') as f:
    js = f.read()

new_js = """
// ─── PHASE 2: EDIT BOOKING & PREPARATION ──────────────────────────────────────────

window.openEditBookingModal = function() {
    if (!currentBookingId) return;
    
    // Fetch current booking data
    fetch(`/caterer/api/bookings/${currentBookingId}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('editBookingId').value = data.id;
            document.getElementById('editBookingOriginalStatus').value = data.status;
            
            document.getElementById('editCustomerName').value = data.customerName || data.customer;
            document.getElementById('editEventDate').value = data.date;
            document.getElementById('editEventTime').value = data.time || '00:00';
            document.getElementById('editVenue').value = data.venue;
            document.getElementById('editGuestCount').value = data.guests;
            
            const reasonContainer = document.getElementById('editReasonContainer');
            const reasonInput = document.getElementById('editModificationReason');
            
            if (['confirmed', 'preparing', 'on_the_way', 'in_progress', 'ready_for_pickup', 'ready_for_delivery'].includes(data.status)) {
                reasonContainer.style.display = 'block';
                reasonInput.required = true;
            } else {
                reasonContainer.style.display = 'none';
                reasonInput.required = false;
                reasonInput.value = '';
            }
            
            window.openModal('editBookingModal');
        })
        .catch(err => alert("Error fetching booking details: " + err));
};

window.submitEditBooking = async function(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSubmitEdit');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    
    const id = document.getElementById('editBookingId').value;
    const data = {
        customer_name: document.getElementById('editCustomerName').value,
        event_date: document.getElementById('editEventDate').value,
        event_time: document.getElementById('editEventTime').value,
        venue_address: document.getElementById('editVenue').value,
        guest_count: document.getElementById('editGuestCount').value,
        reason: document.getElementById('editModificationReason').value
    };
    
    try {
        const res = await window.apiAction(`/caterer/api/bookings/${id}/edit`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (res) {
            window.closeModal('editBookingModal');
            if (window.showSuccess) window.showSuccess('Booking updated successfully.');
            // Refresh modal
            window.openBookingDetailModal(id);
        }
    } catch(err) {
        alert("Error saving booking: " + err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Save Changes';
    }
};

window.setPreparationDate = async function(bookingId) {
    const dateInput = document.getElementById(`prepDateInput_${bookingId}`);
    if (!dateInput || !dateInput.value) {
        alert("Please select a preparation date first.");
        return;
    }
    
    try {
        const res = await window.apiAction(`/caterer/api/bookings/${bookingId}/prep-date`, {
            method: 'POST',
            body: JSON.stringify({ preparation_date: dateInput.value })
        });
        if (res) {
            if (window.showSuccess) window.showSuccess('Preparation lead time scheduled.');
            window.openBookingDetailModal(bookingId);
        }
    } catch(err) {
        alert("Error setting prep date: " + err);
    }
};
"""

if "openEditBookingModal" not in js:
    with open('app/static/js/caterer/bookings.js', 'a', encoding='utf-8') as f:
        f.write("\n" + new_js)
    print("Injected Phase 2 JS into bookings.js")
else:
    print("Phase 2 JS already exists in bookings.js")
