with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(len(lines)-60, len(lines)):
        print(f"{i+1}: {lines[i].rstrip()}")
