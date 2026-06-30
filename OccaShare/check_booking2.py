import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from app.db.database import SessionLocal
from app.db import models

db = SessionLocal()
booking = db.query(models.Booking).get(2)
print(f"Booking {booking.id}:")
print(f"transaction_type: {booking.transaction_type}")
print(f"document_type: {booking.document_type}")
print(f"package_id: {booking.package_id}")
