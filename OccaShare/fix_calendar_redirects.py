import re

# Fix calendar.html
with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

html_content = html_content.replace("/caterer/dashboard?page=bookings&focus=", "/caterer/bookings?focus=")

with open('templates/caterer/calendar.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

# Fix calendar.js
with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

js_content = js_content.replace("/caterer/dashboard?page=bookings&focus=", "/caterer/bookings?focus=")

# Fix recordOfflinePayment in calendar.js to just redirect
js_content = re.sub(
    r'window\.recordOfflinePayment = function\(id\) \{[\s\S]*?window\.openIframeModal[\s\S]*?\};',
    '''window.recordOfflinePayment = function(id) {
    if (!id) id = document.getElementById('evModalBookingId').value;
    if (!id) return;
    
    // Redirect to bookings page where offline payment can be managed properly
    window.location.href = '/caterer/bookings?focus=' + id;
};''',
    js_content
)

with open('app/static/js/caterer/calendar.js', 'w', encoding='utf-8') as f:
    f.write(js_content)
print('Fixed calendar redirects')
