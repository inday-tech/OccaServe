with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(len(lines)):
        if 'dateClick: function' in lines[i]:
            for j in range(i, min(i+30, len(lines))):
                print(f"{j+1}: {lines[j].rstrip()}")
            break
