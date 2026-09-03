with open('templates/caterer/bookings.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('id="bookingModal"')
print(content[idx-100:idx+500])
