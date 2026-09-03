with open('app/static/js/caterer/bookings.js', 'r', encoding='utf-8') as f:
    for line in f:
        if 'data.status ===' in line:
            print(line.strip())
