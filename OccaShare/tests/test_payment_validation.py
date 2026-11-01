import pytest

from app.services.payment_validation import (
    normalize_ph_mobile_number,
    validate_card_number,
    validate_digit_number,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("9123456789", "+639123456789"),
        ("09123456789", "+639123456789"),
        ("+63 912-345-6789", "+639123456789"),
    ],
)
def test_normalize_ph_mobile_number(value, expected):
    assert normalize_ph_mobile_number(value, "GCash number") == expected


@pytest.mark.parametrize("value", ["912345678", "8123456789", "abc9123456789", "+639123"])
def test_reject_invalid_ph_mobile_number(value):
    with pytest.raises(ValueError):
        normalize_ph_mobile_number(value, "Maya number")


def test_validate_digit_number_accepts_optional_blank_and_valid_range():
    assert validate_digit_number(None, "Bank account number", 4, 20) is None
    assert validate_digit_number("123456", "Bank account number", 4, 20) == "123456"


@pytest.mark.parametrize("value", ["123", "1234x", "+1234", "1" * 21])
def test_validate_digit_number_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        validate_digit_number(value, "Bank account number", 4, 20)


@pytest.mark.parametrize("value", ["1234", "123456789012", "1" * 19])
def test_validate_card_number_accepts_last_four_or_full_card(value):
    assert validate_card_number(value) == value


@pytest.mark.parametrize("value", ["123", "1" * 11, "1" * 20, "abcd1234"])
def test_validate_card_number_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        validate_card_number(value)
