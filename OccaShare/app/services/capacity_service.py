from datetime import datetime, timedelta, date, time as dt_time, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Dict, Tuple
from ..db import models

class CapacityService:
    @staticmethod
    def validate_booking_capacity(db: Session, caterer_id: int, event_date: date, event_time: dt_time, event_end_time: dt_time, requested_services: List[Tuple[int, int]], current_booking_id: int = None) -> Tuple[bool, str]:
        """
        Validates if there is enough service capacity (staff or units) for the given requested_services on the event date/time.
        requested_services: list of tuples (service_id, required_qty)
        Returns (is_valid, error_message)
        """
        if not requested_services:
            return True, ""
            
        # Get all confirmed overlapping bookings for this caterer on the same day
        active_bookings_query = db.query(models.Booking).filter(
            models.Booking.caterer_id == caterer_id,
            models.Booking.event_date == event_date,
            models.Booking.status.notin_(['cancelled', 'draft'])
        )
        
        if current_booking_id:
            active_bookings_query = active_bookings_query.filter(models.Booking.id != current_booking_id)
            
        all_active_bookings = active_bookings_query.all()
        
        active_bookings_today = []
        now = datetime.now(timezone.utc) if getattr(datetime, 'now', None) else datetime.now()
        for b in all_active_bookings:
            # Hard locks
            if b.status in ['confirmed', 'preparing', 'in_progress', 'on_the_way', 'completed']:
                active_bookings_today.append(b)
            # Soft locks (expire after 48 hours)
            elif b.status in ['pending', 'pending_quotation', 'awaiting_payment', 'awaiting_caterer', 'pending_review']:
                # Calculate age of booking
                created_at = b.created_at
                if created_at:
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=now.tzinfo)
                    age_hours = (now - created_at).total_seconds() / 3600
                    if age_hours <= 48:
                        active_bookings_today.append(b)
        
        # Check each requested service
        for service_id, required_qty in requested_services:
            service = db.query(models.Service).get(service_id)
            if not service:
                continue
                
            if getattr(service, 'allow_freelancers', False):
                continue # Infinite capacity allowed
                
            buffer_hours = getattr(service, 'buffer_time_hours', 0)
            
            # Calculate requested event window for this specific service
            req_start_dt = datetime.combine(event_date, event_time) - timedelta(hours=buffer_hours)
            req_end_dt = datetime.combine(event_date, event_end_time) + timedelta(hours=buffer_hours) if event_end_time else req_start_dt + timedelta(hours=(service.base_duration_hours or 3) + buffer_hours)
            
            used_qty = 0
            
            # Check overlap with existing active bookings today
            for b in active_bookings_today:
                if not b.event_time: continue
                
                # Check if this booking uses the same service
                booking_service_item = db.query(models.BookingMenuItem).filter(
                    models.BookingMenuItem.booking_id == b.id,
                    models.BookingMenuItem.service_id == service_id
                ).first()
                
                if not booking_service_item:
                    continue
                    
                # Calculate existing booking window for this service
                b_start_dt = datetime.combine(b.event_date, b.event_time) - timedelta(hours=buffer_hours)
                b_end_dt = datetime.combine(b.event_date, b.event_end_time) + timedelta(hours=buffer_hours) if b.event_end_time else b_start_dt + timedelta(hours=(service.base_duration_hours or 3) + buffer_hours)
                
                # Check overlap: (StartA < EndB) and (EndA > StartB)
                if req_start_dt < b_end_dt and req_end_dt > b_start_dt:
                    used_qty += booking_service_item.quantity
                    
            if (used_qty + required_qty) > service.max_available:
                service_type_name = "personnel" if service.capacity_type == "staff_based" else "units"
                return False, f"Not enough available {service_type_name} for '{service.name}'. Available: {service.max_available - used_qty}, Required: {required_qty}."
                
        return True, ""
