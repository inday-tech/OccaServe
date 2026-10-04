import re
from typing import Any, Iterator, Optional

from fastapi import HTTPException, Request
from starlette.datastructures import UploadFile as StarletteUploadFile

from ..db import models
from ..db.database import SessionLocal

DEFAULT_MAX_UPLOAD_MB = 5
_BASE64_PATTERN = re.compile(r"[A-Za-z0-9_+/=-]+\Z")


def _configured_max_upload_mb() -> int:
    db = SessionLocal()
    try:
        config = db.query(models.WebsiteConfig).first()
        value = config.max_file_size_mb if config else DEFAULT_MAX_UPLOAD_MB
        return max(1, int(value or DEFAULT_MAX_UPLOAD_MB))
    except Exception:
        return DEFAULT_MAX_UPLOAD_MB
    finally:
        db.close()


def _encoded_file_size(value: str) -> Optional[int]:
    payload = value
    if value.lower().startswith("data:"):
        header, separator, payload = value.partition(",")
        if not separator or "base64" not in header.lower():
            return None

    if len(payload) < 8 or not _BASE64_PATTERN.fullmatch(payload):
        return None

    padding = len(payload) - len(payload.rstrip("="))
    return max(0, (len(payload) * 3 // 4) - padding)


def _iter_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)


def _reject_oversized(max_size_mb: int) -> None:
    raise HTTPException(
        status_code=413,
        detail=f"Maximum upload file size is {max_size_mb} MB.",
    )


async def validate_upload_size(request: Request = None) -> None:
    if request is None or request.scope.get("type") != "http":
        return
    if request.method not in {"POST", "PUT", "PATCH"}:
        return

    content_type = request.headers.get("content-type", "").lower()
    if not any(content_type.startswith(prefix) for prefix in (
        "multipart/form-data",
        "application/x-www-form-urlencoded",
        "application/json",
        "application/octet-stream",
        "image/",
        "application/pdf",
    )):
        return

    content_length = request.headers.get("content-length")
    request_size = int(content_length) if content_length and content_length.isdigit() else None

    if content_type.startswith(("multipart/form-data", "application/x-www-form-urlencoded")):
        max_size_mb = _configured_max_upload_mb()
        max_size_bytes = max_size_mb * 1024 * 1024
        form = await request.form()
        for _, value in form.multi_items():
            if isinstance(value, StarletteUploadFile):
                file_size = value.size
            elif isinstance(value, str):
                file_size = _encoded_file_size(value)
            else:
                file_size = None
            if file_size is not None and file_size > max_size_bytes:
                await form.close()
                _reject_oversized(max_size_mb)
        return

    if content_type.startswith("application/json"):
        if request_size is None:
            request_size = len(await request.body())
        if request_size <= 1024 * 1024:
            return
        max_size_mb = _configured_max_upload_mb()
        max_size_bytes = max_size_mb * 1024 * 1024
        payload = await request.json()
        if any(
            (file_size := _encoded_file_size(value)) is not None and file_size > max_size_bytes
            for value in _iter_strings(payload)
        ):
            _reject_oversized(max_size_mb)
        return

    if request_size is None:
        request_size = len(await request.body())
    if request_size <= 1024 * 1024:
        return
    max_size_mb = _configured_max_upload_mb()
    max_size_bytes = max_size_mb * 1024 * 1024
    if request_size > max_size_bytes:
        _reject_oversized(max_size_mb)