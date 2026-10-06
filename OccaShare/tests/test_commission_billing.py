from datetime import date
from types import SimpleNamespace

from app.services.commission import (
    build_commission_invoice_rows,
    is_pre_deployment_manual_booking,
)


def make_invoice(invoice_id, booking_id, amount, status, proof=None, booking=None):
    return SimpleNamespace(
        id=invoice_id,
        booking_id=booking_id,
        booking=booking,
        billing_period="September 2026",
        amount=amount,
        due_date=date(2026, 9, 30),
        status=status,
        payment_proof_url=proof,
    )


def test_commission_invoices_are_combined_by_period_and_status():
    rows = build_commission_invoice_rows([
        make_invoice(3, 21, 40, "settled"),
        make_invoice(4, 22, 30, "settled"),
        make_invoice(5, None, 70, "paid", "/proof.png"),
    ])

    assert len(rows) == 1
    assert rows[0].amount == 70
    assert rows[0].status == "settled"
    assert rows[0].payment_proof_url == "/proof.png"
    assert rows[0].can_settle is False


def test_commission_statement_is_pending_and_settleable_before_payment():
    rows = build_commission_invoice_rows([
        make_invoice(3, 21, 40, "pending"),
        make_invoice(4, 22, 30, "pending"),
    ])

    assert len(rows) == 1
    assert rows[0].amount == 70
    assert rows[0].status == "pending"
    assert rows[0].can_settle is True


def test_commission_invoices_stay_separate_between_billing_periods():
    september = make_invoice(3, 21, 40, "pending")
    october = make_invoice(4, 22, 30, "settled")
    october.billing_period = "October 2026"

    rows = build_commission_invoice_rows([september, october])

    assert len(rows) == 2
    assert {row.billing_period for row in rows} == {"September 2026", "October 2026"}


def test_commission_statement_shows_pending_during_verification():
    rows = build_commission_invoice_rows([
        make_invoice(3, 21, 70, "processing", "/proof.png"),
        make_invoice(4, None, 70, "pending", "/proof.png"),
    ])

    assert len(rows) == 1
    assert rows[0].status == "pending"
    assert rows[0].payment_proof_url == "/proof.png"
    assert rows[0].can_settle is False


def test_new_due_is_not_resubmitted_while_period_payment_is_under_review():
    rows = build_commission_invoice_rows([
        make_invoice(3, 21, 70, "processing", "/proof.png"),
        make_invoice(4, 22, 30, "pending"),
    ])

    assert len(rows) == 1
    assert rows[0].amount == 100
    assert rows[0].payment_proof_url == "/proof.png"
    assert rows[0].can_settle is False


def test_pre_deployment_manual_booking_is_exempt_from_commission():
    booking = SimpleNamespace(
        event_date=date(2026, 8, 31),
        user_id=45,
        booking_source="WALK_IN",
        custom_requirements={"is_walk_in": True},
    )
    cutoff_day_booking = SimpleNamespace(
        event_date=date(2026, 9, 10),
        user_id=45,
        booking_source="WALK_IN",
        custom_requirements={"is_walk_in": True},
    )
    online_booking = SimpleNamespace(
        event_date=date(2026, 8, 31),
        user_id=45,
        booking_source="OccaServe",
        custom_requirements={},
    )

    assert is_pre_deployment_manual_booking(booking) is True
    assert is_pre_deployment_manual_booking(cutoff_day_booking) is False
    assert is_pre_deployment_manual_booking(online_booking) is False


def test_pre_deployment_manual_commission_is_not_in_caterer_statement():
    legacy_manual = SimpleNamespace(
        event_date=date(2026, 8, 31),
        user_id=45,
        booking_source="WALK_IN",
        custom_requirements={"is_walk_in": True},
    )
    online_booking = SimpleNamespace(
        event_date=date(2026, 8, 31),
        user_id=46,
        booking_source="OccaServe",
        custom_requirements={},
    )

    rows = build_commission_invoice_rows([
        make_invoice(3, 21, 40, "pending", booking=legacy_manual),
        make_invoice(4, 22, 30, "pending", booking=online_booking),
    ])

    assert len(rows) == 1
    assert rows[0].amount == 30
    assert rows[0].can_settle is True
