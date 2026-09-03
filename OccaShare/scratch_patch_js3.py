with open('app/static/js/caterer/bookings.js', 'r', encoding='utf-8') as f:
    js = f.read()

patch = """
        // Preparation Lead Time UI
        if (data.status === 'confirmed' && prepStatus === 'not_started') {
            actionsEl.innerHTML += `
                <div style="margin-top: 15px; border-top: 1px solid #e2e8f0; padding-top: 10px;">
                    <label class="cal-label" style="font-size: 0.75rem;">Preparation Lead Time</label>
                    <input type="date" id="prepDateInput_${data.id}" class="control-pro" style="font-size: 0.75rem; padding: 4px; margin-bottom: 5px;">
                    <button onclick="window.setPreparationDate(${data.id})" class="btn-primary-pro" style="width: 100%; justify-content: center; font-size: 0.75rem; padding: 6px;"><i class="fas fa-play"></i> Start Preparation</button>
                </div>
            `;
        }
"""

if "Preparation Lead Time UI" not in js:
    idx = js.find("if (actionsEl) {")
    idx2 = js.find("actionsEl.innerHTML += `<button onclick=\"window.openEditBookingModal()\"", idx)
    
    if idx2 != -1:
        insert_idx = js.find(";</button>`;", idx2) + len(";</button>`;")
        new_js = js[:insert_idx] + "\n" + patch + js[insert_idx:]
        with open('app/static/js/caterer/bookings.js', 'w', encoding='utf-8') as f:
            f.write(new_js)
        print("Patched bookingModalActionsTop to include Preparation Lead Time UI")
    else:
        print("Could not find Edit Booking button to insert after.")
else:
    print("Preparation Lead Time UI already in actionsEl")
