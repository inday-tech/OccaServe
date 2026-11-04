from fastapi import HTTPException


DEFAULT_TEXT_LIMIT = 300


def enforce_text_limit(value, field_label, *, existing_value=None, max_length=DEFAULT_TEXT_LIMIT):
    if value is None:
        return value
    text_value = str(value)
    if len(text_value) > max_length and text_value != existing_value:
        raise HTTPException(
            status_code=422,
            detail=f"{field_label} must be {max_length} characters or fewer.",
        )
    return value
