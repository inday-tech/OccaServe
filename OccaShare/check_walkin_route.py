# Check if the walk-in modal is in calendar.html - look for the form/modal
with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()
    if 'manBookingModal' in content or 'id="manFirstName"' in content:
        print("Walk-in multi-step form EXISTS in calendar.html")
    else:
        print("Walk-in form is NOT in calendar.html - needs redirect")
        
# Check if bookings page handles ?new=walkin
with open('templates/caterer/bookings.html', 'r', encoding='utf-8') as f:
    content = f.read()
    if 'new=walkin' in content or 'openManualBookingModal' in content:
        print("Bookings page handles ?new=walkin")
    else:
        print("Bookings page does NOT handle ?new=walkin")
