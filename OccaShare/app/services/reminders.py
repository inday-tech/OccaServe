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
        return []
        
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
        booking_ref = booking.booking_ref or booking.display_booking_ref or f"BK-{booking.id:03d}"
        event_name = booking.event_name or booking.event_type or f"Booking {booking_ref}"
        
        # Determine Reminder Type
        title = None
        message = None
        n_type = "info"
        link = f"/caterer/bookings?focus={booking.id}"
        
        if days_until == 7:
            title = f"Upcoming Event Next Week: {event_name}"
            message = f"'{event_name}' ({booking_ref}) is scheduled for {booking.event_date}. Review its details and preparation plan."
            n_type = "reminder"
        elif days_until == 3:
            title = f"Event Logistics Due Soon: {event_name}"
            message = f"'{event_name}' ({booking_ref}) is scheduled for {booking.event_date}. Review venue, equipment, and staffing."
            n_type = "warning"
        elif days_until == 1:
            title = f"Event Tomorrow: {event_name}"
            message = f"'{event_name}' ({booking_ref}) is scheduled for tomorrow. Review its checklist and delivery schedule."
            n_type = "warning"
        elif days_until == 0:
            title = f"Event Today: {event_name}"
            message = f"'{event_name}' ({booking_ref}) is scheduled for today. Review the booking and its preparation status."
            n_type = "alert"
        elif days_until < 0 and booking.status != 'completed':
            title = f"Booking Needs Follow-up: {event_name}"
            message = f"The scheduled date for '{event_name}' ({booking_ref}) was {booking.event_date}. Review the booking and update its status if appropriate."
            n_type = "alert"
            
        # Payment Reminders
        if booking.payment_status == 'pending' and booking.status == 'confirmed':
            if days_until == 3:
                from app.services.payment_service import PaymentService
                payment_summary = PaymentService.get_payment_summary(booking)
                outstanding = float(payment_summary.get("remaining_balance") or 0)
                title = f"Payment Follow-up: {event_name}"
                message = (
                    f"'{event_name}' ({booking_ref}) has PHP {outstanding:,.2f} remaining "
                    f"for the event on {booking.event_date}. Review its payment details."
                    if outstanding > 0.009
                    else f"Review the payment status for '{event_name}' ({booking_ref}) before the event on {booking.event_date}."
                )
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
    return new_notifications
