import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional


MAX_STARTING_PRICE = Decimal("99999999.99")
MAX_EXPERIENCE_YEARS = 42


def parse_starting_price(value: Optional[str]) -> Decimal:
    raw_value = (value or "0").replace(",", "").strip()
    if not re.fullmatch(r"\d{1,8}(?:\.\d{1,2})?", raw_value):
        raise ValueError("Starting price must be a non-negative amount with up to 2 decimal places.")
    try:
        amount = Decimal(raw_value)
    except InvalidOperation as exc:
        raise ValueError("Enter a valid starting price.") from exc
    if not amount.is_finite() or amount > MAX_STARTING_PRICE:
        raise ValueError("Starting price cannot exceed ₱99,999,999.99.")
    return amount


def validate_experience_years(value: Optional[str], dob: Optional[date], today: date) -> int:
    raw_value = (value or "0").strip()
    if not re.fullmatch(r"\d{1,2}", raw_value):
        raise ValueError("Years of experience must be a whole number.")
    years = int(raw_value)
    maximum = MAX_EXPERIENCE_YEARS
    if dob:
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        maximum = min(maximum, max(0, age - 18))
    if years > maximum:
        raise ValueError(f"Years of experience cannot exceed {maximum} based on your age.")
    return years
