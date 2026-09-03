with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    content = f.read()
    print('closeModal in JS:', 'closeModal(' in content)
    
with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()
    print('closeModal in HTML:', 'closeModal(' in content)
