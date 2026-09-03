with open('templates/caterer/bookings.html', 'r', encoding='utf-8') as f:
    content = f.read()
    if 'manualBookingModal' in content or 'manFirstName' in content:
        print("YES - walk-in form is in bookings.html")
    else:
        print("NO - not found in bookings.html")

import os
files = os.listdir('templates/caterer/')
print("Templates:", files)
