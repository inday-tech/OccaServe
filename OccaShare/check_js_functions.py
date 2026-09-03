with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Check all functions called in HTML exist in JS
html_calls = [
    'openManualBookingModal',
    'openAddScheduleModal',
    'saveSchedule',
    'updateSidebarForDate',
    'openSidebarEventModal',
    'closeModal',
    'toggleDateAvailability',
    'checkAvailabilityStatus',
    'updateCapacitySettings',
    'unblockSelectedDate',
    'submitManualEvent',
    'changeStep',
    'addQuotationRow',
]
for fn in html_calls:
    defined = f'function {fn}' in js or f'window.{fn}' in js or f'{fn} =' in js
    print(f"  {fn}: {'YES' if defined else 'MISSING'}")
    
print()
# check calendar init
print('FullCalendar initialized:', 'new FullCalendar.Calendar' in js)
print('calendar.render() called:', 'calendar.render()' in js or '.render()' in js)
print('DOMContentLoaded handler:', 'DOMContentLoaded' in js)
