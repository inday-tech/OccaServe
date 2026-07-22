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

        is_food_order = (booking.document_type == 'invoice')
        prefix = "ORD" if is_food_order else "BK"
        ref_id = f"{prefix}-{booking.id:03d}"
        subject_prefix = "Order" if is_food_order else "Booking"
        event_date_str = booking.event_date.strftime('%B %d, %Y') if booking.event_date else 'TBD'

        # 1. In-App Notification to Caterer
        notif = models.Notification(
            user_id=user.id,
            title=f"New {subject_prefix} Received!",
            message=f"New {subject_prefix.lower()} {ref_id} for '{booking.event_name}' on {event_date_str} from {customer.first_name} {customer.last_name or ''}.",
            type="Booking",
            link=f"/caterer/bookings"
        )
        db.add(notif)
        db.commit()

        # 2. Email Notification to Customer — with full details
        venue = booking.event_address or booking.venue_address or None
        EmailService.send_booking_confirmation(
            customer.email, 
            booking.id, 
            booking.document_type,
            event_name=booking.event_name,
            caterer_name=caterer.business_name,
            event_date=event_date_str,
            total_amount=float(booking.total_amount) if booking.total_amount else None,
            guest_count=booking.guest_count,
            venue=venue
        )
        
        # Email to Caterer
        customer_name = f"{customer.first_name or ''} {customer.last_name or ''}".strip() or customer.email
        caterer_email_body = (
            f"Hello {caterer.business_name},\n\n"
            f"You have received a new {subject_prefix.lower()} request on OccaServe.\n\n"
            f"Reference: {ref_id}\n"
            f"Customer: {customer_name}\n"
            f"Event: {booking.event_name}\n"
            f"Date: {event_date_str}\n"
            f"Guests: {booking.guest_count or 'TBD'}\n\n"
            f"Please log in to your dashboard to review and respond to this request.\n\n"
            f"Best regards,\nThe OccaServe Team"
        )
        EmailService._send_email(
            user.email,
            f"New {subject_prefix} Request ({ref_id}) - OccaServe",
            caterer_email_body
        )

        # 3. SMS Notification to Caterer
        phone = caterer.contact_phone or user.phone_number
        if phone:
            sms_msg = f"OccaServe: New {subject_prefix.lower()} {ref_id} for '{booking.event_name}' on {event_date_str}. Log in to review!"
            await NotificationService._send_sms(phone, sms_msg)

        # 4. Real-time WebSocket
        await manager.broadcast_to_user(user.id, {"type": "booking_update", "message": f"New {subject_prefix.lower()}: {booking.event_name}"})

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
            "Quotation Ready - OccaServe",
            f"Hello,\n\nA new quotation is ready for '{booking.event_name}'. Log in to review and sign the contract."
        )

    @staticmethod
    async def notify_status_update(db: Session, user_id: int, title: str, message: str, link: str, notif_type: str = "info"):
        """Generic status update notification (In-app + Email + Optimized SMS)."""
        user = db.query(models.User).get(user_id)
        if not user: return

        # Auto-detect semantic type for proper UI icons if generic type is passed
        if notif_type in ["info", "success", "warning", "error"]:
            lower_title = title.lower()
            if any(k in lower_title for k in ['booking', 'event', 'reservation', 'contract', 'cancelled', 'rejected', 'completed', 'verified!', 'signed']):
                notif_type = "Booking"
            elif any(k in lower_title for k in ['payment', 'balance', 'deadline', 'settlement', 'downpayment', 'commission', 'proof']):
                notif_type = "Payment"
            elif any(k in lower_title for k in ['review', 'rate', 'feedback']):
                notif_type = "Review"
            elif any(k in lower_title for k in ['identity', 'verify', 'verification', 'kyc', 'alert', 'application', 'account status', 'action required']):
                notif_type = "Verification"
            elif any(k in lower_title for k in ['customer', 'profile']):
                notif_type = "Customer"
            elif any(k in lower_title for k in ['message', 'chat']):
                notif_type = "Message"

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

        # 2. Email (Always send) — Rich HTML version
        user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Valued Customer"
        site_url = settings.SITE_URL if hasattr(settings, 'SITE_URL') else "https://occaserve.com"
        full_link = f"{site_url}{link}" if link and link.startswith('/') else (link or site_url)
        html_body = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        .container {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; }}
        .header {{ background: linear-gradient(135deg, #FF7B54, #ff5722); padding: 28px 30px; text-align: center; border-radius: 12px 12px 0 0; }}
        .header h1 {{ color: white; margin: 0; font-size: 22px; letter-spacing: -0.5px; }}
        .header p {{ color: rgba(255,255,255,0.85); margin: 6px 0 0 0; font-size: 13px; }}
        .content {{ background: #f9f9f9; padding: 32px 30px; border: 1px solid #e8e8e8; border-top: none; }}
        .notif-card {{ background: #fff; border-radius: 10px; padding: 20px 24px; border-left: 4px solid #FF7B54; margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        .notif-title {{ font-size: 17px; font-weight: 700; color: #1e293b; margin-bottom: 10px; }}
        .notif-message {{ font-size: 15px; color: #475569; line-height: 1.7; }}
        .btn {{ display: inline-block; background: #FF7B54; color: white !important; padding: 14px 28px; text-decoration: none; border-radius: 8px; margin-top: 24px; font-weight: 700; font-size: 15px; }}
        .footer {{ text-align: center; margin-top: 28px; font-size: 12px; color: #94a3b8; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>OccaServe</h1>
            <p>Your Premium Event Catering Platform</p>
        </div>
        <div class="content">
            <p style="color:#475569;margin-bottom:0;">Hello, <strong>{user_name}</strong></p>
            <div class="notif-card">
                <div class="notif-title">📢 {title}</div>
                <div class="notif-message">{message}</div>
            </div>
            <a href="{full_link}" class="btn">View Details →</a>
            <p style="margin-top:24px;font-size:13px;color:#94a3b8;">This notification was sent because you have an active account on OccaServe. If you believe this was sent by mistake, please ignore this email.</p>
        </div>
        <div class="footer">
            © 2026 OccaServe Philippines. All rights reserved.<br>
            <a href="{site_url}" style="color:#FF7B54;text-decoration:none;">occaserve.com</a>
        </div>
    </div>
</body>
</html>"""
        EmailService._send_email(user.email, f"OccaServe Update: {title}", message, html_body)

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
                sms_msg = f"OccaServe: {title}. {message}"
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
            type="Payment",
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
            payment_type,
            booking.document_type
        )

        # 3. SMS to Caterer
        phone = caterer.contact_phone or user.phone_number
        if phone:
            sms_msg = f"OccaServe: {payment_type} of PhP{amount:,.2f} received for '{booking.event_name}'. Please verify proof in your dashboard."
            await NotificationService._send_sms(phone, sms_msg)

        # 4. Real-time
        status_class_map = {
            'confirmed': 'ps-badge-confirmed',
            'preparing': 'ps-badge-preparing',
            'completed': 'ps-badge-completed',
            'pending': 'ps-badge-pending',
        }
        status_label_map = {
            'confirmed': 'Confirmed',
            'preparing': 'Preparing',
            'completed': 'Completed',
        }
        await manager.broadcast_to_user(user.id, {
            "type": "booking_update", 
            "booking_id": booking.id,
            "new_status": booking.status,
            "status_label": status_label_map.get(booking.status, booking.status.replace('_', ' ').capitalize()),
            "status_class": status_class_map.get(booking.status, 'ps-badge-draft'),
            "message": f"New payment received: ₱{amount:,.2f}"
        })
        
        # 5. Real-time to Customer
        await manager.broadcast_to_user(booking.user_id, {
            "type": "payment_update",
            "booking_id": booking.id,
            "message": f"Payment of ₱{amount:,.2f} successful!"
        })

    @staticmethod
    async def notify_proof_rejected(db: Session, booking: models.Booking, reason: str):
        """Notifies customer that their payment proof was rejected."""
        # 1. In-App
        notif = models.Notification(
            user_id=booking.user_id,
            title="Action Required: Payment Proof Rejected",
            message=f"Your payment proof for '{booking.event_name}' was rejected. Reason: {reason}",
            type="Payment",
            link=f"/bookings/step/payment/{booking.id}"
        )
        db.add(notif)
        db.commit()

        # 2. Email
        EmailService._send_email(
            booking.user.email,
            "ACTION REQUIRED: Payment Proof Rejected",
            f"Hello,\n\nYour payment proof for Booking #{booking.id} ({booking.event_name}) was rejected for the following reason:\n\n\"{reason}\"\n\nPlease log in and upload a new, clear proof of payment to proceed."
        )

        # 3. Real-time
        await manager.broadcast_to_user(booking.user_id, {
            "type": "payment_rejected",
            "message": f"Payment proof rejected: {reason}",
            "booking_id": booking.id
        })

    @staticmethod
    async def notify_booking_rejected(db: Session, booking: models.Booking, reason: str):
        """Notifies customer that their booking was rejected by the caterer."""
        # 1. In-App
        notif = models.Notification(
            user_id=booking.user_id,
            title="Booking Rejected",
            message=f"Your booking request for '{booking.event_name}' was rejected. Reason: {reason}",
            type="Booking",
            link="/customer/bookings"
        )
        db.add(notif)
        db.commit()

        # 2. Email
        EmailService._send_email(
            booking.user.email,
            "Booking Request Update - OccaServe",
            f"Hello,\n\nWe regret to inform you that your booking request for '{booking.event_name}' has been rejected by the caterer.\n\nReason: {reason}\n\nYou can browse other caterers on our platform."
        )

        # 3. Real-time
        await manager.broadcast_to_user(booking.user_id, {
            "type": "booking_rejected",
            "message": f"Booking rejected: {reason}",
            "booking_id": booking.id
        })

    @staticmethod
    async def notify_booking_cancelled(db: Session, booking: models.Booking, reason: str, cancelled_by: str = "User"):
        """Notifies the other party when a booking is cancelled."""
        target_user_id = booking.caterer.user_id if cancelled_by == "Customer" else booking.user_id
        target_email = booking.caterer.user.email if cancelled_by == "Customer" else booking.user.email
        
        # 1. In-App
        notif = models.Notification(
            user_id=target_user_id,
            title="Booking Cancelled",
            message=f"The booking for '{booking.event_name}' has been cancelled by the {cancelled_by}. Reason: {reason}",
            type="Booking",
            link="/caterer/bookings" if cancelled_by == "Customer" else "/customer/bookings"
        )
        db.add(notif)
        db.commit()

        # 2. Email
        EmailService._send_email(
            target_email,
            "Booking Cancellation Notice - OccaServe",
            f"Hello,\n\nThis is to notify you that the booking for '{booking.event_name}' has been cancelled by the {cancelled_by}.\n\nReason: {reason}"
        )

        # 3. Real-time
        await manager.broadcast_to_user(target_user_id, {
            "type": "booking_cancelled",
            "message": f"Booking cancelled by {cancelled_by}",
            "booking_id": booking.id
        })
