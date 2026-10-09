"""Private, encrypted storage for identity images uploaded to OccaServe."""

from __future__ import annotations

import io
import os
import re
import uuid
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from ..core.config import settings
from ..core.encryption import decrypt_data, encrypt_data, require_secure_encryption_key

MAX_IDENTITY_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IDENTITY_IMAGE_PIXELS = 25_000_000
_ALLOWED_FORMATS = {
    ".jpg": ("JPEG", "image/jpeg"),
    ".jpeg": ("JPEG", "image/jpeg"),
    ".png": ("PNG", "image/png"),
    ".webp": ("WEBP", "image/webp"),
}
_PRIVATE_NAME = re.compile(r"\A[a-f0-9]{32}\.(?:jpg|jpeg|png|webp)\Z")
_DEFAULT_PRIVATE_IDENTITY_DIR = Path(__file__).resolve().parents[1] / "private_uploads" / "identity"
PRIVATE_IDENTITY_DIR = (
    Path(settings.KYC_PRIVATE_STORAGE_DIR).expanduser().resolve()
    if settings.KYC_PRIVATE_STORAGE_DIR.strip()
    else _DEFAULT_PRIVATE_IDENTITY_DIR
)


def validate_identity_image(content: bytes, original_filename: str) -> tuple[str, str]:
    """Validate size, extension, actual image format, dimensions, and readability."""
    if not content:
        raise ValueError("The image file is empty.")
    if len(content) > MAX_IDENTITY_IMAGE_BYTES:
        raise ValueError("The image must be 5 MB or smaller.")

    suffix = Path(original_filename or "").suffix.lower()
    expected = _ALLOWED_FORMATS.get(suffix)
    if not expected:
        raise ValueError("Upload a JPG, PNG, or WebP image.")

    try:
        with Image.open(io.BytesIO(content)) as image:
            actual_format = image.format
            width, height = image.size
            if actual_format != expected[0]:
                raise ValueError("The file extension does not match the image format.")
            if width < 160 or height < 160 or width * height > MAX_IDENTITY_IMAGE_PIXELS:
                raise ValueError("The image dimensions are unsupported. Use a clear image under 25 megapixels.")
            image.verify()
        # Reopen and force decoding; verify() checks structure but does not decode all pixels.
        with Image.open(io.BytesIO(content)) as image:
            image.load()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("The image is corrupted or unreadable. Choose another image.") from exc

    return expected[1], suffix


def store_identity_image(content: bytes, original_filename: str) -> str:
    """Encrypt an already validated image outside the publicly mounted static tree."""
    require_secure_encryption_key()
    _, suffix = validate_identity_image(content, original_filename)
    filename = f"{uuid.uuid4().hex}{suffix}"
    PRIVATE_IDENTITY_DIR.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        try:
            os.chmod(PRIVATE_IDENTITY_DIR, 0o700)
        except OSError:
            pass
    target = PRIVATE_IDENTITY_DIR / filename
    with target.open("xb") as stored:
        stored.write(encrypt_data(content))
    if os.name != "nt":
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
    return f"/api/bookings/kyc/private/{filename}"


def private_identity_filename(reference: str) -> str | None:
    if not isinstance(reference, str):
        return None
    if reference.startswith("private-kyc://"):
        filename = reference.removeprefix("private-kyc://")
    elif reference.startswith("/api/bookings/kyc/private/"):
        filename = reference.removeprefix("/api/bookings/kyc/private/")
    else:
        return None
    if not _PRIVATE_NAME.fullmatch(filename):
        raise ValueError("Invalid private identity image reference.")
    return filename


def load_identity_image(reference: str) -> bytes:
    filename = private_identity_filename(reference)
    if not filename:
        raise ValueError("Not a private identity image reference.")
    target = PRIVATE_IDENTITY_DIR / filename
    return decrypt_data(target.read_bytes())


def delete_identity_image(reference: str) -> bool:
    filename = private_identity_filename(reference)
    if not filename:
        return False
    target = PRIVATE_IDENTITY_DIR / filename
    try:
        target.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def identity_image_url(reference: str) -> str:
    filename = private_identity_filename(reference)
    if not filename:
        raise ValueError("Not a private identity image reference.")
    return f"/api/bookings/kyc/private/{filename}"
