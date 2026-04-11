from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from sqlalchemy.orm import Session
from ..db import database, models
from ..core import security as auth
from datetime import datetime, timezone
import json

router = APIRouter(prefix="/api", tags=["payments"])

@router.post("/bookings/{booking_id}/pay")
async def process_payment(
    booking_id: int,
    payment_method: str = Form(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # In a real app, integrate with a payment gateway (GCash, PayMaya, etc.)
    # Here we simulate starting the payment process
    return {
        "success": True, 
        "checkout_url": f"https://mock-gateway.com/pay/{booking_id}",
        "message": "Payment initialized"
    }

@router.post("/webhooks/payment")
async def payment_webhook(
    request: Request,
    db: Session = Depends(database.get_db)
):
    # This endpoint receives callbacks from the payment gateway (Paymongo or Mock)
    try:
        payload = await request.json()
        
        # Determine if it's Paymongo format
        if "data" in payload and "attributes" in payload["data"]:
            pm_attrs = payload["data"]["attributes"]
            if pm_attrs.get("type") == "link.payment.paid":
                payment_data = pm_attrs.get("data", {}).get("attributes", {})
                status = payment_data.get("status")
                remarks = payment_data.get("remarks", "")
                
                # Extract booking ID from remarks e.g. "booking_id:15"
                if remarks.startswith("booking_id:"):
                    try:
                        booking_id = int(remarks.split(":", 1)[1])
                    except ValueError:
                        booking_id = None
                else:
                    booking_id = None
            else:
                return {"status": "ignored"}
        else:
            # Mock Fallback
            booking_id = payload.get("booking_id")
            status = payload.get("status") # 'success', 'failed'
        
        booking = db.query(models.Booking).get(booking_id)
        if not booking:
             return {"error": "Booking not found"}

        if status in ["success", "paid"]:
            booking.status = "confirmed"
            booking.payment_status = "paid"
            
            # Log history
            history = models.BookingHistory(
                booking_id=booking_id,
                status="confirmed",
                notes=f"Payment received via {payload.get('method')}"
            )
            db.add(history)
            
            # TODO: Send email confirmation
        
        db.commit()
        return {"status": "received"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/bookings/{booking_id}/expire")
async def expire_booking(
    booking_id: int,
    db: Session = Depends(database.get_db)
):
    # Internal endpoint called by cron or task runner
    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.status == "draft" or booking.status == "pending":
        if booking.expires_at and datetime.now(timezone.utc) > booking.expires_at.replace(tzinfo=timezone.utc):
            booking.status = "expired"
            
            history = models.BookingHistory(
                booking_id=booking_id,
                status="expired",
                notes="Booking expired due to non-payment within 24 hours"
            )
            db.add(history)
            db.commit()
            return {"status": "expired"}
            
    return {"status": "active"}

@router.post("/internal/cleanup-expired")
async def cleanup_expired_bookings(db: Session = Depends(database.get_db)):
    """
    Finds and marks all overdue draft/pending bookings as expired.
    """
    now = datetime.now(timezone.utc)
    expired_bookings = db.query(models.Booking).filter(
        models.Booking.status.in_(["draft", "pending"]),
        models.Booking.expires_at < now
    ).all()
    
    count = 0
    for booking in expired_bookings:
        booking.status = "expired"
        history = models.BookingHistory(
            booking_id=booking.id,
            status="expired",
            notes="Bulk cleanup marked as expired"
        )
        db.add(history)
        count += 1
    
    db.commit()
    return {"expired_count": count}
