from typing import Optional

from ..db import models


DEFAULT_COMMISSION_RATE_PERCENT = 10.0


def get_commission_rate_percent(config: Optional[models.WebsiteConfig]) -> float:
    if not config or config.commission_rate is None:
        return DEFAULT_COMMISSION_RATE_PERCENT
    return float(config.commission_rate)


def calculate_booking_commission(booking_amount: float, rate_percent: float) -> float:
    return max(float(booking_amount or 0.0), 0.0) * float(rate_percent) / 100.0