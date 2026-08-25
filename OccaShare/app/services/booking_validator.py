from datetime import datetime, date
from sqlalchemy.orm import Session
from app.db import models

class BookingValidator:
    """
    Centralized validation logic for Bookings.
    Implements Multi-stage Booking Validation to ensure bookings
    do not proceed if the event date has passed, or if lead time / deadlines are violated.
    """

    @staticmethod
    def validate_booking_state(db: Session, booking: models.Booking, update_if_expired: bool = True) -> tuple[bool, str]:
        """
        Validates the booking state. 
        Returns (is_valid: bool, error_message: str).
        If update_if_expired is True, it will automatically update the booking status to 'expired' if invalid.
        """
        if not booking:
            return False, "Booking not found."

        # 1. If already expired or cancelled or completed, don't allow transitions
        terminal_statuses = ["expired", "cancelled", "completed", "rejected"]
        if booking.status in terminal_statuses:
            return False, f"Booking cannot be modified because its status is '{booking.status}'."

        now = datetime.now()
        current_date = now.date()
        
        # 2. Check Event Date Passed
        if booking.event_date < current_date:
            BookingValidator._expire_booking(db, booking, "Event date has already passed", update_if_expired)
            return False, "The scheduled event date has already passed. This booking cannot be continued."

        # 3. Check Minimum Lead Time (Only if booking is not yet confirmed/paid)
        # If the booking is already accepted or contract signed, we assume the caterer agreed to the timeline.
        pre_acceptance_statuses = ["draft", "pending", "pending_quotation", "awaiting_caterer"]
        if booking.status in pre_acceptance_statuses:
            caterer = db.query(models.CatererProfile).get(booking.caterer_id)
            if caterer:
                lead_time_days = caterer.booking_lead_time or 0
                days_until_event = (booking.event_date - current_date).days
                if days_until_event < lead_time_days:
                    BookingValidator._expire_booking(db, booking, f"Minimum lead time of {lead_time_days} days not met", update_if_expired)
                    return False, f"The caterer requires at least {lead_time_days} days advance booking. Your event is only {days_until_event} days away."

        # 4. Check Booking General Expiration (if set)
        if booking.expires_at and booking.expires_at.replace(tzinfo=None) < now:
            BookingValidator._expire_booking(db, booking, "Booking deadline passed", update_if_expired)
            return False, "The booking has expired as it exceeded the allowed timeframe."

        # 5. Check Contract Expiration
        contract = db.query(models.BookingContract).filter(models.BookingContract.booking_id == booking.id).first()
        if contract and contract.status != "fully_signed":
            if contract.expires_at and contract.expires_at.replace(tzinfo=None) < now:
                BookingValidator._expire_booking(db, booking, "Contract signing deadline passed", update_if_expired)
                # Also expire contract
                if update_if_expired:
                    contract.status = "expired"
                    db.commit()
                return False, "The contract signing deadline has passed. This contract is no longer valid."

        return True, "Booking is valid."

    @staticmethod
    def _expire_booking(db: Session, booking: models.Booking, reason: str, commit: bool):
        if commit:
            booking.status = "expired"
            # We can log the reason in booking history or caterer notes
            if booking.caterer_notes:
                booking.caterer_notes += f"\n[System] Expired: {reason}"
            else:
                booking.caterer_notes = f"[System] Expired: {reason}"
            
            history = models.BookingHistory(
                booking_id=booking.id,
                status="expired",
                notes=f"Auto-expired by system: {reason}"
            )
            db.add(history)
            db.commit()
