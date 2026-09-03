with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f.readlines()):
        if 'calendar' in line.lower() and ('id=' in line or 'id =' in line):
            print(f"Line {i+1}: {line.strip()}")
