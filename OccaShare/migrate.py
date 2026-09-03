from app.db.database import SessionLocal
from app.db.models import Booking, InternalSchedule

db = SessionLocal()
internal_bookings = db.query(Booking).filter(Booking.booking_source == 'Internal').all()
for b in internal_bookings:
    # Migrate to InternalSchedule
    s = InternalSchedule(
        caterer_id=b.caterer_id,
        title=b.event_name,
        schedule_type=b.event_type,
        date=b.event_date,
        time=b.event_time,
        is_pinned=False
    )
    db.add(s)
    db.delete(b)

db.commit()
print(f"Migrated and deleted {len(internal_bookings)} legacy Internal Bookings.")
db.close()
