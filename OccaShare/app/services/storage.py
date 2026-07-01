"""
Supabase Storage Service — ZERO new dependencies.
Uses httpx (already in requirements.txt) to call Supabase Storage REST API directly.
No 'supabase' package needed = no pip conflicts on Railway.
"""

import uuid
import mimetypes
from typing import Optional
import httpx

from app.core.config import settings

DEFAULT_BUCKET = "occaserve-uploads"

# Pre-build the base URL and auth header once at startup
_SUPABASE_URL = getattr(settings, "SUPABASE_URL", "") or ""
_SUPABASE_KEY = getattr(settings, "SUPABASE_KEY", "") or ""
_STORAGE_BASE = f"{_SUPABASE_URL}/storage/v1" if _SUPABASE_URL else ""

if _STORAGE_BASE and _SUPABASE_KEY:
    print(f"Supabase Storage: Configured via REST API → {_SUPABASE_URL}")
else:
    print("Warning: SUPABASE_URL or SUPABASE_KEY not set. Cloud storage disabled; uploads will use local fallback.")


async def upload_file_to_supabase(
    file_bytes: bytes,
    filename: str,
    folder: str = "general",
    bucket: str = DEFAULT_BUCKET,
    content_type: str = None
) -> Optional[str]:
    """
    Uploads a file to Supabase Storage via REST API and returns the public CDN URL.
    Uses httpx — no supabase package required.
    Returns None if upload fails or Supabase is not configured.
    """
    if not _STORAGE_BASE or not _SUPABASE_KEY:
        print("Warning: Supabase not configured. File not uploaded to CDN.")
        return None

    try:
        # Generate a unique filename to prevent collisions
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else ''
        unique_filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex

        # Build path inside bucket
        path = f"{folder}/{unique_filename}"

        # Determine content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            if not content_type:
                content_type = "application/octet-stream"

        # Upload via Supabase Storage REST API
        upload_url = f"{_STORAGE_BASE}/object/{bucket}/{path}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                upload_url,
                headers={
                    "Authorization": f"Bearer {_SUPABASE_KEY}",
                    "apikey": _SUPABASE_KEY,
                    "Content-Type": content_type,
                },
                content=file_bytes,
            )

        if response.status_code in (200, 201):
            # Build the permanent public CDN URL
            public_url = f"{_SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"
            return public_url
        else:
            print(f"Supabase upload failed ({response.status_code}): {response.text}")
            return None

    except Exception as e:
        print(f"Error uploading file to Supabase: {e}")
        return None


async def delete_file_from_supabase(url: str, bucket: str = DEFAULT_BUCKET) -> bool:
    """
    Deletes a file from Supabase Storage via REST API given its public URL.
    """
    if not _STORAGE_BASE or not _SUPABASE_KEY or not url:
        return False

    try:
        # Extract path from public URL
        # URL format: https://[project].supabase.co/storage/v1/object/public/[bucket]/[folder]/[filename]
        bucket_public_path = f"/object/public/{bucket}/"
        if bucket_public_path not in url:
            return False

        path_in_bucket = url.split(bucket_public_path)[-1]

        # Delete via Supabase Storage REST API
        delete_url = f"{_STORAGE_BASE}/object/{bucket}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                "DELETE",
                delete_url,
                headers={
                    "Authorization": f"Bearer {_SUPABASE_KEY}",
                    "apikey": _SUPABASE_KEY,
                    "Content-Type": "application/json",
                },
                json={"prefixes": [path_in_bucket]},
            )

        return response.status_code in (200, 201, 204)

    except Exception as e:
        print(f"Error deleting file from Supabase: {e}")
        return False
