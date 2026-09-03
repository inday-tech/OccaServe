with open('app/static/js/caterer/bookings.js', 'r', encoding='utf-8') as f:
    js = f.read()

# We want to add an Edit Details button to actionsEl
patch = """
        // Edit Booking Button
        actionsEl.innerHTML += `<button onclick="window.openEditBookingModal()" class="btn-sm-outline" style="background:white; border:1px solid #cbd5e1; color:#475569; justify-content:flex-start; width:100%; margin-bottom: 8px;"><i class="fas fa-edit" style="width:16px;"></i> Edit Booking Details</button>`;
"""

if "window.openEditBookingModal()" not in js.split("if (actionsEl) {")[1]:
    idx = js.find("if (actionsEl) {")
    idx2 = js.find("actionsEl.innerHTML = '';", idx)
    
    if idx2 != -1:
        insert_idx = idx2 + len("actionsEl.innerHTML = '';")
        new_js = js[:insert_idx] + "\n" + patch + js[insert_idx:]
        with open('app/static/js/caterer/bookings.js', 'w', encoding='utf-8') as f:
            f.write(new_js)
        print("Patched bookingModalActionsTop to include Edit Details button")
    else:
        print("Could not find actionsEl.innerHTML = '';")
else:
    print("Edit Details button already in actionsEl")
