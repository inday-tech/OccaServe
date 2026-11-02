from datetime import date
from types import SimpleNamespace

from app.services.commission import (
    build_commission_invoice_rows,
    calculate_booking_commission,
    get_commission_rate_percent,
    is_pre_deployment_manual_booking,
    reprice_open_commission_invoices,
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


def test_commission_statement_explains_each_booking_charge():
    booking = SimpleNamespace(
        id=21,
        booking_ref="REP-BK-021",
        event_name="Garcia Wedding",
        event_type="Wedding",
        event_date=date(2026, 9, 18),
        total_amount=750.0,
        total_price=750.0,
        user=SimpleNamespace(first_name="Ana", last_name="Garcia"),
    )
    invoice = make_invoice(3, 21, 75.0, "pending", booking=booking)
    invoice.commission_rate = 0.10

    row = build_commission_invoice_rows([invoice])[0]

    assert row.amount == 75.0
    assert row.line_items == [{
        "booking_reference": "REP-BK-021",
        "event_name": "Garcia Wedding",
        "customer_name": "Ana Garcia",
        "event_date": "Sep 18, 2026",
        "booking_amount": 750.0,
        "commission_rate_percent": 10.0,
        "commission_amount": 75.0,
        "status": "Pending",
        "booking_details_available": True,
    }]
    assert row.breakdown_note is None


def test_commission_amount_uses_admin_rate_and_rounds_to_cents():
    assert calculate_booking_commission(1234.56, 7.5) == 92.59
    assert calculate_booking_commission(1234.56, 0) == 0


def test_commission_rate_normalizes_legacy_fraction_without_misreading_one_percent():
    assert get_commission_rate_percent(SimpleNamespace(commission_rate=0.1)) == 10.0
    assert get_commission_rate_percent(SimpleNamespace(commission_rate=1.0)) == 1.0
    assert get_commission_rate_percent(SimpleNamespace(commission_rate=10.0)) == 10.0


def test_admin_rate_reprices_only_unpaid_booking_invoices_without_proof():
    booking = SimpleNamespace(
        id=21,
        event_date=date(2026, 9, 18),
        booking_source="OccaServe",
        user_id=12,
        custom_requirements={},
        total_amount=1234.56,
        total_price=1234.56,
    )
    pending = make_invoice(3, 21, 100.0, "pending", booking=booking)
    pending.caterer_id = 5
    pending.commission_rate = 0.1
    paid = make_invoice(4, 22, 100.0, "paid", booking=booking)
    paid.caterer_id = 5
    paid.commission_rate = 0.1
    processing = make_invoice(5, 23, 100.0, "processing", "/receipt.png", booking=booking)
    processing.caterer_id = 5
    processing.commission_rate = 0.1
    legacy_manual_booking = SimpleNamespace(
        id=24,
        event_date=date(2026, 8, 31),
        booking_source="WALK_IN",
        user_id=12,
        custom_requirements={"is_walk_in": True},
        total_amount=1000.0,
    )
    manual = make_invoice(6, 24, 100.0, "pending", booking=legacy_manual_booking)
    manual.caterer_id = 6
    manual.commission_rate = 0.1

    impacted = reprice_open_commission_invoices(
        [pending, paid, processing, manual],
        7.5,
    )

    assert impacted == {5}
    assert pending.amount == 92.59
    assert pending.commission_rate == 0.075
    assert paid.amount == 100.0
    assert processing.amount == 100.0
    assert manual.amount == 100.0


def test_commission_statement_keeps_billed_amount_when_booking_record_is_missing():
    invoice = make_invoice(8, 42, 65.0, "pending")
    invoice.commission_rate = 0.1

    row = build_commission_invoice_rows([invoice])[0]

    assert row.amount == 65.0
    assert row.line_items[0]["booking_reference"] == "BK-000042"
    assert row.line_items[0]["booking_amount"] is None
    assert row.line_items[0]["commission_amount"] == 65.0
    assert row.line_items[0]["booking_details_available"] is False
    assert "booking records are unavailable" in row.breakdown_note.lower()


def test_legacy_aggregate_statement_discloses_missing_booking_breakdown():
    row = build_commission_invoice_rows([
        make_invoice(7, None, 150.0, "pending", "/settlement-proof.png")
    ])[0]

    assert row.amount == 150.0
    assert row.line_items == []
    assert "legacy aggregate" in row.breakdown_note.lower()


def test_statement_breakdown_matches_only_the_open_commission_due():
    settled_booking = SimpleNamespace(
        id=21,
        booking_ref="REP-BK-021",
        event_name="Completed Event",
        event_date=date(2026, 9, 18),
        total_amount=1000.0,
        user=SimpleNamespace(first_name="A", last_name="Customer"),
    )
    open_booking = SimpleNamespace(
        id=22,
        booking_ref="REP-BK-022",
        event_name="Upcoming Event",
        event_date=date(2026, 9, 25),
        total_amount=2000.0,
        user=SimpleNamespace(first_name="B", last_name="Customer"),
    )
    settled = make_invoice(3, 21, 100.0, "settled", booking=settled_booking)
    open_invoice = make_invoice(4, 22, 200.0, "pending", booking=open_booking)
    settled.commission_rate = 0.1
    open_invoice.commission_rate = 0.1

    row = build_commission_invoice_rows([settled, open_invoice])[0]

    assert row.amount == 200.0
    assert [item["booking_reference"] for item in row.line_items] == ["REP-BK-022"]
    assert sum(item["commission_amount"] for item in row.line_items) == row.amount


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
