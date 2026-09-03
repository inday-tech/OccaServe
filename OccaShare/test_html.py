with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    if 'main.min.js' in f.read():
        print("Found main.min.js")
    else:
        print("MISSING main.min.js")
