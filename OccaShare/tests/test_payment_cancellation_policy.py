from types import SimpleNamespace

from app.services.payment_service import PaymentService


def make_booking(payment_status, amount_paid=0, proof_url=None):
    return SimpleNamespace(
        total_price=100,
        total_amount=100,
        reservation_fee=None,
        quotation=None,
        payment_status=payment_status,
        payment_records=[],
        amount_paid=amount_paid,
        payment_proof_url=proof_url,
        balance_proof_url=None,
        status="confirmed",
    )


def test_verified_downpayment_requires_cancellation_review():
    booking = make_booking("deposit_paid", amount_paid=50)

    assert PaymentService.has_payment_requiring_cancellation_review(booking)


def test_payment_proof_under_review_requires_cancellation_review():
    booking = make_booking("proof_submitted", proof_url="/proof.png")

    assert PaymentService.has_payment_requiring_cancellation_review(booking)


def test_unpaid_booking_can_be_cancelled():
    booking = make_booking("pending")

    assert not PaymentService.has_payment_requiring_cancellation_review(booking)
