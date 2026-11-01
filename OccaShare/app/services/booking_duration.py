from datetime import date, datetime, time, timedelta


def expected_same_day_end_time(
    event_date: date,
    ingress_time: time,
    duration_hours: int,
) -> time | None:
    if not 1 <= duration_hours <= 23:
        return None

    end_datetime = datetime.combine(event_date, ingress_time) + timedelta(hours=duration_hours)
    if end_datetime.date() != event_date:
        return None
    return end_datetime.time()
