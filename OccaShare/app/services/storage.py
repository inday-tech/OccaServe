"""
Cloudinary Storage Service
Handles uploading and deleting images/assets via Cloudinary.
Organized folder structure:
  - profile_images/
  - valid_ids/
  - gallery/
  - menu_images/
  - payment_receipts/
  - verification/
"""

import os
from typing import Optional, Dict, Any
from app.core.config import settings

# --- CLOUDINARY CONFIGURATION ---
_CLOUDINARY_CLOUD_NAME = getattr(settings, "CLOUDINARY_CLOUD_NAME", "") or os.getenv("CLOUDINARY_CLOUD_NAME", "")
_CLOUDINARY_API_KEY = getattr(settings, "CLOUDINARY_API_KEY", "") or os.getenv("CLOUDINARY_API_KEY", "")
_CLOUDINARY_API_SECRET = getattr(settings, "CLOUDINARY_API_SECRET", "") or os.getenv("CLOUDINARY_API_SECRET", "")

_CLOUDINARY_CONFIGURED = False
if _CLOUDINARY_CLOUD_NAME and _CLOUDINARY_API_KEY and _CLOUDINARY_API_SECRET:
    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(
            cloud_name=_CLOUDINARY_CLOUD_NAME,
            api_key=_CLOUDINARY_API_KEY,
            api_secret=_CLOUDINARY_API_SECRET,
            secure=True
        )
        _CLOUDINARY_CONFIGURED = True
        print(f"Cloudinary Storage: Configured for cloud '{_CLOUDINARY_CLOUD_NAME}'")
    except Exception as e:
        print(f"Warning: Cloudinary configuration failed: {e}")
else:
    print("Cloudinary Storage: Not configured (missing CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, or CLOUDINARY_API_SECRET).")


def extract_public_id(public_id_or_url: str) -> str:
    """
    Extracts Cloudinary public_id from a full URL if needed.
    Example:
      'https://res.cloudinary.com/vtottsao/image/upload/v123456/gallery/abc123.jpg'
      -> 'gallery/abc123'
    """
    if not public_id_or_url:
        return ""
    if "cloudinary.com" in public_id_or_url:
        parts = public_id_or_url.split("/upload/")
        if len(parts) > 1:
            rel = parts[1]
            if rel.startswith("v") and "/" in rel:
                rel = rel.split("/", 1)[1]
            if "." in rel:
                rel = rel.rsplit(".", 1)[0]
            return rel
    return public_id_or_url


def upload_file_to_cloudinary(
    file_bytes: bytes,
    folder: str = "general",
    public_id: Optional[str] = None
) -> Optional[str]:
    """
    Uploads a file byte stream to Cloudinary and returns the secure CDN URL.
    Folders: profile_images, valid_ids, gallery, menu_images, payment_receipts, verification
    """
    res = upload_image_with_metadata(file_bytes, folder=folder, public_id=public_id)
    return res.get("url") if res else None


def upload_image_with_metadata(
    file_bytes: bytes,
    folder: str = "general",
    public_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Uploads file to Cloudinary and returns metadata dict:
    {
       "url": "https://res.cloudinary.com/.../image/upload/v123/folder/filename.jpg",
       "public_id": "folder/filename",
       "format": "jpg",
       "width": 800,
       "height": 600
    }
    """
    if not _CLOUDINARY_CONFIGURED:
        print("Warning: Cloudinary is not configured. Saving file locally to disk...")
        return _save_file_locally(file_bytes, folder=folder, public_id=public_id)

    try:
        import cloudinary.uploader
        options = {
            "folder": folder,
            "resource_type": "auto"
        }
        if public_id:
            options["public_id"] = public_id

        res = cloudinary.uploader.upload(file_bytes, **options)
        return {
            "url": res.get("secure_url") or res.get("url"),
            "public_id": res.get("public_id"),
            "format": res.get("format"),
            "width": res.get("width"),
            "height": res.get("height")
        }
    except Exception as e:
        print(f"Error uploading file to Cloudinary: {e}. Falling back to local storage.")
        return _save_file_locally(file_bytes, folder=folder, public_id=public_id)


def _save_file_locally(file_bytes: bytes, folder: str = "general", public_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fallback helper to save uploaded file to local app/static/uploads directory."""
    try:
        import uuid
        upload_dir = os.path.join("app", "static", "uploads", folder)
        os.makedirs(upload_dir, exist_ok=True)
        filename = f"{public_id or uuid.uuid4().hex}.jpg"
        if not filename.endswith((".jpg", ".png", ".jpeg")):
            filename += ".jpg"
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        local_url = f"/static/uploads/{folder}/{filename}"
        return {
            "url": local_url,
            "public_id": f"{folder}/{filename}",
            "format": "jpg",
            "width": 800,
            "height": 600
        }
    except Exception as err:
        print(f"Error saving file locally: {err}")
        return None


def delete_file_from_cloudinary(public_id_or_url: str) -> bool:
    """
    Deletes an asset from Cloudinary given its public_id or full Cloudinary URL.
    Handles extraction of public_id automatically from full URL.
    """
    if not _CLOUDINARY_CONFIGURED or not public_id_or_url:
        return False

    try:
        import cloudinary.uploader
        public_id = extract_public_id(public_id_or_url)
        res = cloudinary.uploader.destroy(public_id)
        return res.get("result") in ("ok", "not_found")
    except Exception as e:
        print(f"Error deleting file from Cloudinary: {e}")
        return False


# Aliases for clean usage across the application
async def upload_file(file_bytes: bytes, filename: str = "", folder: str = "general") -> Optional[str]:
    """Alias for upload_file_to_cloudinary."""
    return upload_file_to_cloudinary(file_bytes, folder=folder)


async def delete_file(url: str) -> bool:
    """Alias for delete_file_from_cloudinary."""
    return delete_file_from_cloudinary(url)
