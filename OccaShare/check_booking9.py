import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from app.db.database import SessionLocal
from app.db import models

db = SessionLocal()
booking = db.query(models.Booking).get(9)
if booking:
    print(f"Booking 9:")
    print(f"transaction_type: {booking.transaction_type}")
    print(f"document_type: {booking.document_type}")
    print(f"Selected Items count: {len(booking.selected_items)}")
    for i in booking.selected_items:
        print(f" - {i.id}: menu_item_id={i.menu_item_id}, qty={i.quantity}, price={i.price}")
else:
    print("Booking 9 not found")
