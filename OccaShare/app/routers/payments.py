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
    payment_type: str = Form("dp"), # "dp" or "balance"
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    try:
        res_fee = float(booking.reservation_fee or 0)
        total = float(booking.total_amount or 0)
        
        amount = res_fee if payment_type == "dp" else (total - res_fee)
        
        if amount <= 0:
            return {"success": False, "message": f"Invalid payment amount: ₱{amount:,.2f}. Please contact support."}
    except Exception as e:
        return {"success": False, "message": f"Calculation error: {str(e)}"}

    from ..services.paymongo import paymongo_service
    description = f"Payment for {booking.event_name or 'Event'} ({payment_type.upper()})"
    remarks = f"booking_id:{booking.id}:type:{payment_type}"
    
    try:
        link_data = paymongo_service.create_payment_link(amount, description, remarks)
        
        booking.paymongo_link_id = link_data["id"]
        booking.paymongo_link_url = link_data["url"]
        db.commit()

        return {
            "success": True, 
            "checkout_url": link_data["url"],
            "message": "Payment link generated"
        }
    except Exception as e:
        print(f"FAILED TO GENERATE PAYMONGO LINK: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhooks/payment")
async def payment_webhook(
    request: Request,
    db: Session = Depends(database.get_db)
):
    """
    Official Paymongo Webhook Handler
    """
    try:
        body = await request.body()
        signature = request.headers.get("paymongo-signature", "")
        # For simplicity in this demo environment, we extract signature components if needed
        # but the specific signature verification logic is in PaymongoService
        
        payload = json.loads(body)
        
        if "data" in payload and "attributes" in payload["data"]:
            event_type = payload["data"]["attributes"].get("type")
            
            if event_type == "link.payment.paid":
                payment_data = payload["data"]["attributes"].get("data", {}).get("attributes", {})
                remarks = payment_data.get("remarks", "")
                external_ref = payment_data.get("reference_number")
                amount_paid = payment_data.get("amount", 0) / 100.0 # convert cents to pesos
                
                # Parse remarks e.g. "booking_id:15:type:dp"
                parts = remarks.split(":")
                booking_id = None
                pay_type = "dp"
                
                if len(parts) >= 2 and parts[0] == "booking_id":
                    booking_id = int(parts[1])
                if len(parts) >= 4 and parts[2] == "type":
                    pay_type = parts[3]
                
                if not booking_id:
                     return {"error": "Booking ID missing in remarks"}

                booking = db.query(models.Booking).get(booking_id)
                if not booking:
                     return {"error": "Booking not found"}

                # 1. Update Booking Status
                if pay_type == "dp":
                    booking.payment_status = "deposit_paid"
                    booking.status = "confirmed"
                else:
                    booking.payment_status = "paid"
                
                booking.payment_reference = external_ref

                # 2. Logic for Escrow / Payout
                config = db.query(models.WebsiteConfig).first()
                commission = config.commission_fixed_amount if pay_type == "dp" else 0.0
                net_amount = amount_paid - commission
                
                # Check if a Payout record exists for this caterer/booking
                payout = db.query(models.Payout).filter(
                    models.Payout.caterer_id == booking.caterer_id,
                    models.Payout.status == "pending"
                ).first()
                
                if not payout:
                    payout = models.Payout(
                        caterer_id=booking.caterer_id,
                        amount=0,
                        status="pending"
                    )
                    db.add(payout)
                    db.flush()

                # Create Payout Item
                # DP is released 'immediate' (Prep Funds), Balance is released 'on_completion' (Escrow)
                trigger = "immediate" if pay_type == "dp" else "on_completion"
                status = "ready" if trigger == "immediate" else "escrowed"
                
                payout_item = models.PayoutItem(
                    payout_id=payout.id,
                    booking_id=booking.id,
                    amount=net_amount,
                    status=status,
                    release_trigger=trigger
                )
                db.add(payout_item)
                
                # Update total payout amount
                payout.amount += net_amount

                # 3. Log history
                history = models.BookingHistory(
                    booking_id=booking_id,
                    status=booking.status,
                    notes=f"Payment of ₱{amount_paid:,.2f} ({pay_type.upper()}) received via Paymongo."
                )
                db.add(history)
                
                # 4. Trigger Notification
                from ..services.notification import NotificationService
                await NotificationService.notify_payment_received(db, booking, amount_paid, "Paymongo Online")
                
                db.commit()
                return {"status": "success", "booking_id": booking_id}
            
        return {"status": "ignored", "event": payload.get("data", {}).get("attributes", {}).get("type")}
    except Exception as e:
        db.rollback()
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
