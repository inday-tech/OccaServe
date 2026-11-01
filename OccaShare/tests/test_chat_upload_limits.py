import asyncio
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile

from app.routers import chat
from app.db import models


class ConfigQuery:
    def first(self):
        return SimpleNamespace(max_file_size_mb=1)


class ConfigDatabase:
    def query(self, model):
        assert model is models.WebsiteConfig
        return ConfigQuery()


def test_chat_upload_rejects_file_over_configured_limit(monkeypatch):
    upload_called = False

    def reject_unexpected_upload(*args, **kwargs):
        nonlocal upload_called
        upload_called = True
        return "https://example.test/file.txt"

    monkeypatch.setattr(
        "app.services.storage.upload_file_to_cloudinary",
        reject_unexpected_upload,
    )
    file = UploadFile(filename="large.txt", file=BytesIO(b"x" * (1024 * 1024 + 1)))

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            chat.upload_chat_file(
                file=file,
                db=ConfigDatabase(),
                current_user=SimpleNamespace(id=1),
            )
        )

    assert error.value.status_code == 413
    assert "1 MB" in error.value.detail
    assert not upload_called


def test_chat_upload_accepts_file_at_configured_limit(monkeypatch):
    uploaded = {}

    def save_upload(content, folder):
        uploaded["content"] = content
        uploaded["folder"] = folder
        return "https://example.test/file.txt"

    monkeypatch.setattr(
        "app.services.storage.upload_file_to_cloudinary",
        save_upload,
    )
    file = UploadFile(filename="valid.txt", file=BytesIO(b"x" * (1024 * 1024)))

    result = asyncio.run(
        chat.upload_chat_file(
            file=file,
            db=ConfigDatabase(),
            current_user=SimpleNamespace(id=1),
        )
    )

    assert result == {
        "file_url": "https://example.test/file.txt",
        "file_name": "valid.txt",
        "message_type": "file",
    }
    assert len(uploaded["content"]) == 1024 * 1024
    assert uploaded["folder"] == "chat_attachments"
