from types import SimpleNamespace

from app.services.preparation_service import build_prep_summary


def test_ready_preparation_status_uses_event_catering_label():
    booking = SimpleNamespace(
        preparation_status="ready_for_delivery",
        status="ready_for_delivery",
        updated_at=None,
        created_at=None,
    )

    summary = build_prep_summary(booking)

    assert summary["label"] == "Preparation Complete"
    assert next(
        status["label"]
        for status in summary["statuses"]
        if status["key"] == "ready_for_delivery"
    ) == "Preparation Complete"
