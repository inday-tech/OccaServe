import re

files = [
    'templates/caterer/bookings.html', 
    'templates/caterer/calendar.html',
    'templates/caterer/orders.html'
]

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Increment version for js/css files
        content = re.sub(r'(\?v=)(\d+\.\d+|\d+)', lambda m: m.group(1) + str(float(m.group(2)) + 0.1), content)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated versions in {filepath}")
    except FileNotFoundError:
        pass
