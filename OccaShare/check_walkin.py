# Check if the walk-in modal is in calendar.html 
with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if 'manualBookingModal' in line or 'walk-in' in line.lower() or 'walkin' in line.lower():
            print(f"{i+1}: {line.strip()}")
