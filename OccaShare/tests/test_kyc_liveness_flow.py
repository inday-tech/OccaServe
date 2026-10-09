import asyncio
import io
from io import BytesIO
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import BackgroundTasks, HTTPException, UploadFile
from PIL import Image

from app.db import models
from app.routers import kyc


class FakeQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model

    def filter(self, *conditions):
        return self

    def order_by(self, *columns):
        return self

    def with_for_update(self):
        return self

    def first(self):
        return self.db.records.get(self.model)

    def get(self, record_id):
        return self.db.records.get(self.model)


class FakeDB:
    def __init__(self, booking, identity=None):
        self.records = {
            models.Booking: booking,
            models.IdentityVerification: identity,
            models.VerificationSession: None,
            models.OCRVerification: None,
        }

    def query(self, model):
        return FakeQuery(self, model)

    def add(self, record):
        self.records[type(record)] = record

    def commit(self):
        pass

    def refresh(self, record):
        if getattr(record, "id", None) is None:
            record.id = 1


def make_user():
    return SimpleNamespace(
        id=7,
        role="customer",
        first_name="Test",
        middle_name=None,
        last_name="Customer",
        dob=None,
        address=None,
        kyc_attempts=0,
    )


def make_jpeg_bytes():
    image = Image.new("RGB", (320, 240), color="white")
    output = BytesIO()
    image.save(output, format="JPEG", quality=90)
    return output.getvalue()


def make_booking():
    return SimpleNamespace(
        id=86,
        user_id=7,
        current_address=None,
        id_address=None,
    )


def test_id_upload_persists_booking_state_before_liveness_init(monkeypatch):
    async def valid_id_result(*args, **kwargs):
        return {
            "status": "matched",
            "name_matched": True,
            "ocr_data": {"fields": {"last_name": "Customer"}},
        }

    monkeypatch.setattr(kyc, "store_identity_image", lambda *args, **kwargs: "/api/bookings/kyc/private/" + "a" * 32 + ".jpg")
    monkeypatch.setattr(kyc.verification_service, "verify_id_document", valid_id_result)
    user = make_user()
    db = FakeDB(make_booking())
    upload = UploadFile(filename="id.jpg", file=BytesIO(make_jpeg_bytes()))

    result = asyncio.run(kyc.upload_id(
        booking_id=86,
        id_type="Passport",
        id_number="P1234567A",
        first_name="Test",
        middle_name=None,
        last_name="Customer",
        dob=None,
        address=None,
        id_address_extracted=None,
        id_document=upload,
        db=db,
        current_user=user,
    ))

    record = db.records[models.IdentityVerification]
    assert result["success"] is True
    assert record.booking_id == 86
    assert record.verification_status == "pending_liveliness"
    initialized = asyncio.run(kyc.init_kyc_session(86, db=db, current_user=user))
    assert initialized["success"] is True
    assert initialized["session_token"]


def test_id_upload_routes_missing_structured_ocr_to_manual_review(monkeypatch):
    async def inconclusive_id_result(*args, **kwargs):
        return {"status": "matched", "name_matched": True, "ocr_data": {}}

    monkeypatch.setattr(kyc, "store_identity_image", lambda *args, **kwargs: "/api/bookings/kyc/private/" + "a" * 32 + ".jpg")
    monkeypatch.setattr(kyc.verification_service, "verify_id_document", inconclusive_id_result)
    db = FakeDB(make_booking())

    result = asyncio.run(kyc.upload_id(
        booking_id=86,
        id_type="Passport",
        id_number="P1234567A",
        first_name="Test",
        middle_name=None,
        last_name="Customer",
        dob=None,
        address=None,
        id_address_extracted=None,
        id_document=UploadFile(filename="id.jpg", file=BytesIO(make_jpeg_bytes())),
        db=db,
        current_user=make_user(),
    ))

    record = db.records[models.IdentityVerification]
    assert result["status"] == "pending_manual_review"
    assert record.verification_status == "pending_manual_review"
    assert record.ocr_status == "needs_review"
    assert record.ocr_data == {}


def test_id_upload_routes_account_conflict_to_manual_review(monkeypatch):
    async def review_id_result(*args, **kwargs):
        return {
            "status": "needs_review",
            "name_matched": False,
            "ocr_data": {"fields": {"last_name": {"value": "Different", "confidence": 90}}},
        }

    monkeypatch.setattr(kyc, "store_identity_image", lambda *args, **kwargs: "/api/bookings/kyc/private/" + "a" * 32 + ".jpg")
    monkeypatch.setattr(kyc.verification_service, "verify_id_document", review_id_result)
    db = FakeDB(make_booking())

    result = asyncio.run(kyc.upload_id(
        booking_id=86,
        id_type="Passport",
        id_number="P1234567A",
        first_name="Test",
        middle_name=None,
        last_name="Customer",
        dob=None,
        address=None,
        id_address_extracted=None,
        id_document=UploadFile(filename="id.jpg", file=BytesIO(make_jpeg_bytes())),
        db=db,
        current_user=make_user(),
    ))

    assert result["status"] == "pending_manual_review"
    assert db.records[models.IdentityVerification].verification_status == "pending_manual_review"


def test_id_upload_does_not_allow_another_customer_booking(monkeypatch):
    db = FakeDB(SimpleNamespace(id=86, user_id=99, current_address=None, id_address=None))
    with pytest.raises(HTTPException) as error:
        asyncio.run(kyc.upload_id(
            booking_id=86,
            id_type="Passport",
            id_number="P1234567A",
            first_name="Test",
            middle_name=None,
            last_name="Customer",
            dob=None,
            address=None,
            id_address_extracted=None,
            id_document=UploadFile(filename="id.jpg", file=BytesIO(make_jpeg_bytes())),
            db=db,
            current_user=make_user(),
        ))
    assert error.value.status_code == 404


def test_failed_id_validation_is_persisted_and_cannot_start_liveness(monkeypatch):
    async def rejected_id_result(*args, **kwargs):
        return {
            "status": "rejected",
            "name_matched": False,
            "failure_reason": "ID number mismatch",
            "ocr_data": {"fields": {"last_name": "Different"}},
        }

    monkeypatch.setattr(kyc, "store_identity_image", lambda *args, **kwargs: "/api/bookings/kyc/private/" + "a" * 32 + ".jpg")
    monkeypatch.setattr(kyc.verification_service, "verify_id_document", rejected_id_result)
    user = make_user()
    db = FakeDB(make_booking())
    upload = UploadFile(filename="id.jpg", file=BytesIO(make_jpeg_bytes()))

    with pytest.raises(HTTPException) as error:
        asyncio.run(kyc.upload_id(
            booking_id=86,
            id_type="Passport",
            id_number="P1234567A",
            first_name="Test",
            middle_name=None,
            last_name="Customer",
            dob=None,
            address=None,
            id_address_extracted=None,
            id_document=upload,
            db=db,
            current_user=user,
        ))

    record = db.records[models.IdentityVerification]
    assert error.value.status_code == 400
    assert record.verification_status == "failed"
    assert record.failure_reason == "ID number mismatch"
    with pytest.raises(HTTPException) as init_error:
        asyncio.run(kyc.init_kyc_session(86, db=db, current_user=user))
    assert init_error.value.status_code == 400


@pytest.mark.parametrize("status", ["pending", "pending_confirmation", "failed", "liveliness_failed"])
def test_liveness_init_rejects_id_states_that_are_not_ready(status):
    record = models.IdentityVerification(user_id=7, booking_id=86, verification_status=status)
    db = FakeDB(make_booking(), record)

    with pytest.raises(HTTPException) as error:
        asyncio.run(kyc.init_kyc_session(86, db=db, current_user=make_user()))

    assert error.value.status_code == 400
    assert error.value.detail == "ID verification is not ready for liveness verification."


def test_liveness_retry_resets_failed_attempt_then_initializes():
    record = models.IdentityVerification(
        user_id=7,
        booking_id=86,
        verification_status="liveliness_failed",
        failure_reason="Liveness failed",
        liveness_status="failed",
    )
    db = FakeDB(make_booking(), record)
    user = make_user()

    asyncio.run(kyc.reset_liveness_status(booking_id=86, db=db, current_user=user))
    assert record.verification_status == "pending_liveliness"
    assert record.failure_reason is None
    assert record.liveness_status is None

    initialized = asyncio.run(kyc.init_kyc_session(86, db=db, current_user=user))
    assert initialized["success"] is True
    assert initialized["session_token"]


def test_expired_liveness_session_is_rejected():
    record = models.IdentityVerification(user_id=7, booking_id=86, verification_status="pending_liveliness")
    session = models.VerificationSession(
        user_id=7,
        status="pending_liveness",
        verification_result={"booking_id": 86, "session_token": "expired-token"},
        created_at=datetime.now(timezone.utc) - timedelta(minutes=11),
    )
    db = FakeDB(make_booking(), record)
    db.records[models.VerificationSession] = session

    with pytest.raises(HTTPException) as error:
        asyncio.run(kyc.verify_full(
            booking_id=86,
            background_tasks=BackgroundTasks(),
            request=None,
            selfies=[],
            completed_challenges=None,
            session_token="expired-token",
            db=db,
            current_user=make_user(),
        ))

    assert error.value.status_code == 409
    assert "expired" in error.value.detail.lower()
