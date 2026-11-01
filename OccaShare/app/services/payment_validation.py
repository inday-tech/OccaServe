import re
from typing import Optional


def normalize_ph_mobile_number(value: Optional[str], label: str) -> Optional[str]:
    raw_value = (value or "").strip()
    if not raw_value:
        return None
    if not re.fullmatch(r"[0-9+\s()-]+", raw_value):
        raise ValueError(f"{label} must be a valid Philippine mobile number.")

    digits = re.sub(r"\D", "", raw_value)
    if digits.startswith("63"):
        digits = digits[2:]
    if digits.startswith("0"):
        digits = digits[1:]
    if not re.fullmatch(r"9\d{9}", digits):
        raise ValueError(f"{label} must have 10 digits after +63.")
    return f"+63{digits}"


def validate_digit_number(
    value: Optional[str],
    label: str,
    minimum_digits: int,
    maximum_digits: int,
) -> Optional[str]:
    number = (value or "").strip()
    if not number:
        return None
    if not re.fullmatch(rf"\d{{{minimum_digits},{maximum_digits}}}", number):
        raise ValueError(f"{label} must contain {minimum_digits} to {maximum_digits} digits.")
    return number


def validate_card_number(value: Optional[str]) -> Optional[str]:
    number = (value or "").strip()
    if not number:
        return None
    if not re.fullmatch(r"(?:\d{4}|\d{12,19})", number):
        raise ValueError("Card number must be the last 4 digits or a full 12 to 19 digit number.")
    return number
