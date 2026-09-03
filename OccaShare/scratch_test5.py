with open('templates/caterer/bookings.html', 'r', encoding='utf-8') as f:
    for line in f:
        if 'open' in line.lower() and 'modal' in line.lower():
            print(line.strip())
