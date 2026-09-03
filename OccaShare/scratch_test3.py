with open('templates/caterer/bookings.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'id="bookingModal"' in line:
        print(f"Found at line {i+1}")
        break
