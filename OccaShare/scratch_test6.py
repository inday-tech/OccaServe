with open('templates/caterer/bookings.html', 'r', encoding='utf-8') as f:
    for line in f:
        if 'tr class="hover-row"' in line or 'onclick' in line and 'Booking' in line:
            print(line.strip())
