from datetime import datetime, date, time as dt_time, timedelta
from typing import Optional, Union, Dict, Any
from sqlalchemy.orm import Session
from ..db import models


class AvailabilityService:
    @staticmethod
    def get_operating_hours_error(
        target_time: dt_time,
        settings: Dict[str, Any],
    ) -> Optional[str]:
        """Return a customer-facing error when ingress falls outside service hours."""
        try:
            open_time = datetime.strptime(settings["open_time"], "%H:%M").time()
        except (KeyError, TypeError, ValueError):
            open_time = dt_time(8, 0)

        try:
            close_time = datetime.strptime(settings["close_time"], "%H:%M").time()
        except (KeyError, TypeError, ValueError):
            close_time = dt_time(20, 0)

        if target_time >= close_time:
            close_label = close_time.strftime("%I:%M %p").lstrip("0")
            return f"Ingress must be before {close_label}. Choose an earlier time."
        if target_time < open_time:
            return "The selected event time is outside the caterer’s available hours. Please select another time."
        return None

    @staticmethod
    def get_caterer_availability_settings(caterer: models.CatererProfile) -> Dict[str, Any]:
        """
        Extracts and normalizes the caterer's availability settings.
        Caterer Business Settings -> Booking/Event Availability is the single source of truth.
        """
        rules = caterer.scheduling_rules or {}
        event_avail = rules.get("event_availability", {})
        bh = rules.get("business_hours", {})

        availability_status = event_avail.get("availability_status", "Available")

        # Operating days (default Mon-Sun)
        operating_days = event_avail.get(
            "operating_days",
            bh.get("operating_days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        )
        if not operating_days or not isinstance(operating_days, list):
            operating_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        # Operating hours
        open_time_str = event_avail.get("open_time", bh.get("open_time", "08:00")) or "08:00"
        close_time_str = event_avail.get("close_time", bh.get("close_time", "20:00")) or "20:00"

        # Lead time in days
        raw_lead = event_avail.get("booking_lead_time", caterer.booking_lead_time)
        try:
            lead_time = max(0, int(raw_lead)) if raw_lead is not None else 3
        except (ValueError, TypeError):
            lead_time = 3

        # Max advance booking in days
        raw_advance = event_avail.get(
            "max_advance_booking_days",
            rules.get("booking_rules", {}).get("max_advance_booking_days", 180)
        )
        try:
            max_advance_days = max(1, int(raw_advance)) if raw_advance is not None else 180
        except (ValueError, TypeError):
            max_advance_days = 180

        # Max events per day
        raw_max_events = event_avail.get("max_events_per_day", caterer.max_bookings_per_day)
        try:
            max_events_per_day = max(1, int(raw_max_events)) if raw_max_events is not None else 1
        except (ValueError, TypeError):
            max_events_per_day = 1

        # Blocked dates list
        raw_blocked = event_avail.get("blocked_dates", [])
        blocked_dates_list = []
        if isinstance(raw_blocked, list):
            for item in raw_blocked:
                if isinstance(item, dict):
                    d_str = str(item.get("date", "")).strip()
                    if d_str:
                        blocked_dates_list.append({
                            "date": d_str,
                            "reason": item.get("reason", "Unavailable")
                        })
                elif isinstance(item, str) and item.strip():
                    blocked_dates_list.append({
                        "date": item.strip(),
                        "reason": "Unavailable"
                    })

        return {
            "availability_status": availability_status,
            "operating_days": operating_days,
            "open_time": open_time_str,
            "close_time": close_time_str,
            "booking_lead_time": lead_time,
            "max_advance_booking_days": max_advance_days,
            "max_events_per_day": max_events_per_day,
            "blocked_dates": blocked_dates_list
        }

    @classmethod
    def check_caterer_availability(
        cls,
        db: Session,
        caterer_id: int,
        event_date: Union[date, str],
        event_time: Optional[Union[dt_time, str]] = None,
        exclude_booking_id: Optional[int] = None,
        event_end_time: Optional[Union[dt_time, str]] = None,
    ) -> Dict[str, Any]:
        """
        Validates whether a given caterer is available on the specified date and time.
        Returns a dict:
            {
                "available": bool,
                "code": str,       # 'available' | 'temporarily_unavailable' | 'unavailable_day' |
                                   # 'too_soon' | 'too_far' | 'blocked_date' | 'capacity_reached' |
                                   # 'outside_hours' | 'slot_conflict'
                "message": str,
                "settings": dict
            }
        """
        caterer = db.query(models.CatererProfile).filter(models.CatererProfile.id == caterer_id).first()
        if not caterer and hasattr(db.query(models.CatererProfile), 'get'):
            try:
                caterer = db.query(models.CatererProfile).get(caterer_id)
            except Exception:
                pass
        if not caterer:
            return {
                "available": False,
                "code": "not_found",
                "message": "Caterer profile not found.",
                "settings": {}
            }

        settings = cls.get_caterer_availability_settings(caterer)

        # 1. Availability Status Check
        if settings["availability_status"] == "Temporarily Unavailable":
            return {
                "available": False,
                "code": "temporarily_unavailable",
                "reason": "temporarily_unavailable",
                "message": "This caterer is temporarily unavailable and not accepting new bookings.",
                "settings": settings
            }

        # Parse target date
        target_date: date
        if isinstance(event_date, str):
            try:
                target_date = datetime.strptime(event_date.strip(), "%Y-%m-%d").date()
            except ValueError:
                return {
                    "available": False,
                    "code": "invalid_date",
                    "reason": "invalid_date",
                    "message": "Invalid date format. Expected YYYY-MM-DD.",
                    "settings": settings
                }
        else:
            target_date = event_date

        today = date.today()

        # 2. Operating Days Check
        day_of_week = target_date.strftime("%A")
        if day_of_week not in settings["operating_days"]:
            return {
                "available": False,
                "code": "unavailable_day",
                "reason": "unavailable_day",
                "message": "The caterer does not accept bookings on this day. Please select another date.",
                "settings": settings
            }

        # 3. Minimum Booking Lead Time Check
        lead_time = settings["booking_lead_time"]
        min_allowed_date = today + timedelta(days=lead_time)
        if target_date < min_allowed_date:
            unit = "day" if lead_time == 1 else "days"
            return {
                "available": False,
                "code": "too_soon",
                "reason": "too_soon",
                "message": f"This caterer requires bookings at least {lead_time} {unit} before the event date. Please select a later date.",
                "settings": settings
            }

        # 4. Maximum Advance Booking Check
        max_advance_days = settings["max_advance_booking_days"]
        max_allowed_date = today + timedelta(days=max_advance_days)
        if target_date > max_allowed_date:
            if max_advance_days >= 365 and max_advance_days % 365 == 0:
                years = max_advance_days // 365
                duration_str = f"{years} year{'s' if years > 1 else ''}"
            elif max_advance_days >= 30 and max_advance_days % 30 == 0:
                months = max_advance_days // 30
                duration_str = f"{months} month{'s' if months > 1 else ''}"
            elif max_advance_days >= 30:
                months = round(max_advance_days / 30)
                duration_str = f"{months} months"
            else:
                duration_str = f"{max_advance_days} days"

            return {
                "available": False,
                "code": "too_far_in_advance",
                "reason": "too_far_in_advance",
                "message": f"This caterer only accepts bookings up to {duration_str} in advance.",
                "settings": settings
            }

        # 5. Operating Hours Check (if event_time provided)
        target_time: Optional[dt_time] = None
        if event_time:
            if isinstance(event_time, str):
                cleaned_time = event_time.strip()
                if cleaned_time:
                    try:
                        target_time = datetime.strptime(cleaned_time, "%H:%M").time()
                    except ValueError:
                        try:
                            target_time = datetime.strptime(cleaned_time, "%H:%M:%S").time()
                        except ValueError:
                            pass
            else:
                target_time = event_time

        if target_time:
            hours_error = cls.get_operating_hours_error(target_time, settings)
            if hours_error:
                return {
                    "available": False,
                    "code": "outside_hours",
                    "reason": "outside_hours",
                    "message": hours_error,
                    "settings": settings
                }

        target_end_time: Optional[dt_time] = None
        if event_end_time:
            if isinstance(event_end_time, str):
                try:
                    target_end_time = datetime.strptime(event_end_time.strip(), "%H:%M").time()
                except ValueError:
                    try:
                        target_end_time = datetime.strptime(event_end_time.strip(), "%H:%M:%S").time()
                    except ValueError:
                        pass
            else:
                target_end_time = event_end_time

        # 5. Blocked / Unavailable Dates Check
        target_date_str = target_date.strftime("%Y-%m-%d")
        blocked_in_settings = any(item["date"] == target_date_str for item in settings["blocked_dates"])

        db_blocked = db.query(models.Availability).filter(
            models.Availability.caterer_id == caterer_id,
            models.Availability.date == target_date,
            models.Availability.is_available == False
        ).first()

        if blocked_in_settings or db_blocked:
            return {
                "available": False,
                "code": "blocked_date",
                "reason": "blocked_date",
                "message": "This date is unavailable for this caterer. Please select another date.",
                "settings": settings
            }

        # 6. Maximum Events Per Day Capacity Check
        max_events = settings["max_events_per_day"]
        if max_events and max_events > 0:
            active_events_query = db.query(models.Booking).filter(
                models.Booking.caterer_id == caterer_id,
                models.Booking.event_date == target_date,
                models.Booking.status.in_([
                    'confirmed', 'preparing', 'in_progress', 'on_the_way', 'completed',
                    'awaiting_payment', 'pending_review', 'pending_quotation', 'pending', 'pending_payment', 'awaiting_caterer'
                ])
            )
            if exclude_booking_id:
                active_events_query = active_events_query.filter(models.Booking.id != exclude_booking_id)

            active_events_count = active_events_query.count()
            json_events_query = db.query(models.Booking).filter(
                models.Booking.caterer_id == caterer_id,
                models.Booking.status.in_([
                    'confirmed', 'preparing', 'in_progress', 'on_the_way', 'completed',
                    'awaiting_payment', 'pending_review', 'pending_quotation', 'pending', 'pending_payment', 'awaiting_caterer'
                ]),
                models.Booking.custom_requirements["events"].contains([{"event_date": target_date_str}]),
            )
            if exclude_booking_id:
                json_events_query = json_events_query.filter(models.Booking.id != exclude_booking_id)
            for existing_booking in json_events_query.all():
                booking_events = (
                    existing_booking.custom_requirements.get("events", [])
                    if isinstance(existing_booking.custom_requirements, dict)
                    else []
                )
                matching_events = [
                    item for item in booking_events
                    if isinstance(item, dict) and item.get("event_date") == target_date_str
                ] if isinstance(booking_events, list) else []
                legacy_count = 1 if existing_booking.event_date == target_date else 0
                active_events_count += max(len(matching_events) - legacy_count, 0)
            if active_events_count >= max_events:
                return {
                    "available": False,
                    "code": "daily_capacity_reached",
                    "reason": "daily_capacity_reached",
                    "message": "The caterer has reached the maximum number of events for this date. Please select another date.",
                    "settings": settings
                }

        # 7. Slot Overlap / Conflict with Confirmed Booking
        if target_time:
            same_day_confirmed = db.query(models.Booking).filter(
                models.Booking.caterer_id == caterer_id,
                models.Booking.event_date == target_date,
                models.Booking.status.in_(['confirmed', 'preparing', 'in_progress', 'on_the_way', 'completed', 'pending_review'])
            )
            if exclude_booking_id:
                same_day_confirmed = same_day_confirmed.filter(models.Booking.id != exclude_booking_id)

            same_day_json = db.query(models.Booking).filter(
                models.Booking.caterer_id == caterer_id,
                models.Booking.status.in_(['confirmed', 'preparing', 'in_progress', 'on_the_way', 'completed', 'pending_review']),
                models.Booking.custom_requirements["events"].contains([{"event_date": target_date_str}]),
            )
            if exclude_booking_id:
                same_day_json = same_day_json.filter(models.Booking.id != exclude_booking_id)

            turnover_hours = 2.0
            rules_pkg = caterer.scheduling_rules.get("package_rules", {}) if caterer.scheduling_rules else {}
            if rules_pkg and "turnover_time_hours" in rules_pkg:
                try:
                    turnover_hours = float(rules_pkg["turnover_time_hours"])
                except Exception:
                    turnover_hours = 2.0

            confirmed_bookings = {
                booking.id: booking
                for booking in same_day_confirmed.all()
            }
            for booking in same_day_json.all():
                confirmed_bookings[booking.id] = booking

            for confirmed_booking in confirmed_bookings.values():
                saved_events = (
                    confirmed_booking.custom_requirements.get("events", [])
                    if isinstance(confirmed_booking.custom_requirements, dict)
                    else []
                )
                matching_events = [
                    item for item in saved_events
                    if isinstance(item, dict) and item.get("event_date") == target_date_str
                ] if isinstance(saved_events, list) else []
                if matching_events:
                    schedules = [
                        (item.get("ingress"), item.get("egress"))
                        for item in matching_events
                    ]
                elif confirmed_booking.event_date == target_date:
                    schedules = [(confirmed_booking.event_time, confirmed_booking.event_end_time)]
                else:
                    schedules = []

                for ingress, egress in schedules:
                    if isinstance(ingress, str):
                        try:
                            ingress = datetime.strptime(ingress, "%H:%M").time()
                        except ValueError:
                            try:
                                ingress = datetime.strptime(ingress, "%H:%M:%S").time()
                            except ValueError:
                                ingress = None
                    if isinstance(egress, str):
                        try:
                            egress = datetime.strptime(egress, "%H:%M").time()
                        except ValueError:
                            try:
                                egress = datetime.strptime(egress, "%H:%M:%S").time()
                            except ValueError:
                                egress = None
                    if not ingress:
                        continue

                    candidate_start = datetime.combine(target_date, target_time)
                    existing_start = datetime.combine(target_date, ingress)
                    if target_end_time and egress:
                        candidate_end = datetime.combine(target_date, target_end_time)
                        existing_end = datetime.combine(target_date, egress)
                        has_conflict = (
                            candidate_start < existing_end + timedelta(hours=turnover_hours)
                            and candidate_end + timedelta(hours=turnover_hours) > existing_start
                        )
                    else:
                        diff_hours = abs((candidate_start - existing_start).total_seconds()) / 3600.0
                        has_conflict = diff_hours < turnover_hours

                    if has_conflict:
                        return {
                            "available": False,
                            "code": "slot_conflict",
                            "reason": "slot_conflict",
                            "message": "The caterer is already booked around this time. Please select another time.",
                            "settings": settings
                        }

        # 9. All Checks Passed
        return {
            "available": True,
            "code": "available",
            "reason": "available",
            "message": "This date and time is available for booking.",
            "settings": settings
        }
