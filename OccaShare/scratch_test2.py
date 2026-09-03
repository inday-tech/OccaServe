with open('templates/caterer/bookings.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('bookingModal')
if idx != -1:
    print("Found bookingModal in bookings.html:")
    print(content[idx-100:idx+500])
else:
    print("bookingModal NOT found in bookings.html")
