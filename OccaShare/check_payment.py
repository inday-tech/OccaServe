with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    for line in f:
        if 'manPaymentStatus' in line:
            print(line.strip())
