import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db.database import engine
from app.db.models import Base, InternalSchedule
InternalSchedule.__table__.create(bind=engine, checkfirst=True)
print("Table internal_schedules created.")
