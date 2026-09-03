with open('app/static/css/caterer/calendar.css', 'r', encoding='utf-8') as f:
    css = f.read()

checks = [
    ('#calendar {', 'Calendar div height style'),
    ('.fc-view', 'FullCalendar view style'),
    ('.cal-card-calendar', 'Calendar card container'),
    ('.cal-grid', 'Grid layout'),
    ('.cal-sidebar', 'Sidebar'),
    ('.filter-btn', 'Filter buttons'),
    ('.pill-dot', 'Pill dots'),
    ('.weekly-event-card', 'Upcoming booking cards'),
    ('.weekly-event-date', 'Date column of booking card'),
    ('.weekly-event-info', 'Info column of booking card'),
    ('.modal-overlay', 'Modal overlay'),
    ('.status-badge', 'Status badge'),
    ('.empty-state', 'Empty state'),
]
for css_rule, desc in checks:
    print(f"  {desc} ({css_rule}): {'YES' if css_rule in css else 'MISSING'}") 
