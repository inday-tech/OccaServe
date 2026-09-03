with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'manPaymentStatus' in line or 'value="paid"' in line or 'value="unpaid"' in line:
            print(f'{i+1}: {line.strip()}')
