import sys
import re

sys.path.append(r'c:\OccaServe\OccaShare')
from app.db.database import SessionLocal
from app.db.models import Notification

session = SessionLocal()
notifs = session.query(Notification).all()
updated_count = 0

for notif in notifs:
    if notif.title:
        original = notif.title
        # Strip all non-ascii characters (emojis)
        notif.title = re.sub(r'[^\x00-\x7F]+', '', notif.title).strip()
        
        # We also might need to check if message has it, although user showed title
        if notif.message:
            notif.message = re.sub(r'[^\x00-\x7F]+', '', notif.message).strip()
            
        if notif.title != original or notif.message != (notif.message if notif.message else ''):
            updated_count += 1

session.commit()
print(f"Removed emojis from {updated_count} historical notifications.")
