import sys
import os

sys.path.append(r'c:\OccaServe\OccaShare')
from app.db.database import SessionLocal
from app.db.models import Notification

replacements = {
    'Preparation Started! ??': 'Preparation Started!',
    'Ready for Delivery! ??': 'Ready for Delivery!',
    'Order is in Transit! ??': 'Order is in Transit!',
    'Caterer has Arrived! ??': 'Caterer has Arrived!',
    'Dining Setup Ongoing ???': 'Dining Setup Ongoing',
    'Transaction Completed! ??': 'Transaction Completed!',
    'Booking Confirmed! ??': 'Booking Confirmed!',
    'Payment Fully Verified! ??': 'Payment Fully Verified!',
    'Booking Cancelled ?': 'Booking Cancelled',
    'Booking Rejected ?': 'Booking Rejected',
    'Event Service Completed ?': 'Event Service Completed',
    '?? High Risk Payment Detected! Check AI Scan details.': 'High Risk Payment Detected! Check AI Scan details.'
}

session = SessionLocal()
notifs = session.query(Notification).all()
updated_count = 0

for notif in notifs:
    if notif.title:
        original = notif.title
        for old, new in replacements.items():
            if old in notif.title:
                notif.title = notif.title.replace(old, new)
        
        # fallback string replace
        notif.title = notif.title.replace('??', '').replace('??', '').replace('??', '').replace('??', '').replace('???', '').replace('??', '').replace('??', '').replace('?', '').replace('?', '').replace('??', '').strip()
        
        if notif.title != original:
            updated_count += 1

session.commit()
print(f"Removed emojis from {updated_count} historical notifications.")
