import sys
import os

# Add the app directory to the sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from app.db.database import SessionLocal
from app.db import models

db = SessionLocal()
booking = db.query(models.Booking).get(2)
if booking:
    print(f"Booking 2: {booking.event_name}")
    print(f"Selected Items count: {len(booking.selected_items)}")
    for i in booking.selected_items:
        print(f" - {i.id}: menu_item_id={i.menu_item_id}, qty={i.quantity}, price={i.price}")
else:
    print("Booking 2 not found")
