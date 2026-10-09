import asyncio
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from fastapi import HTTPException
from types import SimpleNamespace

from app.services import identity_storage
from app.routers import kyc


def make_image_bytes(fmt="JPEG", size=(320, 240)):
    image = Image.new("RGB", size, color="white")
    output = BytesIO()
    image.save(output, format=fmt)
    return output.getvalue()


@pytest.mark.parametrize(
    ("filename", "fmt", "mime"),
    [
        ("front.jpg", "JPEG", "image/jpeg"),
        ("front.png", "PNG", "image/png"),
        ("front.webp", "WEBP", "image/webp"),
    ],
)
def test_validate_identity_image_accepts_supported_formats(filename, fmt, mime):
    assert identity_storage.validate_identity_image(make_image_bytes(fmt), filename) == (
        mime,
        "." + filename.rsplit(".", 1)[-1],
    )


def test_validate_identity_image_rejects_signature_mismatch():
    with pytest.raises(ValueError, match="extension does not match"):
        identity_storage.validate_identity_image(make_image_bytes("JPEG"), "front.png")


@pytest.mark.parametrize(
    ("content", "filename", "message"),
    [
        (b"", "front.jpg", "empty"),
        (b"not an image", "front.jpg", "corrupted"),
        (make_image_bytes(size=(100, 100)), "front.jpg", "dimensions"),
        (make_image_bytes(), "front.svg", "JPG, PNG, or WebP"),
    ],
)
def test_validate_identity_image_rejects_invalid_files(content, filename, message):
    with pytest.raises(ValueError, match=message):
        identity_storage.validate_identity_image(content, filename)


def test_validate_identity_image_rejects_oversized_files():
    with pytest.raises(ValueError, match="5 MB or smaller"):
        identity_storage.validate_identity_image(
            b"x" * (identity_storage.MAX_IDENTITY_IMAGE_BYTES + 1), "front.jpg"
        )


def test_identity_upload_is_encrypted_and_stored_outside_static(monkeypatch):
    storage_path = Path(__file__).parent / "_identity_storage_test"
    monkeypatch.setattr(identity_storage, "PRIVATE_IDENTITY_DIR", storage_path)
    monkeypatch.setattr(identity_storage, "require_secure_encryption_key", lambda: None)
    content = make_image_bytes()

    reference = identity_storage.store_identity_image(content, "untrusted-name.jpg")
    filename = identity_storage.private_identity_filename(reference)
    stored_path = storage_path / filename

    assert reference.startswith("/api/bookings/kyc/private/")
    assert filename != "untrusted-name.jpg"
    assert stored_path.read_bytes() != content
    assert identity_storage.load_identity_image(reference) == content
    assert identity_storage.delete_identity_image(reference) is True


class DocumentQuery:
    def __init__(self, record):
        self.record = record

    def filter(self, *conditions):
        return self

    def first(self):
        return self.record


class DocumentDB:
    def __init__(self, record):
        self.record = record

    def query(self, model):
        return DocumentQuery(self.record)


def test_private_identity_document_requires_record_owner(monkeypatch):
    filename = "a" * 32 + ".jpg"
    reference = f"/api/bookings/kyc/private/{filename}"
    record = SimpleNamespace(
        user_id=7,
        document_url=reference,
        document_back_url=None,
        selfie_url=None,
        selfie_2_url=None,
        selfie_3_url=None,
    )
    monkeypatch.setattr(kyc, "load_identity_image", lambda value: b"image-bytes")

    response = asyncio.run(kyc.view_private_kyc_document(
        filename,
        db=DocumentDB(record),
        current_user=SimpleNamespace(id=7, role="customer"),
    ))
    assert response.body == b"image-bytes"
    assert response.headers["cache-control"] == "private, no-store, max-age=0"

    with pytest.raises(HTTPException) as error:
        asyncio.run(kyc.view_private_kyc_document(
            filename,
            db=DocumentDB(record),
            current_user=SimpleNamespace(id=8, role="customer"),
        ))
    assert error.value.status_code == 404
