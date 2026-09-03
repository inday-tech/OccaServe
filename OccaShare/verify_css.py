with open('app/static/css/caterer/calendar.css', 'r', encoding='utf-8') as f:
    content = f.read()

checks = [
    '.filter-btn',
    '.cal-legend-bar',
    '.modal-overlay',
    '.cal-grid',
    '.cal-sidebar',
    '.cal-card-calendar',
]
for c in checks:
    print(f"{c}: {'YES' if c in content else 'MISSING'}")
