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

    @staticmethod
    async def notify_proof_rejected(db: Session, booking: models.Booking, reason: str):
        """Notifies customer that their payment proof was rejected."""
        # 1. In-App
        notif = models.Notification(
            user_id=booking.user_id,
            title="Action Required: Payment Proof Rejected",
            message=f"Your payment proof for '{booking.event_name}' was rejected. Reason: {reason}",
            type="warning",
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
            type="error",
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
            type="warning",
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
    @staticmethod
    async def notify_payout_requested(db: Session, payout: models.Payout):
        """Notifies caterer that their payout request has been received."""
        caterer = payout.caterer
        user = caterer.user
        if not user: return

        # 1. In-App
        notif = models.Notification(
            user_id=user.id,
            title="Withdrawal Requested",
            message=f"Your request for ₱{payout.amount:,.2f} has been received and is being processed.",
            type="info",
            link="/caterer/payments"
        )
        db.add(notif)
        db.commit()

        # 2. Email
        EmailService._send_email(
            user.email,
            "Withdrawal Request Received - OccaServe",
            f"Hello {caterer.business_name},\n\nWe have received your withdrawal request for ₱{payout.amount:,.2f}.\nOur team will verify the transaction and release the funds to your registered {caterer.payout_method} within 24-48 hours."
        )

        # 3. SMS (Only if offline)
        is_online = user.id in manager.user_connections
        if not is_online:
            phone = caterer.contact_phone or user.phone_number
            if phone:
                sms_msg = f"OccaServe: Withdrawal request for PhP{payout.amount:,.2f} received. Processing time: 24-48 hours."
                await NotificationService._send_sms(phone, sms_msg)

        # 4. Real-time to Caterer
        await manager.broadcast_to_user(user.id, {
            "type": "payout_update", 
            "message": f"Withdrawal of ₱{payout.total_amount:,.2f} requested",
            "payout_id": payout.id
        })

        # 5. --- NOTIFY ALL ADMINS ---
        admins = db.query(models.User).filter(models.User.role == "admin", models.User.is_archived == False).all()
        for admin in admins:
            # In-App for Admin
            admin_notif = models.Notification(
                user_id=admin.id,
                title="New Withdrawal Request",
                message=f"Caterer '{caterer.business_name}' is requesting ₱{payout.total_amount:,.2f} via {caterer.payout_method or 'GCash'}.",
                type="warning",
                link="/admin/payouts"
            )
            db.add(admin_notif)
            
            # Email to Admin
            EmailService._send_email(
                admin.email,
                f"URGENT: New Payout Request from {caterer.business_name}",
                f"Hello Admin,\n\nA new withdrawal request has been submitted by {caterer.business_name}.\n\n" +
                f"Amount: ₱{payout.total_amount:,.2f}\n" +
                f"Method: {caterer.payout_method or 'GCash'}\n" +
                f"Ref ID: {payout.payout_reference}\n\n" +
                "Please log in to the Admin Panel to review and process this payout."
            )
        
        db.commit()

        # Real-time Broadcast to all Admins
        await manager.broadcast_to_role("admin", {
            "type": "new_payout_request",
            "message": f"New payout request: ₱{payout.total_amount:,.2f} from {caterer.business_name}",
            "amount": payout.total_amount,
            "caterer": caterer.business_name
        })

    @staticmethod
    async def notify_payout_completed(payout_id: int, db: Session):
        """Notifies caterer that their payout has been released/completed."""
        payout = db.query(models.Payout).get(payout_id)
        if not payout: return
        
        caterer = payout.caterer
        user = caterer.user
        if not user: return

        # 1. In-App
        notif = models.Notification(
            user_id=user.id,
            title="Withdrawal Completed!",
            message=f"Your funds (₱{payout.total_amount:,.2f}) have been successfully transferred to your {caterer.payout_method}.",
            type="success",
            link="/caterer/payments"
        )
        db.add(notif)
        db.commit()

        # 2. Email
        EmailService._send_email(
            user.email,
            "Withdrawal Successful - OccaServe",
            f"Great news {caterer.business_name}!\n\nYour withdrawal request of ₱{payout.total_amount:,.2f} has been successfully processed and transferred.\n\n" +
            f"Status: COMPLETED\n" +
            f"Notes: {payout.admin_notes or 'Processed successfully'}\n\n" +
            "Thank you for being a valued partner of OccaServe!"
        )

        # 3. SMS (Critical for success)
        phone = caterer.contact_phone or user.phone_number
        if phone:
            sms_msg = f"OccaServe: Your withdrawal of PhP{payout.total_amount:,.2f} is now COMPLETED. Please check your {caterer.payout_method} account."
            await NotificationService._send_sms(phone, sms_msg)

        # 4. Real-time
        await manager.broadcast_to_user(user.id, {
            "type": "payout_completed",
            "message": f"Withdrawal of ₱{payout.total_amount:,.2f} completed successfully!",
            "payout_id": payout.id
        })
