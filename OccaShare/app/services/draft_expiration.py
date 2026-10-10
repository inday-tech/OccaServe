from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db import models


DRAFT_EXPIRATION_NOTE = (
    "Automatically cancelled because the customer did not continue the draft within 24 hours."
)


def cancel_expired_booking_drafts(db: Session) -> int:
    """Cancel unfinished booking drafts whose 24-hour continuation window elapsed."""
    now = datetime.now(timezone.utc)
    drafts = (
        db.query(models.Booking)
        .filter(
            models.Booking.status == "draft",
            models.Booking.expires_at.isnot(None),
            models.Booking.expires_at <= now,
        )
        .with_for_update(skip_locked=True)
        .all()
    )

    for booking in drafts:
        booking.status = "cancelled"
        db.add(models.BookingHistory(
            booking_id=booking.id,
            status="cancelled",
            notes=DRAFT_EXPIRATION_NOTE,
        ))
        if booking.user_id:
            db.add(models.Notification(
                user_id=booking.user_id,
                title="Draft booking cancelled",
                message="Your unfinished booking was automatically cancelled after 24 hours. You can start a new booking anytime.",
                type="warning",
                link="/customer/orders",
            ))

    if drafts:
        db.commit()
    return len(drafts)
