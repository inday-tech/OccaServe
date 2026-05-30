import sys
import os

sys.path.append(r'c:\OccaServe\OccaShare')
from app.db.database import SessionLocal
from app.db.models import Notification

def determine_notif_type(title, current_type):
    if current_type in ["Booking", "Payment", "Review", "Verification", "Customer", "Message"]:
        return current_type
        
    if current_type in ["info", "success", "warning", "error"] or not current_type:
        lower_title = (title or "").lower()
        if any(k in lower_title for k in ['booking', 'event', 'reservation', 'contract', 'cancelled', 'rejected', 'completed', 'verified!', 'signed']):
            return "Booking"
        elif any(k in lower_title for k in ['payment', 'balance', 'deadline', 'settlement', 'downpayment', 'commission', 'proof']):
            return "Payment"
        elif any(k in lower_title for k in ['review', 'rate', 'feedback']):
            return "Review"
        elif any(k in lower_title for k in ['identity', 'verify', 'verification', 'kyc', 'alert', 'application', 'account status', 'action required']):
            return "Verification"
        elif any(k in lower_title for k in ['customer', 'profile']):
            return "Customer"
        elif any(k in lower_title for k in ['message', 'chat']):
            return "Message"
            
    return current_type or "info"

session = SessionLocal()
notifs = session.query(Notification).all()
updated_count = 0

for notif in notifs:
    original_type = notif.type
    new_type = determine_notif_type(notif.title, original_type)
    if new_type != original_type:
        notif.type = new_type
        updated_count += 1

session.commit()
print(f"Successfully migrated {updated_count} historical notifications to semantic types.")
