import os
import uuid
import mimetypes
from io import BytesIO
from typing import Optional

# Graceful import: app will start even if supabase is not installed yet
try:
    from supabase import create_client, Client as SupabaseClient
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("Warning: 'supabase' package not installed. Storage features disabled. Add 'supabase>=2.0.0' to requirements.txt.")

from app.core.config import settings

# Initialize Supabase Client
supabase = None
if SUPABASE_AVAILABLE:
    try:
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            print("Supabase Storage: Connected successfully.")
        else:
            print("Warning: SUPABASE_URL or SUPABASE_KEY not set. Storage disabled.")
    except Exception as e:
        print(f"Warning: Failed to initialize Supabase client: {e}")

DEFAULT_BUCKET = "occaserve-uploads"

async def upload_file_to_supabase(
    file_bytes: bytes,
    filename: str,
    folder: str = "general",
    bucket: str = DEFAULT_BUCKET,
    content_type: str = None
) -> Optional[str]:
    """
    Uploads a file to Supabase Storage and returns the public CDN URL.
    Returns None if upload fails or Supabase is not configured.
    """
    if not supabase:
        print("Warning: Supabase client is not initialized. File not uploaded to CDN.")
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

        # Upload to Supabase Storage
        supabase.storage.from_(bucket).upload(
            file=file_bytes,
            path=path,
            file_options={"content-type": content_type}
        )

        # Get Public URL
        public_url = supabase.storage.from_(bucket).get_public_url(path)
        return public_url

    except Exception as e:
        print(f"Error uploading file to Supabase: {e}")
        return None


async def delete_file_from_supabase(url: str, bucket: str = DEFAULT_BUCKET) -> bool:
    """
    Deletes a file from Supabase Storage given its public URL.
    """
    if not supabase or not url:
        return False

    try:
        # Extract path from URL
        # URL format: https://[project].supabase.co/storage/v1/object/public/[bucket]/[folder]/[filename]
        bucket_public_path = f"/object/public/{bucket}/"
        if bucket_public_path in url:
            path_in_bucket = url.split(bucket_public_path)[-1]
            supabase.storage.from_(bucket).remove([path_in_bucket])
            return True
        return False
    except Exception as e:
        print(f"Error deleting file from Supabase: {e}")
        return False
