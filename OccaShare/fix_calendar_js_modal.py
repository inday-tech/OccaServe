with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    content = f.read()

# I need to revert the window.openManualBookingModal function
# From:
# window.openManualBookingModal = function() {
#     // Walk-in booking is managed from the bookings page
#     window.location.href = '/caterer/bookings';
# };
# To:
# window.openManualBookingModal = function() {
#     const manModal = document.getElementById('manBookingModal') || document.getElementById('manualBookingModal');
#     if (manModal) {
#         if(manModal.classList) manModal.classList.add('active');
#         manModal.style.display = 'flex';
#         if (typeof currentStep !== 'undefined') currentStep = 1;
#     } else {
#         window.location.href = '/caterer/bookings?new=walkin';
#     }
# };

import re
old_func_pattern = re.compile(r'window\.openManualBookingModal\s*=\s*function\(\)\s*\{[\s\S]*?\};')
new_func = """window.openManualBookingModal = function() {
    const manModal = document.getElementById('manBookingModal') || document.getElementById('manualBookingModal');
    if (manModal) {
        if(manModal.classList) manModal.classList.add('active');
        manModal.style.display = 'flex';
        if (typeof currentStep !== 'undefined') currentStep = 1;
    } else {
        window.location.href = '/caterer/bookings?new=walkin';
    }
};"""

content = old_func_pattern.sub(new_func, content)

with open('app/static/js/caterer/calendar.js', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated openManualBookingModal in calendar.js")
