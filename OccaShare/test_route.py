import requests
import re

# Try to hit the server
try:
    # First check if server is alive
    r = requests.get('http://127.0.0.1:8000/', timeout=3)
    print(f'Server is running: {r.status_code}')
except Exception as e:
    print(f'Server not responding: {e}')
    exit()

# Check login page to see what's happening
r = requests.get('http://127.0.0.1:8000/caterer/calendar', timeout=5, allow_redirects=False)
print(f'Calendar page status: {r.status_code}')
print(f'Headers: {dict(r.headers)}')
if r.status_code == 200:
    html = r.text
    # Check for key elements
    checks = [
        ('id=.calendar.', 'Calendar div'),
        ('fullcalendar', 'FullCalendar CSS/JS'),
        ('filter-btn', 'Filter buttons'),
        ('addScheduleModal', 'Add Schedule modal'),
        ('manualBookingModal', 'Walk-in modal'),
        ('block extra_css', 'CSS block issue'),
        ('block content', 'Content block issue'),
    ]
    for pattern, name in checks:
        found = re.search(pattern, html, re.IGNORECASE)
        print(f'  {name}: {"YES" if found else "NO"}')
        
    # Check for any Python/Jinja errors in the page
    if 'Internal Server Error' in html or 'Traceback' in html:
        print('ERROR: Server error in response!')
        print(html[:2000])
elif r.status_code in [301, 302]:
    print(f'Redirect to: {r.headers.get("location")}')
