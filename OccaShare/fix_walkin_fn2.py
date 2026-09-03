with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    content = f.read()

old = """window.openManualBookingModal = function() {
    // If we're on the calendar page, open the walk-in modal directly
    const manModal = document.getElementById('manBookingModal');
    if (manModal) {
        manModal.classList.add('active');
        // Reset step
        if (typeof currentStep !== 'undefined') {
            currentStep = 1;
        }
    } else {
        // Fallback: go to bookings page
        window.location.href = '/caterer/bookings';
    }
};"""

new = """window.openManualBookingModal = function() {
    // Walk-in booking is managed from the bookings page
    window.location.href = '/caterer/bookings';
};"""

content = content.replace(old, new)

with open('app/static/js/caterer/calendar.js', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed openManualBookingModal to redirect to bookings")
