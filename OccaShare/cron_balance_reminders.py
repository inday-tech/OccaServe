import os
import sys
import asyncio
from datetime import datetime, date, timedelta

# Add parent dir to path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from sqlalchemy.orm import Session
from app.db import database, models
from app.services.notification import NotificationService

async def run_reminders():
    print(f"[{datetime.now()}] Starting Automated Balance Reminder Engine...")
    
    # Get DB session directly
    db_gen = database.get_db()
    db = next(db_gen)
    
    try:
        today = date.today()
        
        # We only want bookings that are confirmed, have a balance due date, and are not fully paid
        # Not fully paid means payment_status not in ('paid', 'proof_submitted', 'balance_reupload_requested')
        active_bookings = db.query(models.Booking).filter(
            models.Booking.status == 'confirmed',
            models.Booking.payment_plan != 'full',
            models.Booking.balance_due_date.isnot(None),
            ~models.Booking.payment_status.in_(['paid', 'proof_submitted', 'balance_reupload_requested'])
        ).all()
        
        count_reminders = 0
        
        for booking in active_bookings:
            due_date = booking.balance_due_date
            if isinstance(due_date, datetime):
                due_date = due_date.date()
                
            days_left = (due_date - today).days
            
            # Decide on the message based on days_left
            title = None
            msg = None
            
            if days_left == 3:
                title = "Gentle Reminder: Balance Due in 3 Days"
                msg = f"Your remaining balance for '{booking.event_name}' is due on {due_date.strftime('%B %d, %Y')}. Please settle it soon to avoid any issues."
            elif days_left == 2:
                title = "Reminder: Balance Due in 2 Days"
                msg = f"Just a reminder that your payment for '{booking.event_name}' is due in 2 days. Settle your balance via your dashboard."
            elif days_left == 1:
                title = "Action Required: Balance Due Tomorrow!"
                msg = f"Your final payment for '{booking.event_name}' is due tomorrow! Settle it to finalize your booking."
            elif days_left == 0:
                title = "URGENT: Balance Due Today"
                msg = f"Today is the deadline for your remaining balance for '{booking.event_name}'. Please pay immediately."
            elif days_left < 0:
                # Overdue
                title = "CRITICAL: Payment Overdue"
                msg = f"Your payment for '{booking.event_name}' is OVERDUE by {abs(days_left)} days. Please settle your account immediately to prevent cancellation."
                if booking.payment_status != 'overdue':
                    booking.payment_status = 'overdue'
                    db.commit()
            
            if title and msg:
                # Calculate balance
                total = booking.total_price or booking.total_amount or 0.0
                paid = booking.amount_paid or 0.0
                balance = total - paid
                
                if balance > 0:
                    link = f"/customer/bookings/manage/{booking.id}"
                    if booking.package_id:
                        link = f"/customer/bookings/manage-package/{booking.id}"
                        
                    await NotificationService.notify_status_update(
                        db,
                        booking.user_id,
                        title,
                        msg,
                        link
                    )
                    count_reminders += 1
                    print(f"Sent '{title}' to User ID {booking.user_id} for Booking #{booking.id}")
        
        print(f"[{datetime.now()}] Engine finished. Sent {count_reminders} reminders.")
        
    except Exception as e:
        print(f"Error running reminders: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_reminders())
