import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models import Booking, Notification, CatererProfile, User

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
            # Check if this exact reminder was already fired today
            existing = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.title == title,
                func.date(Notification.created_at) == today,
                Notification.link == link
            ).first()
            
            if not existing:
                new_notif = Notification(
                    user_id=user_id,
                    title=title,
                    message=message,
                    type=n_type,
                    link=link
                )
                db.add(new_notif)
                db.commit()
