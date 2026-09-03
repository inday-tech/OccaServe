with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    content = f.read()

checks = [
    'openAddScheduleModal',
    'openManualBookingModal',
    'saveSchedule',
    'updateSidebarForDate',
    'sidebarSelectedDateStr',
    'sidebarDayEvents',
    'sidebarAvailabilityStatus',
    'window.fullCalendarInstance = calendar',
    'filter-btn',
]
for c in checks:
    print(f"{c}: {'YES' if c in content else 'MISSING'}")
