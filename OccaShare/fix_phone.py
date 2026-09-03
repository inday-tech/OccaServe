import re

files = ['templates/caterer/bookings.html', 'templates/caterer/orders.html', 'templates/caterer/calendar.html']

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace booking.user.contact_number with booking.user.phone_number
        new_content = content.replace('booking.user.contact_number', 'booking.user.phone_number')
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'Updated {filepath}')
    except FileNotFoundError:
        pass
