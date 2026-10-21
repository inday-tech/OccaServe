import asyncio
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.db import models
from app.routers import quotations


class QuotationQuery:
    def __init__(self, quotation):
        self.quotation = quotation

    def options(self, *_args):
        return self

    def filter(self, *_args):
        return self

    def first(self):
        return self.quotation


class QuotationDatabase:
    def __init__(self, quotation):
        self.quotation = quotation

    def query(self, model):
        assert model is models.Quotation
        return QuotationQuery(self.quotation)


def test_customer_cannot_sign_before_caterer(monkeypatch):
    customer = SimpleNamespace(id=12)
    booking = SimpleNamespace(
        id=34,
        user_id=customer.id,
        caterer=SimpleNamespace(user_id=56),
    )
    quotation = SimpleNamespace(
        booking=booking,
        caterer_signature=None,
        customer_signature=None,
    )
    db = QuotationDatabase(quotation)
    monkeypatch.setattr(quotations, "get_session_user", lambda _request, _db: customer)

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            quotations.sign_contract(
                booking_id=booking.id,
                request=object(),
                background_tasks=BackgroundTasks(),
                data={
                    "signature_data": "data:image/png;base64,signature",
                    "confirm_agreement": True,
                },
                db=db,
            )
        )

    assert error.value.status_code == 409
    assert "caterer must sign" in error.value.detail.lower()
