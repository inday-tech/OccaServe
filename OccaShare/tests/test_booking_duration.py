from datetime import date, time

from app.services.booking_duration import expected_same_day_end_time


def test_expected_egress_uses_exact_package_duration():
    assert expected_same_day_end_time(date(2026, 6, 15), time(10, 30), 4) == time(14, 30)


def test_expected_egress_rejects_duration_that_crosses_midnight():
    assert expected_same_day_end_time(date(2026, 6, 15), time(22, 0), 4) is None


def test_expected_egress_rejects_invalid_duration():
    assert expected_same_day_end_time(date(2026, 6, 15), time(10, 0), 0) is None
    assert expected_same_day_end_time(date(2026, 6, 15), time(10, 0), 24) is None
