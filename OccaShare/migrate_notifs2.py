import sys
import os

sys.path.append(r'c:\OccaServe\OccaShare')
from app.db.database import SessionLocal
from app.db.models import Notification
from app.services.notification import NotificationService

session = SessionLocal()

notifs = session.query(Notification).all()
updated_count = 0

for notif in notifs:
    original_type = notif.type
    new_type = NotificationService._determine_notif_type(notif.title, original_type)
    if new_type != original_type:
        notif.type = new_type
        updated_count += 1

session.commit()
print(f"Successfully migrated {updated_count} historical notifications to semantic types.")
