import re

with open('app/routers/caterer_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = '''
    timeframe = request.query_params.get('timeframe', 'month')
    stats = _get_caterer_stats(profile, bookings, timeframe=timeframe)

    from datetime import date, timedelta
    today = date.today()
    
    # 1. Operational Dashboard Metrics
    all_bookings = profile.bookings
    today_events_count = len([b for b in all_bookings if b.event_date == today and b.status not in ['cancelled', 'draft']])
    upcoming_events_count = len([b for b in all_bookings if b.event_date and today < b.event_date <= today + timedelta(days=30) and b.status not in ['cancelled', 'draft']])
    
    outstanding_balance = 0
    outstanding_count = 0
    action_center_items = []
    
    for b in all_bookings:
        if b.status in ['cancelled', 'draft', 'completed']:
            continue
            
        amount = float(b.total_amount or b.total_price or 0)
        paid = float(b.amount_paid or 0)
        
        # Balance computation
        if amount > paid and b.status not in ['pending_quotation', 'pending_review']:
            outstanding_balance += (amount - paid)
            outstanding_count += 1
            if b.event_date and b.event_date <= today + timedelta(days=3):
                action_center_items.append({'type': 'urgent', 'title': 'Payment Overdue', 'desc': f'Booking #{b.id}', 'icon': 'fa-money-bill-wave'})
            elif b.event_date and b.event_date <= today + timedelta(days=14) and b.status == 'confirmed':
                action_center_items.append({'type': 'warning', 'title': 'Final Balance Due', 'desc': f'Booking #{b.id}', 'icon': 'fa-coins'})
                
        # Prep / Deadline computation
        if b.event_date and today < b.event_date <= today + timedelta(days=7):
            action_center_items.append({'type': 'warning', 'title': 'Event within 7 days', 'desc': f'{b.event_type} - Booking #{b.id}', 'icon': 'fa-calendar-day'})
            
        if getattr(b, 'contract_status', '') == 'awaiting_signature':
            action_center_items.append({'type': 'warning', 'title': 'Contract Pending', 'desc': f'Booking #{b.id}', 'icon': 'fa-file-signature'})

    # Action required mapping
    action_required_count = stats.get('pending_actions', {}).get('total', 0)
    
    # Sort action center items
    action_center_items.sort(key=lambda x: 0 if x['type'] == 'urgent' else 1)
    
    stats['today_events_count'] = today_events_count
    stats['upcoming_events_count'] = upcoming_events_count
    stats['outstanding_balance'] = outstanding_balance
    stats['outstanding_count'] = outstanding_count
    stats['action_required_count'] = action_required_count
    stats['action_center_items'] = action_center_items[:6] # Top 6 items
'''

content = re.sub(
    r"timeframe = request\.query_params\.get\('timeframe', 'month'\)\n\s+stats = _get_caterer_stats\(profile, bookings, timeframe=timeframe\)",
    replacement.strip(),
    content
)

with open('app/routers/caterer_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated caterer_dashboard.py with operational metrics")
