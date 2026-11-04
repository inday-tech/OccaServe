import pytest
from fastapi import HTTPException

from app.core.text_limits import enforce_text_limit


def test_default_limit_accepts_300_characters():
    value = "x" * 300
    assert enforce_text_limit(value, "Notes") == value


def test_default_limit_rejects_301_characters():
    with pytest.raises(HTTPException) as exc_info:
        enforce_text_limit("x" * 301, "Notes")

    assert exc_info.value.status_code == 422
    assert "300 characters or fewer" in exc_info.value.detail


def test_limit_counts_unicode_codepoints():
    value = "😊" * 300
    assert enforce_text_limit(value, "Comment") == value
    with pytest.raises(HTTPException):
        enforce_text_limit(value + "😊", "Comment")


def test_unchanged_legacy_value_over_limit_is_preserved():
    legacy_value = "legacy " * 60
    assert len(legacy_value) > 300
    assert enforce_text_limit(legacy_value, "Description", existing_value=legacy_value) == legacy_value


def test_changed_legacy_value_over_limit_is_rejected():
    legacy_value = "legacy " * 60
    with pytest.raises(HTTPException):
        enforce_text_limit(legacy_value + "new", "Description", existing_value=legacy_value)


def test_custom_long_form_limit():
    value = "x" * 1000
    assert enforce_text_limit(value, "Business description", max_length=1000) == value
    with pytest.raises(HTTPException):
        enforce_text_limit(value + "x", "Business description", max_length=1000)
