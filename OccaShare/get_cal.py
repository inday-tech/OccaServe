with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    start = -1
    for i, line in enumerate(lines):
        if 'class="calendar-header"' in line or 'Page Header' in line or 'dash-header' in line:
            start = i
            break
            
    if start != -1:
        for j in range(start, start+150):
            print(f'{j+1}: {lines[j].strip()}')
