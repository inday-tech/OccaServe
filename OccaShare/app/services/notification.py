import os
import httpx
from sqlalchemy.orm import Session
from ..db import models
from ..core.config import settings
from .email import EmailService
from ..services.realtime import manager

class NotificationService:
    @staticmethod
    async def _send_sms(to_number: str, message: str):
        """Helper to send SMS via configured provider."""
        if not settings.SMS_API_KEY or not to_number:
            print(f"[SMS MOCK] To: {to_number} | Msg: {message}")
            return True

        try:
            if settings.SMS_PROVIDER == "semaphore":
                url = "https://api.semaphore.co/api/v4/messages"
                payload = {
                    "apikey": settings.SMS_API_KEY,
                    "number": to_number,
                    "message": message,
                    "sendername": settings.SMS_SENDER_NAME
                }
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, data=payload)
                    if response.status_code == 200:
                        print(f"[SMS SERVICE] Sent to {to_number} via Semaphore")
                        return True
                    else:
                        print(f"[SMS ERROR] Semaphore responded with {response.status_code}: {response.text}")
            
            elif settings.SMS_PROVIDER == "twilio":
                # Twilio implementation would go here
                print(f"[SMS TWILIO] Twilio provider not fully implemented yet.")
            
            else:
                print(f"[SMS MOCK] To: {to_number} | Msg: {message}")
                return True
        except Exception as e:
            print(f"[SMS SERVICE ERROR] {e}")
            return False

    @staticmethod
    async def notify_new_booking(db: Session, booking: models.Booking):
        """Notifies caterer of a new booking request."""
        caterer = booking.caterer
        user = caterer.user
        customer = booking.user

        if not user: return

        # 1. In-App Notification
        notif = models.Notification(
            user_id=user.id,
            title="New Booking Received!",
            message=f"New booking for '{booking.event_name}' on {booking.event_date}.",
            type="Booking",
            link=f"/caterer/bookings"
        )
        db.add(notif)
        db.commit()

        # 2. Email Notification
        EmailService.send_booking_confirmation(customer.email, booking.id) # To Customer
        
        # Email to Caterer
        EmailService._send_email(
            user.email,
            "New Booking Request - OccaShare",
            f"Hello {caterer.business_name},\n\nYou have received a new booking for '{booking.event_name}'.\nLog in to your dashboard to review."
        )

        # 3. SMS Notification to Caterer
        phone = caterer.contact_phone or user.phone_number
        if phone:
            sms_msg = f"OccaShare: New booking for '{booking.event_name}' on {booking.event_date}. Log in to review!"
            await NotificationService._send_sms(phone, sms_msg)

        # 4. Real-time WebSocket
        await manager.broadcast_to_user(user.id, {"type": "booking_update", "message": f"New booking: {booking.event_name}"})

    @staticmethod
    async def notify_quotation_ready(db: Session, booking: models.Booking):
        """Notifies customer that a quotation is ready for review."""
        # 1. In-App
        notif = models.Notification(
            user_id=booking.user_id,
            title="Quotation Ready",
            message=f"The caterer has generated a new quotation for your event '{booking.event_name}'.",
            type="info",
            link=f"/bookings/step/quotation/{booking.id}"
        )
        db.add(notif)
        db.commit()

        # 2. Email to Customer
        EmailService._send_email(
            booking.user.email,
            "Quotation Ready - OccaShare",
            f"Hello,\n\nA new quotation is ready for '{booking.event_name}'. Log in to review and sign the contract."
        )

    @staticmethod
    async def notify_status_update(db: Session, user_id: int, title: str, message: str, link: str, notif_type: str = "info"):
        """Generic status update notification (In-app + Email + Optimized SMS)."""
        user = db.query(models.User).get(user_id)
        if not user: return

        # 1. In-App
        notif = models.Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notif_type,
            link=link
        )
        db.add(notif)
        db.commit()

        # 2. Email (Always send)
        EmailService._send_email(user.email, f"OccaShare Update: {title}", message)

        # 3. Real-time (Always try to broadcast)
        await manager.broadcast_to_user(user_id, {
            "type": notif_type if notif_type != "info" else "new_notification", 
            "message": f"{title}: {message}",
            "title": title,
            "status": "approved" if "Approved" in title else "rejected" if "Rejected" in title or "Action Required" in title else "info"
        })

        # 4. Optimized SMS (Only if user is OFFLINE)
        is_online = user_id in manager.user_connections
        if not is_online:
            phone = user.phone_number
            if phone:
                sms_msg = f"OccaShare: {title}. {message}"
                # Limit length for SMS to avoid multiple segments if possible
                if len(sms_msg) > 160:
                    sms_msg = sms_msg[:157] + "..."
                await NotificationService._send_sms(phone, sms_msg)
            else:
                print(f"[NOTIF DEBUG] User {user_id} is offline but has no phone number.")
        else:
            print(f"[NOTIF DEBUG] User {user_id} is online. SMS skipped to save cost.")

    @staticmethod
    async def notify_payment_received(db: Session, booking: models.Booking, amount: float, payment_type: str = "Downpayment"):
        """Notifies caterer of a payment submission."""
        caterer = booking.caterer
        user = caterer.user
        
        if not user: return

        # 1. In-App
        notif = models.Notification(
            user_id=user.id,
            title=f"{payment_type} Received!",
            message=f"Payment of ₱{amount:,.2f} received for '{booking.event_name}'.",
            type="success",
            link=f"/caterer/bookings"
        )
        db.add(notif)
        db.commit()

        # 2. Email Receipt to Customer
        EmailService.send_payment_receipt(
            booking.user.email, 
            booking.id, 
            amount, 
            booking.payment_reference or "N/A", 
            payment_type
        )

        # 3. SMS to Caterer
        phone = caterer.contact_phone or user.phone_number
        if phone:
            sms_msg = f"OccaShare: {payment_type} of PhP{amount:,.2f} received for '{booking.event_name}'. Please verify proof in your dashboard."
            await NotificationService._send_sms(phone, sms_msg)

        # 4. Real-time
        await manager.broadcast_to_user(user.id, {"type": "dashboard_update", "message": "New payment received"})


