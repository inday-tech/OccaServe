with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    text = f.read()

for i, line in enumerate(text.splitlines()):
    if 'cal-grid' in line or 'cal-card-calendar' in line or '<!-- Right: Sidebar -->' in line or '<!-- Calendar Event Details Modal -->' in line:
        print(f"{i+1}: {line}")
