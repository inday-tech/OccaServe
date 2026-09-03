import re

files = ['templates/caterer/bookings.html', 'templates/caterer/orders.html', 'templates/caterer/calendar.html']

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add data-booking-source before data-is-food-order
        if 'data-booking-source=' not in content:
            new_content = content.replace('data-is-food-order=', 'data-booking-source="{{ booking.booking_source or \'\' }}"\n                                data-is-food-order=')
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f'Updated {filepath}')
    except FileNotFoundError:
        pass
