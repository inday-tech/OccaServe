with open('templates/caterer/bookings.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('<tr class="booking-row-item"')
print(content[idx:idx+400])
