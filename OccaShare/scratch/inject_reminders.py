import re

backend_path = r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py'

with open(backend_path, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to inject it where `def _get_caterer_stats` is called or where the `templates.TemplateResponse("caterer/index.html"` happens.
target = """    stats = _get_caterer_stats(profile, bookings, timeframe=timeframe, start_date=start_date, end_date=end_date)"""

replacement = """    stats = _get_caterer_stats(profile, bookings, timeframe=timeframe, start_date=start_date, end_date=end_date)
    
    # Generate intelligent calendar reminders proactively
    try:
        from app.services.reminders import generate_caterer_reminders
        generate_caterer_reminders(user.id, db)
    except Exception as e:
        print(f"Error generating reminders: {e}")"""

if target in content:
    content = content.replace(target, replacement)
    with open(backend_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Injected successfully!")
else:
    print("Target not found.")
