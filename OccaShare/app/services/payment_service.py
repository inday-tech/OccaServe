"""Payment Service — single source of truth for booking payment state.

All customer and caterer UIs must derive paid / pending / balance from
`get_payment_summary()`, not from manually maintained amount fields alone.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from ..db import models

# Statuses that mean a customer submission is awaiting caterer action
UNDER_REVIEW_STATUSES = {
    "proof_submitted",
    "balance_proof_submitted",
    "cash_payment_requested",
    "cash_balance_requested",
    "pending_verification",
}

# Statuses that mean at least a deposit is verified
VERIFIED_STATUSES = {
    "deposit_paid",
    "paid",
    "fully_paid",
    "partially_paid",
    "confirmed",
}

REJECTED_STATUSES = {
    "reupload_requested",
    "balance_reupload_requested",
}

INITIAL_PAYMENT_TYPES = {"deposit", "full", "downpayment"}
BALANCE_PAYMENT_TYPES = {"balance", "installment", "final", "balance_payment"}


class PaymentService:
    """Centralised payment helper for OccaServe bookings."""

    @staticmethod
    def required_deposit(booking: models.Booking) -> float:
        """Backend-calculated required deposit (never trust the frontend)."""
        total = float(booking.total_price or booking.total_amount or 0.0)
        if total <= 0:
            return 0.0

        if booking.reservation_fee and float(booking.reservation_fee) > 0:
            fee = float(booking.reservation_fee)
            # reservation_fee sometimes holds full amount for 100% plans
            if fee <= total:
                return round(fee, 2)

        dp_percent = 50.0
        if booking.quotation and getattr(booking.quotation, "downpayment_percent", None):
            try:
                dp_percent = float(booking.quotation.downpayment_percent)
            except (TypeError, ValueError):
                dp_percent = 50.0

        return round(total * (dp_percent / 100.0), 2)

    @staticmethod
    def _normalize_type(value: Optional[str]) -> str:
        return str(value or "").strip().lower()

    @staticmethod
    def _normalize_by(value: Optional[str]) -> str:
        return str(value or "").strip().lower()

    @staticmethod
    def is_under_review(booking: models.Booking) -> bool:
        ps = (booking.payment_status or "").lower()
        if ps in UNDER_REVIEW_STATUSES:
            return True
        # Heal drifted rows: proof exists, booking still early, nothing verified yet
        if ps in REJECTED_STATUSES:
            return False
        has_proof = bool(booking.payment_proof_url or booking.balance_proof_url)
        early = (booking.status or "").lower() in {
            "pending", "awaiting_payment", "pending_payment", "pending_review"
        }
        paid = float(booking.amount_paid or 0.0)
        if has_proof and early and paid <= 0 and ps not in VERIFIED_STATUSES:
            return True
        # Customer payment records waiting without a verified amount
        for rec in (booking.payment_records or []):
            if PaymentService._normalize_by(rec.recorded_by) == "customer":
                if paid <= 0 and early and ps not in VERIFIED_STATUSES:
                    return True
        return False

    @staticmethod
    def display_payment_label(booking: models.Booking, summary: Optional[dict] = None) -> str:
        summary = summary or PaymentService.get_payment_summary(booking)
        ps = (booking.payment_status or "").lower()
        if ps in REJECTED_STATUSES:
            return "Re-upload Required"
        if summary.get("is_under_review"):
            if ps in {"cash_payment_requested", "cash_balance_requested"}:
                return "Awaiting Cash Confirmation"
            return "Under Review"
        if summary["remaining_balance"] <= 0 and summary["total_amount"] > 0:
            return "Fully Paid"
        if summary["verified_paid"] > 0:
            return "Partially Paid"
        return "Unpaid"

    @staticmethod
    def display_booking_action_label(booking: models.Booking, summary: Optional[dict] = None) -> str:
        """Caterer table status/action label."""
        summary = summary or PaymentService.get_payment_summary(booking)
        ps = (booking.payment_status or "").lower()
        st = (booking.status or "").lower()

        if ps in REJECTED_STATUSES:
            return "Re-upload"
        if summary.get("is_under_review"):
            if ps in {"balance_proof_submitted", "cash_balance_requested"}:
                return "Verify Balance"
            if ps in {"cash_payment_requested"}:
                return "Confirm Cash"
            return "Verify Payment"
        if st in {"awaiting_payment", "pending_payment"}:
            return "Awaiting Pay"
        if st == "pending":
            return "Pending Pay"
        return (st or "unknown").replace("_", " ").title()

    @staticmethod
    def needs_caterer_verification(booking: models.Booking, summary: Optional[dict] = None) -> bool:
        summary = summary or PaymentService.get_payment_summary(booking)
        return bool(summary.get("is_under_review"))

    @staticmethod
    def sync_review_status(booking: models.Booking, db: Optional[Session] = None) -> bool:
        """Repair drifted payment_status when proof/records exist but status is wrong.

        Returns True if a repair was applied.
        """
        if not booking:
            return False
        ps = (booking.payment_status or "").lower()
        if ps in UNDER_REVIEW_STATUSES | VERIFIED_STATUSES | REJECTED_STATUSES:
            return False
        if float(booking.amount_paid or 0) > 0:
            return False

        early = (booking.status or "").lower() in {
            "pending", "awaiting_payment", "pending_payment", "pending_review"
        }
        if not early:
            return False

        has_balance_proof = bool(booking.balance_proof_url)
        has_initial_proof = bool(booking.payment_proof_url)
        has_customer_record = any(
            PaymentService._normalize_by(r.recorded_by) == "customer"
            for r in (booking.payment_records or [])
        )

        repaired = False
        if has_balance_proof:
            booking.payment_status = "balance_proof_submitted"
            repaired = True
        elif has_initial_proof or has_customer_record:
            if (booking.payment_method or "").lower() == "cash" and not has_initial_proof:
                booking.payment_status = "cash_payment_requested"
            else:
                booking.payment_status = "proof_submitted"
            if (booking.status or "").lower() in {"awaiting_payment", "pending_payment"}:
                booking.status = "pending"
            repaired = True

        if repaired and db is not None:
            db.add(booking)
            db.flush()
        return repaired

    @staticmethod
    def update_payment_status(booking: models.Booking, db: Session) -> None:
        """Recalculate payment_status from VERIFIED records only.

        Never overwrites an active under-review or rejected status.
        Never treats unverified customer submissions as paid.
        """
        if not booking:
            return

        ps = (booking.payment_status or "").lower()
        if ps in UNDER_REVIEW_STATUSES | REJECTED_STATUSES:
            return

        summary = PaymentService.get_payment_summary(booking)
        verified = summary["verified_paid"]
        total = summary["total_amount"]
        deposit = PaymentService.required_deposit(booking)

        if verified <= 0:
            new_status = "pending" if ps not in VERIFIED_STATUSES else ps
            # Keep pending for unpaid; do not force "unpaid" over wizard defaults
            if ps in {"", "unpaid", "pending", "no_payment"}:
                new_status = "pending"
            else:
                return
        elif total > 0 and verified >= total:
            new_status = "paid"
        elif deposit > 0 and verified >= deposit:
            new_status = "deposit_paid"
        else:
            new_status = "partially_paid"

        booking.amount_paid = verified
        if booking.payment_status != new_status:
            booking.payment_status = new_status
            db.add(booking)
            db.flush()

    @staticmethod
    def get_payment_summary(booking: models.Booking) -> dict:
        """Unified payment summary derived from payment records + booking flags."""
        empty = {
            "total_amount": 0.0,
            "verified_paid": 0.0,
            "pending_review": 0.0,
            "remaining_balance": 0.0,
            "remaining_after_verification": 0.0,
            "required_deposit": 0.0,
            "payment_status": "unpaid",
            "computed_payment_status": "unpaid",
            "is_under_review": False,
            "needs_verification": False,
            "can_start_preparation": False,
        }
        if not booking:
            return empty

        total_amount = float(booking.total_price or booking.total_amount or 0.0)
        payment_status = (booking.payment_status or "pending").lower()
        records = booking.payment_records or []
        required_deposit = PaymentService.required_deposit(booking)

        is_initial_under_review = payment_status in {
            "proof_submitted", "cash_payment_requested", "pending_verification"
        }
        is_balance_under_review = payment_status in {
            "balance_proof_submitted", "cash_balance_requested"
        }

        # Heal detection when status drifted but proofs/records remain
        drifted_under_review = False
        if payment_status not in UNDER_REVIEW_STATUSES | VERIFIED_STATUSES | REJECTED_STATUSES:
            if PaymentService.is_under_review(booking):
                drifted_under_review = True
                if booking.balance_proof_url:
                    is_balance_under_review = True
                else:
                    is_initial_under_review = True

        verified_paid = 0.0
        pending_review = 0.0

        for rec in records:
            try:
                amt = float(rec.amount or 0.0)
            except (TypeError, ValueError):
                amt = 0.0
            if amt <= 0:
                continue

            rec_by = PaymentService._normalize_by(rec.recorded_by)
            rec_type = PaymentService._normalize_type(rec.payment_type)

            if rec_by == "customer":
                if payment_status in REJECTED_STATUSES:
                    continue
                if is_initial_under_review and (
                    rec_type in INITIAL_PAYMENT_TYPES or rec_type == ""
                ):
                    pending_review += amt
                elif is_balance_under_review and rec_type in BALANCE_PAYMENT_TYPES:
                    pending_review += amt
                elif is_balance_under_review and rec_type in INITIAL_PAYMENT_TYPES:
                    # Prior deposit already accepted
                    verified_paid += amt
                elif payment_status in VERIFIED_STATUSES:
                    verified_paid += amt
                elif is_initial_under_review:
                    pending_review += amt
                else:
                    # Ambiguous: prefer pending when early + unpaid
                    early = (booking.status or "").lower() in {
                        "pending", "awaiting_payment", "pending_payment"
                    }
                    if early and float(booking.amount_paid or 0) <= 0:
                        pending_review += amt
                    else:
                        verified_paid += amt
            else:
                # Caterer or System (Paymongo) — counted as verified
                verified_paid += amt

        legacy_paid = float(booking.amount_paid or 0.0)
        if payment_status in VERIFIED_STATUSES:
            verified_paid = max(verified_paid, legacy_paid)

        # Fallbacks when no payment records exist yet
        if len(records) == 0:
            if is_initial_under_review or (
                drifted_under_review and booking.payment_proof_url
            ):
                pending_review = max(pending_review, required_deposit or (total_amount * 0.5))
            elif is_balance_under_review or (
                drifted_under_review and booking.balance_proof_url
            ):
                pending_review = max(pending_review, max(0.0, total_amount - verified_paid))
            elif payment_status in {"paid", "fully_paid"}:
                verified_paid = max(verified_paid, total_amount)
            elif payment_status in {"deposit_paid", "partially_paid"}:
                verified_paid = max(verified_paid, required_deposit or (total_amount * 0.5))

        if total_amount > 0:
            verified_paid = min(verified_paid, total_amount)
            pending_review = min(pending_review, total_amount)

        remaining_balance = max(0.0, total_amount - verified_paid)
        remaining_after_verification = max(0.0, remaining_balance - pending_review)
        is_under_review = bool(
            is_initial_under_review or is_balance_under_review or pending_review > 0
        )

        if total_amount > 0 and verified_paid >= total_amount:
            computed = "fully_paid"
        elif is_under_review:
            computed = "under_review"
        elif verified_paid > 0:
            computed = "partially_paid"
        else:
            computed = "unpaid"

        can_start = (
            verified_paid >= required_deposit > 0
            or (total_amount > 0 and verified_paid >= total_amount)
        ) and payment_status in VERIFIED_STATUSES | {"deposit_paid", "paid", "fully_paid", "partially_paid"}

        # Also allow preparation when booking already confirmed with verified funds
        if (booking.status or "").lower() == "confirmed" and verified_paid >= max(required_deposit, 0):
            can_start = True

        is_fully_paid = bool(total_amount > 0 and remaining_balance <= 0.009)

        return {
            "total_amount": round(total_amount, 2),
            "verified_paid": round(verified_paid, 2),
            "pending_review": round(pending_review, 2),
            "remaining_balance": round(remaining_balance, 2),
            "remaining_after_verification": round(remaining_after_verification, 2),
            "required_deposit": round(required_deposit, 2),
            "payment_status": booking.payment_status or "pending",
            "computed_payment_status": computed,
            "is_under_review": is_under_review,
            "needs_verification": is_under_review,
            "can_start_preparation": can_start,
            "is_fully_paid": is_fully_paid,
            "can_mark_completed": is_fully_paid and not is_under_review,
        }

    @staticmethod
    def is_fully_paid(booking: models.Booking, summary: Optional[dict] = None) -> bool:
        """True only when verified paid covers the full booking total (no remaining balance)."""
        summary = summary or PaymentService.get_payment_summary(booking)
        return bool(summary.get("is_fully_paid"))

    @staticmethod
    def assert_can_mark_completed(booking: models.Booking) -> dict:
        """Raise-ready check: booking must be fully paid before Mark Completed."""
        summary = PaymentService.get_payment_summary(booking)
        if summary.get("is_under_review"):
            return {
                "ok": False,
                "message": "Cannot complete booking: a payment is still Under Review. Verify it first.",
                "summary": summary,
            }
        if not summary.get("is_fully_paid"):
            remaining = summary.get("remaining_balance", 0)
            return {
                "ok": False,
                "message": (
                    f"Cannot complete booking: remaining balance of "
                    f"₱{remaining:,.2f} must be settled and verified first."
                ),
                "summary": summary,
            }
        return {"ok": True, "message": "", "summary": summary}
