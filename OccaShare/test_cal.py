with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if 'id="calendar"' in line or "id='calendar'" in line:
            print(f"{i+1}: {line.strip()}")
