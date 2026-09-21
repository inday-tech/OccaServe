import os
import sys
from datetime import date, time, timedelta
import pytest
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.availability_service import AvailabilityService
from app.db import models

class MockCaterer:
    def __init__(self, caterer_id=1, scheduling_rules=None, booking_lead_time=3, max_bookings_per_day=3):
        self.id = caterer_id
        self.scheduling_rules = scheduling_rules or {}
        self.booking_lead_time = booking_lead_time
        self.max_bookings_per_day = max_bookings_per_day

def test_get_caterer_availability_settings_defaults():
    mock_caterer = MockCaterer(caterer_id=10, scheduling_rules={}, booking_lead_time=4, max_bookings_per_day=5)

    settings = AvailabilityService.get_caterer_availability_settings(mock_caterer)
    assert settings["availability_status"] == "Available"
    assert len(settings["operating_days"]) == 7
    assert settings["open_time"] == "08:00"
    assert settings["close_time"] == "20:00"
    assert settings["booking_lead_time"] == 4
    assert settings["max_events_per_day"] == 5

def test_status_temporarily_unavailable():
    mock_db = MagicMock()
    rules = {
        "event_availability": {
            "status": "temporarily_unavailable"
        }
    }
    mock_caterer = MockCaterer(scheduling_rules=rules)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_caterer
    mock_db.query.return_value.filter.return_value.all.return_value = []

    res = AvailabilityService.check_caterer_availability(
        mock_db, 1, date.today() + timedelta(days=10), time(12, 0)
    )
    assert res["available"] is False
    assert res["reason"] == "temporarily_unavailable"
    assert "temporarily unavailable" in res["message"]

def test_operating_days_restriction():
    mock_db = MagicMock()
    rules = {
        "event_availability": {
            "status": "available",
            "operating_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        }
    }
    mock_caterer = MockCaterer(scheduling_rules=rules)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_caterer
    mock_db.query.return_value.filter.return_value.all.return_value = []

    # Find next Sunday
    target = date.today() + timedelta(days=10)
    while target.strftime("%A") != "Sunday":
        target += timedelta(days=1)

    res = AvailabilityService.check_caterer_availability(mock_db, 1, target, time(12, 0))
    assert res["available"] is False
    assert res["reason"] == "unavailable_day"
    assert "does not accept bookings on this day" in res["message"]

def test_minimum_lead_time_restriction():
    mock_db = MagicMock()
    rules = {
        "event_availability": {
            "status": "available",
            "lead_time_days": 5
        }
    }
    mock_caterer = MockCaterer(scheduling_rules=rules)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_caterer
    mock_db.query.return_value.filter.return_value.all.return_value = []

    # Select tomorrow (only 1 day away, lead time requires 5)
    target = date.today() + timedelta(days=1)
    res = AvailabilityService.check_caterer_availability(mock_db, 1, target, time(12, 0))
    assert res["available"] is False
    assert res["reason"] == "too_soon"
    assert "requires bookings at least 5 days" in res["message"]

def test_maximum_advance_restriction():
    mock_db = MagicMock()
    rules = {
        "event_availability": {
            "status": "available",
            "lead_time_days": 1,
            "max_advance_val": 3,
            "max_advance_unit": "months"
        }
    }
    mock_caterer = MockCaterer(scheduling_rules=rules)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_caterer
    mock_db.query.return_value.filter.return_value.all.return_value = []

    # 180 days away is ~6 months, exceeds 3 months
    target = date.today() + timedelta(days=180)
    res = AvailabilityService.check_caterer_availability(mock_db, 1, target, time(12, 0))
    assert res["available"] is False
    assert res["reason"] == "too_far_in_advance"
    assert "only accepts bookings up to 3 months" in res["message"]

def test_blocked_date_restriction():
    mock_db = MagicMock()
    blocked_target = date.today() + timedelta(days=15)
    rules = {
        "event_availability": {
            "status": "available",
            "lead_time_days": 1,
            "blocked_dates": [{"date": blocked_target.isoformat(), "reason": "Family holiday"}]
        }
    }
    mock_caterer = MockCaterer(scheduling_rules=rules)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_caterer
    mock_db.query.return_value.filter.return_value.all.return_value = []

    res = AvailabilityService.check_caterer_availability(mock_db, 1, blocked_target, time(12, 0))
    assert res["available"] is False
    assert res["reason"] == "blocked_date"
    assert "unavailable for this caterer" in res["message"]

def test_operating_hours_restriction():
    mock_db = MagicMock()
    rules = {
        "event_availability": {
            "status": "available",
            "lead_time_days": 1,
            "opening_time": "09:00",
            "closing_time": "20:00"
        }
    }
    mock_caterer = MockCaterer(scheduling_rules=rules)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_caterer
    mock_db.query.return_value.filter.return_value.all.return_value = []

    target = date.today() + timedelta(days=10)
    
    # 7:30 AM is before 9:00 AM
    res_early = AvailabilityService.check_caterer_availability(mock_db, 1, target, time(7, 30))
    assert res_early["available"] is False
    assert res_early["reason"] == "outside_hours"
    assert "outside the caterer’s available hours" in res_early["message"]

    # 21:30 is after 20:00
    res_late = AvailabilityService.check_caterer_availability(mock_db, 1, target, time(21, 30))
    assert res_late["available"] is False
    assert res_late["reason"] == "outside_hours"

def test_daily_event_capacity_limit():
    mock_db = MagicMock()
    rules = {
        "event_availability": {
            "status": "available",
            "lead_time_days": 1,
            "max_events_per_day": 2
        }
    }
    mock_caterer = MockCaterer(scheduling_rules=rules, max_bookings_per_day=2)

    # First query returns caterer profile
    # Second query (Availability table) returns empty list
    # Third query (Booking count) returns 2 (max reached)
    def query_side_effect(model):
        m = MagicMock()
        if model == models.CatererProfile:
            m.filter.return_value.first.return_value = mock_caterer
        elif model == models.Availability:
            m.filter.return_value.all.return_value = []
        elif model == models.Booking:
            m.filter.return_value.filter.return_value.count.return_value = 2
            m.filter.return_value.count.return_value = 2
            m.filter.return_value.all.return_value = []
        return m

    mock_db.query.side_effect = query_side_effect

    target = date.today() + timedelta(days=10)
    res = AvailabilityService.check_caterer_availability(mock_db, 1, target, time(12, 0))
    assert res["available"] is False
    assert res["reason"] == "daily_capacity_reached"
    assert "reached the maximum number of events" in res["message"]

def test_fully_available_slot():
    mock_db = MagicMock()
    rules = {
        "event_availability": {
            "status": "available",
            "operating_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            "opening_time": "08:00",
            "closing_time": "22:00",
            "lead_time_days": 3,
            "max_advance_val": 1,
            "max_advance_unit": "years",
            "max_events_per_day": 5,
            "blocked_dates": []
        }
    }
    mock_caterer = MockCaterer(scheduling_rules=rules)

    def query_side_effect(model):
        m = MagicMock()
        if model == models.CatererProfile:
            m.filter.return_value.first.return_value = mock_caterer
        elif model == models.Availability:
            m.filter.return_value.all.return_value = []
        elif model == models.Booking:
            m.filter.return_value.filter.return_value.count.return_value = 0
            m.filter.return_value.count.return_value = 0
            m.filter.return_value.all.return_value = []
        return m

    mock_db.query.side_effect = query_side_effect

    target = date.today() + timedelta(days=14)
    res = AvailabilityService.check_caterer_availability(mock_db, 1, target, time(14, 0))
    assert res["available"] is True
    assert res["reason"] == "available"
    assert "This date and time is available for booking." in res["message"]
