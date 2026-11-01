from datetime import date
from decimal import Decimal

import pytest

from app.services.profile_validation import parse_starting_price, validate_experience_years


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0", Decimal("0")),
        ("1,250.50", Decimal("1250.50")),
        ("99999999.99", Decimal("99999999.99")),
    ],
)
def test_parse_starting_price_accepts_valid_amounts(value, expected):
    assert parse_starting_price(value) == expected


@pytest.mark.parametrize(
    "value",
    ["-1", "100000000", "1.999", "123456789", "12abc", "1e3"],
)
def test_parse_starting_price_rejects_invalid_amounts(value):
    with pytest.raises(ValueError):
        parse_starting_price(value)


def test_validate_experience_years_uses_age_and_global_maximum():
    today = date(2026, 6, 15)
    assert validate_experience_years("42", date(1966, 6, 15), today) == 42
    assert validate_experience_years("10", date(1998, 6, 15), today) == 10


@pytest.mark.parametrize(
    ("value", "dob"),
    [
        ("43", date(1980, 6, 15)),
        ("9", date(2000, 6, 15)),
        ("1.5", date(1980, 6, 15)),
        ("100", date(1980, 6, 15)),
        ("-1", date(1980, 6, 15)),
    ],
)
def test_validate_experience_years_rejects_invalid_or_impossible_values(value, dob):
    with pytest.raises(ValueError):
        validate_experience_years(value, dob, date(2026, 6, 15))
