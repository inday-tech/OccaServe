import datetime
import calendar
from sqlalchemy.orm import Session
from app.db.models import Booking, BillingInvoice, Notification, CatererProfile, User


def billing_period_due_date(billing_period: str, fallback_date=None):
    try:
        period_date = datetime.datetime.strptime(billing_period, "%B %Y").date()
    except (TypeError, ValueError):
        period_date = fallback_date or datetime.date.today()

    last_day = calendar.monthrange(period_date.year, period_date.month)[1]
    return datetime.date(period_date.year, period_date.month, last_day)

def generate_caterer_reminders(user_id: int, db: Session):
    """
    Intelligent Calendar Reminder System
    Proactively checks bookings and generates contextual notifications
    if they haven't been generated yet today.
    """
    today = datetime.date.today()
    
    profile = db.query(CatererProfile).filter(CatererProfile.user_id == user_id).first()
    if not profile:
        return
        
    active_bookings = db.query(Booking).filter(
        Booking.caterer_id == profile.id,
        Booking.status.notin_(['draft', 'pending_quotation', 'cancelled', 'completed'])
    ).all()

    # Load existing daily reminders once. The old loop issued a SELECT and
    # committed separately for every overdue/near-term booking.
    day_start = datetime.datetime.combine(today, datetime.time.min)
    day_end = day_start + datetime.timedelta(days=1)
    existing_daily = db.query(Notification.title, Notification.link).filter(
        Notification.user_id == user_id,
        Notification.created_at >= day_start,
        Notification.created_at < day_end,
    ).all()
    existing_daily_keys = {(title, link) for title, link in existing_daily}
    new_notifications = []
    
    for booking in active_bookings:
        if not booking.event_date: continue
        
        days_until = (booking.event_date - today).days
        
        # Determine Reminder Type
        title = None
        message = None
        n_type = "info"
        link = f"/caterer/bookings?focus={booking.id}"
        
        if days_until == 7:
            title = "Upcoming Event Next Week"
            message = f"You have a {booking.event_type} in 7 days. Suggested: Review menu, check inventory, confirm venue."
            n_type = "reminder"
        elif days_until == 3:
            title = "Prepare Event Logistics"
            message = f"Your {booking.event_type} is in 3 days. Prepare equipment, assign staff."
            n_type = "warning"
        elif days_until == 1:
            title = "Tomorrow's Event!"
            message = f"Review checklist and delivery schedule for {booking.event_type} tomorrow."
            n_type = "warning"
        elif days_until == 0:
            title = "Event Day: " + str(booking.event_type)
            message = "Today is the event! Start kitchen prep and equipment loading."
            n_type = "alert"
        elif days_until < 0 and booking.status != 'completed':
            title = "Overdue Booking Action"
            message = f"The {booking.event_type} has passed. Please mark it as completed or archived."
            n_type = "alert"
            
        # Payment Reminders
        if booking.payment_status == 'pending' and booking.status == 'confirmed':
            if days_until == 3:
                title = "Payment Reminder"
                message = f"Customer has an outstanding balance for {booking.event_type} in 3 days."
                n_type = "warning"
        
        # Only create if not already created today
        if title:
            if (title, link) not in existing_daily_keys:
                new_notifications.append(Notification(
                    user_id=user_id,
                    title=title,
                    message=message,
                    type=n_type,
                    link=link
                ))
                existing_daily_keys.add((title, link))

    invoices = db.query(BillingInvoice).filter(
        BillingInvoice.caterer_id == profile.id,
        BillingInvoice.status.in_(["pending", "overdue"]),
        BillingInvoice.payment_proof_url.is_(None)
    ).all()
    invoice_changes = False
    existing_invoice_reminders = {
        (row.title, row.link) for row in db.query(Notification.title, Notification.link).filter(
            Notification.user_id == user_id,
            Notification.link.like('/caterer/payments#commission-invoice-%'),
        ).all()
    }

    for invoice in invoices:
        fallback_date = invoice.created_at.date() if invoice.created_at else today
        due_date = invoice.due_date or billing_period_due_date(invoice.billing_period, fallback_date)
        if invoice.due_date is None:
            invoice.due_date = due_date
            invoice_changes = True

        days_until_due = (due_date - today).days
        if days_until_due > 3:
            continue

        is_overdue = days_until_due < 0
        title = "Commission Invoice Overdue" if is_overdue else "Commission Payment Due Soon"
        invoice_ref = f"INV-{invoice.id:04d}"
        link = f"/caterer/payments#commission-invoice-{invoice.id}"
        message = (
            f"Commission invoice {invoice_ref} for {invoice.billing_period} "
            f"(₱{float(invoice.amount or 0):,.2f}) was due on {due_date:%b %d, %Y}."
            if is_overdue else
            f"Commission invoice {invoice_ref} for {invoice.billing_period} "
            f"(₱{float(invoice.amount or 0):,.2f}) is due on {due_date:%b %d, %Y}. "
            "Please submit the payment proof before the due date."
        )
        if (title, link) not in existing_invoice_reminders:
            new_notifications.append(Notification(
                user_id=user_id,
                title=title,
                message=message,
                type="alert" if is_overdue else "reminder",
                link=link
            ))
            existing_invoice_reminders.add((title, link))
            invoice_changes = True

    if new_notifications:
        db.add_all(new_notifications)
    if invoice_changes or new_notifications:
        db.commit()
