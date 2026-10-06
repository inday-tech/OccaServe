from datetime import date, datetime
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
    return float(config.commission_rate)


def calculate_booking_commission(booking_amount: float, rate_percent: float) -> float:
    return max(float(booking_amount or 0.0), 0.0) * float(rate_percent) / 100.0


def build_commission_invoice_rows(
    invoices: Iterable[models.BillingInvoice],
) -> list[SimpleNamespace]:
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
        ))

    return sorted(rows, key=lambda invoice: invoice.id, reverse=True)