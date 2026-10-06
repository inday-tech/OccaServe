from datetime import date
from types import SimpleNamespace

from app.services.commission import build_commission_invoice_rows


def make_invoice(invoice_id, booking_id, amount, status, proof=None):
    return SimpleNamespace(
        id=invoice_id,
        booking_id=booking_id,
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
