import sys
import os

sys.path.append(r'c:\OccaServe\OccaShare')
from app.db.database import SessionLocal
from app.db.models import Notification

session = SessionLocal()
notifs = session.query(Notification).order_by(Notification.id.desc()).limit(15).all()

for n in notifs:
    title = (n.title or "").encode('ascii', 'ignore').decode('ascii')
    msg = (n.message or "").encode('ascii', 'ignore').decode('ascii')
    print(f"ID: {n.id}, Type: {n.type}, Title: {title}, Message: {msg[:40]}")

