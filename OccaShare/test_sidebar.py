with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    start = -1
    for i, line in enumerate(lines):
        if '<!-- Right: Sidebar -->' in line:
            start = i
            break
            
    if start != -1:
        for j in range(start, start+150):
            if j < len(lines):
                print(f'{j+1}: {lines[j].strip()}')
            if '</div>' in lines[j] and 'cal-grid' not in lines[j] and 'endblock' in lines[j+1] if j+1 < len(lines) else False:
                pass
