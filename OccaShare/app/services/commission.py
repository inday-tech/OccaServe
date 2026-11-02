from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from types import SimpleNamespace
from typing import Iterable, Optional

from ..db import models


DEFAULT_COMMISSION_RATE_PERCENT = 10.0
COMMISSION_LAUNCH_DATE = date(2026, 9, 10)


def is_pre_deployment_manual_booking(booking: models.Booking) -> bool:
    event_date = booking.event_date
    if isinstance(event_date, datetime):
        event_date = event_date.date()
    if not event_date or event_date >= COMMISSION_LAUNCH_DATE:
        return False

    source = (booking.booking_source or "").casefold()
    is_manual = (
        not booking.user_id
        or any(marker in source for marker in ("walk", "manual", "internal"))
        or bool((booking.custom_requirements or {}).get("is_walk_in"))
    )
    return is_manual


def get_commission_rate_percent(config: Optional[models.WebsiteConfig]) -> float:
    if not config or config.commission_rate is None:
        return DEFAULT_COMMISSION_RATE_PERCENT
    configured_rate = float(config.commission_rate)
    # WebsiteConfig has historically held both percent values (10) and a
    # fractional rate (0.10). Normalize the latter to the percent contract
    # used by calculate_booking_commission and the admin settings form.
    if 0 < configured_rate < 1:
        return configured_rate * 100.0
    return configured_rate


def calculate_booking_commission(booking_amount: float, rate_percent: float) -> float:
    amount = max(Decimal(str(booking_amount or 0.0)), Decimal("0"))
    rate = Decimal(str(rate_percent or 0.0))
    return float((amount * rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def reprice_open_commission_invoices(
    invoices: Iterable[models.BillingInvoice],
    rate_percent: float,
) -> set[int]:
    """Apply the current admin rate to unpaid booking invoices without submitted proof."""
    rate_percent = float(rate_percent)
    if not 0 <= rate_percent <= 100:
        raise ValueError("Commission rate must be between 0% and 100%.")

    impacted_caterer_ids = set()
    for invoice in invoices:
        if (
            invoice.booking_id is None
            or invoice.status not in ("pending", "overdue")
            or (invoice.payment_proof_url or "").strip()
            or not invoice.booking
            or is_pre_deployment_manual_booking(invoice.booking)
        ):
            continue

        booking_amount = (
            getattr(invoice.booking, "total_amount", None)
            or getattr(invoice.booking, "total_price", None)
            or 0.0
        )
        invoice.amount = calculate_booking_commission(booking_amount, rate_percent)
        invoice.commission_rate = rate_percent / 100.0
        if invoice.caterer_id is not None:
            impacted_caterer_ids.add(invoice.caterer_id)
    return impacted_caterer_ids


def build_commission_invoice_rows(
    invoices: Iterable[models.BillingInvoice],
) -> list[SimpleNamespace]:
    def statement_line_item(invoice):
        booking = getattr(invoice, "booking", None)
        booking_id = getattr(invoice, "booking_id", None)
        if not booking and booking_id is None:
            return None

        raw_booking_amount = (
            (getattr(booking, "total_amount", None) or getattr(booking, "total_price", None))
            if booking else None
        )
        booking_amount = float(raw_booking_amount) if raw_booking_amount is not None else None
        raw_rate = getattr(invoice, "commission_rate", None)
        rate_percent = float(raw_rate or 0.0)
        if 0 < rate_percent <= 1:
            rate_percent *= 100
        elif rate_percent <= 0 and booking_amount and booking_amount > 0:
            rate_percent = float(invoice.amount or 0.0) / booking_amount * 100

        customer = getattr(booking, "user", None) if booking else None
        customer_name = "Customer"
        if customer:
            customer_name = " ".join(
                part for part in (
                    getattr(customer, "first_name", None),
                    getattr(customer, "last_name", None),
                )
                if part
            ).strip() or customer_name
        customer_name = (
            customer_name if customer_name != "Customer"
            else (getattr(booking, "customer_name", None) if booking else None) or customer_name
        )

        event_date = getattr(booking, "event_date", None) if booking else None
        return {
            "booking_reference": (
                (getattr(booking, "booking_ref", None) if booking else None)
                or f"BK-{getattr(booking, 'id', booking_id):06d}"
            ),
            "event_name": (
                (
                    getattr(booking, "event_name", None)
                    or getattr(booking, "event_type", None)
                    or "Catering event"
                ) if booking else "Booking details unavailable"
            ),
            "customer_name": customer_name if booking else "Booking details unavailable",
            "event_date": event_date.strftime("%b %d, %Y") if event_date else "Not scheduled",
            "booking_amount": booking_amount,
            "commission_rate_percent": rate_percent if raw_rate is not None or booking_amount else None,
            "commission_amount": float(invoice.amount or 0.0),
            "status": str(getattr(invoice, "status", "pending") or "pending").replace("_", " ").title(),
            "booking_details_available": booking is not None,
        }

    booking_groups = {}
    settlement_groups = {}
    for invoice in invoices:
        booking = getattr(invoice, "booking", None)
        if booking and is_pre_deployment_manual_booking(booking):
            continue

        period_key = (invoice.billing_period or "General").strip().casefold()
        if invoice.booking_id is not None:
            booking_groups.setdefault(period_key, []).append(invoice)
        elif invoice.payment_proof_url:
            settlement_groups.setdefault(period_key, []).append(invoice)

    rows = []
    for period_key, period_invoices in booking_groups.items():
        period_invoices.sort(key=lambda invoice: invoice.id)
        open_invoices = [
            invoice for invoice in period_invoices
            if invoice.status in ("pending", "processing", "overdue")
        ]
        processing_proofs = [
            invoice.payment_proof_url
            for invoice in open_invoices
            if invoice.status == "processing" and invoice.payment_proof_url
        ]
        proof_url = None
        if processing_proofs:
            proof_url = processing_proofs[0]
        elif open_invoices and all(invoice.payment_proof_url for invoice in open_invoices):
            proof_url = next(invoice.payment_proof_url for invoice in open_invoices if invoice.payment_proof_url)
        elif not open_invoices:
            proof_url = next(
                (
                    invoice.payment_proof_url
                    for invoice in reversed(period_invoices)
                    if invoice.payment_proof_url
                ),
                None,
            )
            if not proof_url:
                proof_url = next(
                    (
                        invoice.payment_proof_url
                        for invoice in settlement_groups.get(period_key, [])
                        if invoice.payment_proof_url
                    ),
                    None,
                )

        statuses = {invoice.status for invoice in period_invoices}
        statement_invoices = open_invoices or period_invoices
        line_items = [
            line_item
            for invoice in statement_invoices
            if (line_item := statement_line_item(invoice)) is not None
        ]
        rows.append(SimpleNamespace(
            id=period_invoices[0].id,
            booking_id=None,
            billing_period=period_invoices[0].billing_period or "General",
            amount=sum(float(invoice.amount or 0.0) for invoice in (open_invoices or period_invoices)),
            due_date=min(
                (invoice.due_date for invoice in period_invoices if invoice.due_date),
                default=None,
            ),
            status="settled" if statuses and statuses.issubset({"paid", "settled"}) else "pending",
            payment_proof_url=proof_url,
            can_settle=not processing_proofs and any(
                invoice.status in ("pending", "overdue") and not invoice.payment_proof_url
                for invoice in period_invoices
            ),
            line_items=line_items,
            breakdown_note=(
                "Some booking records are unavailable. Their billed commission is included, "
                "but booking value, customer, and event details cannot be shown."
                if any(not item["booking_details_available"] for item in line_items)
                else None
            ),
        ))

    for period_key, period_invoices in settlement_groups.items():
        if period_key in booking_groups:
            continue
        period_invoices.sort(key=lambda invoice: invoice.id)
        rows.append(SimpleNamespace(
            id=period_invoices[0].id,
            booking_id=None,
            billing_period=period_invoices[0].billing_period or "General",
            amount=sum(float(invoice.amount or 0.0) for invoice in period_invoices),
            due_date=min(
                (invoice.due_date for invoice in period_invoices if invoice.due_date),
                default=None,
            ),
            status="settled" if all(invoice.status in ("paid", "settled") for invoice in period_invoices) else "pending",
            payment_proof_url=next(
                (
                    invoice.payment_proof_url
                    for invoice in reversed(period_invoices)
                    if invoice.payment_proof_url
                ),
                None,
            ),
            can_settle=False,
            line_items=[],
            breakdown_note=(
                "This is a legacy aggregate settlement record. Booking-level commission "
                "details were not stored for this billing period."
            ),
        ))

    return sorted(rows, key=lambda invoice: invoice.id, reverse=True)
