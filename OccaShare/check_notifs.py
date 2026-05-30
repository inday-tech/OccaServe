import sys
import os

sys.path.append(r'c:\OccaServe\OccaShare')
from app.db.database import SessionLocal
from app.db.models import Notification

session = SessionLocal()
notifs = session.query(Notification).order_by(Notification.id.desc()).limit(10).all()

for n in notifs:
    print(f"ID: {n.id}, Type: {n.type}, Title: {n.title}, Message: {n.message[:30]}")

