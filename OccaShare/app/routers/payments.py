from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import database, models
from datetime import datetime, timezone
from ..services.notification import NotificationService

router = APIRouter(prefix="/api", tags=["payments"])

@router.post("/bookings/{booking_id}/expire")
async def expire_booking(
    booking_id: int,
    db: Session = Depends(database.get_db)
):
    # Internal endpoint called by cron or task runner
    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.status == "draft":
        if booking.expires_at and datetime.now(timezone.utc) > booking.expires_at.replace(tzinfo=timezone.utc):
            booking.status = "expired"
            
            history = models.BookingHistory(
                booking_id=booking_id,
                status="expired",
                notes="Unfinished booking draft expired after its continuation window."
            )
            db.add(history)
            db.commit()
            return {"status": "expired"}
            
    return {"status": "active"}

@router.post("/internal/cleanup-expired")
async def cleanup_expired_bookings(db: Session = Depends(database.get_db)):
    """
    Expires unfinished drafts and overdue initial payment requests without cancelling bookings.
    """
    now = datetime.now(timezone.utc)
    expired_bookings = db.query(models.Booking).filter(
        models.Booking.status == "draft",
        models.Booking.expires_at < now
    ).all()
    
    count = 0
    for booking in expired_bookings:
        booking.status = "expired"
        history = models.BookingHistory(
            booking_id=booking.id,
            status="expired",
            notes="Unfinished booking draft expired after its continuation window."
        )
        db.add(history)
        count += 1

    from ..services.payment_deadline import expire_initial_payment_if_due
    overdue_payment_requests = db.query(models.Booking).filter(
        models.Booking.payment_deadline_at <= now,
        models.Booking.payment_request_status == "pending",
        models.Booking.status.in_(["pending", "awaiting_payment", "pending_payment"]),
    ).all()
    payment_expired_count = 0
    for booking in overdue_payment_requests:
        if not expire_initial_payment_if_due(db, booking, now=now):
            continue
        payment_expired_count += 1
        await NotificationService.notify_status_update(
            db, booking.user_id, "Payment Request Expired",
            "The initial payment deadline passed. You can request an extension from the caterer.",
            f"/customer/bookings?open_detail={booking.id}&open_chat=1", "warning"
        )
        await NotificationService.notify_status_update(
            db, booking.caterer.user_id, "Payment Request Expired",
            "The customer's initial payment deadline passed. Review the booking and any extension request.",
            f"/caterer/bookings?open_booking={booking.id}&open_tab=payment", "warning"
        )
    
    db.commit()
    return {"expired_count": count, "payment_requests_expired": payment_expired_count}
