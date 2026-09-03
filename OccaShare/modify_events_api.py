import re

with open('app/routers/caterer_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = '''
    for b in bookings:
        start_dt = str(b.event_date)
        if b.event_time:
            start_dt += f"T{b.event_time}"

        # Track counts
        date_key = str(b.event_date)
        date_booking_counts[date_key] = date_booking_counts.get(date_key, 0) + 1

        # Normalize event type for color mapping
        raw_type = (b.event_type or "Wedding").strip()
        ev_type = raw_type.title()
        if ev_type.lower() in ['ala carte', 'alacarte', 'a la carte', 'ala carte order']:
            ev_type = "Ala Carte"
        elif ev_type.lower() in ['equipment rental']:
            ev_type = "Equipment Rental"

        event_data = {
            "id": str(b.id),
            "start": start_dt,
            "backgroundColor": colors.get(ev_type, "#6366f1"),
            "borderColor": colors.get(ev_type, "#6366f1"),
        }

        if is_owner:
            customer_name = f"{b.user.first_name} {b.user.last_name}" if b.user else "Unknown Customer"
            customer_first_name = b.user.first_name if b.user else "Customer"
            event_data["title"] = f"{b.event_type or 'Event'} - {b.event_name or customer_first_name}"
            event_data["extendedProps"] = {
                "recordType": "booking",
                "customer": customer_name,
                "type": b.event_type or "N/A",
                "guests": b.guest_count,
                "venue": b.venue_address or "TBD",
                "package": b.package.name if b.package else "Custom",
                "time": str(b.event_time) if b.event_time else "TBD",
                "status": b.status,
                "payment_status": b.payment_status or "pending",
                "preparation_status": b.preparation_status or "not_started",
                "preparation_date": str(b.preparation_date.strftime('%B %d, %Y')) if getattr(b, 'preparation_date', None) else "TBD",
                "total_price": float(b.total_amount or b.total_price or 0.0),
                "amount_paid": float(b.amount_paid or 0.0),
                "customer_email": b.user.email if b.user else (b.customer_email or "N/A"),
                "customer_contact": b.user.contact_number if b.user else (b.customer_contact or "N/A"),
                "booking_id": b.id,
                "special_requests": b.special_requests or ""
            }
            events.append(event_data)
            
            # Sub-event: Preparation
            if getattr(b, 'preparation_date', None) and b.status in ['confirmed', 'preparing', 'setup_ongoing', 'in_progress']:
                events.append({
                    "id": f"prep-{b.id}",
                    "start": str(b.preparation_date),
                    "backgroundColor": "#0ea5e9",
                    "borderColor": "#0ea5e9",
                    "title": f"Prep: {b.event_type or 'Event'}",
                    "extendedProps": {
                        "recordType": "preparation",
                        "customer": customer_name,
                        "booking_id": b.id
                    }
                })
                
            # Sub-event: Payment Reminder (if unpaid/partial and event is in future)
            from datetime import timedelta, date
            if b.payment_status in ['pending', 'unpaid', 'deposit_paid', 'partial', 'pending_verification'] and b.event_date and b.event_date > date.today():
                deadline_date = b.event_date - timedelta(days=3)
                if deadline_date >= date.today():
                    events.append({
                        "id": f"pay-{b.id}",
                        "start": str(deadline_date),
                        "backgroundColor": "#f59e0b",
                        "borderColor": "#f59e0b",
                        "title": f"Payment Due: {customer_first_name}",
                        "extendedProps": {
                            "recordType": "reminder",
                            "customer": customer_name,
                            "booking_id": b.id
                        }
                    })
        else:
            event_data["title"] = "BOOKED"
            event_data["display"] = "background"
            event_data["overlap"] = False
            events.append(event_data)
'''

content = re.sub(
    r'for b in bookings:\s*start_dt = str\(b\.event_date\)[\s\S]*?(?=# Add blocked dates from availability)',
    replacement + '\n        ',
    content
)

with open('app/routers/caterer_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated API events logic")
