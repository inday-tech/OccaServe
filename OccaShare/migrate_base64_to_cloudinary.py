"""
Migration Script: Migrate Legacy Base64 Images to Cloudinary CDN
Decodes existing `data:image...;base64,...` strings in PostgreSQL and uploads them directly to Cloudinary,
updating database rows with secure CDN URLs using raw SQL (resilient to schema differences).
"""

import sys
import os
import base64
from sqlalchemy import text

# Add app directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.services.storage import upload_file_to_cloudinary, _CLOUDINARY_CONFIGURED


def decode_base64_data_uri(data_uri: str):
    """
    Decodes a Base64 data URI string into binary bytes.
    Returns (bytes, mime_type) or (None, None) if not a Base64 string.
    """
    if not data_uri or not isinstance(data_uri, str) or not data_uri.startswith("data:"):
        return None, None

    try:
        header, encoded = data_uri.split(",", 1)
        mime = header.split(";")[0].replace("data:", "")
        file_bytes = base64.b64decode(encoded)
        return file_bytes, mime
    except Exception as e:
        print(f"  [ERROR] Failed to decode Base64 URI: {e}")
        return None, None


def run_migration():
    print("=" * 60)
    print("Starting Base64 to Cloudinary Database Migration (Raw SQL)...")
    print("=" * 60)

    if not _CLOUDINARY_CONFIGURED:
        print("\n[CRITICAL ERROR] Cloudinary is NOT configured!")
        print("Please check your .env file or Railway environment variables:")
        print("  - CLOUDINARY_CLOUD_NAME")
        print("  - CLOUDINARY_API_KEY")
        print("  - CLOUDINARY_API_SECRET")
        return

    db = SessionLocal()
    total_migrated = 0

    # Comprehensive Targets List: (table_name, column_name, cloudinary_folder)
    migration_targets = [
        ("users", "profile_image_url", "profile_images"),
        ("caterer_profiles", "logo_url", "profile_images"),
        ("caterer_profiles", "cover_image_url", "gallery"),
        ("caterer_profiles", "permit_url", "verification"),
        ("caterer_profiles", "dti_url", "verification"),
        ("caterer_profiles", "bir_url", "verification"),
        ("caterer_profiles", "mayors_permit_url", "verification"),
        ("caterer_galleries", "media_url", "gallery"),
        ("catering_packages", "image_url", "menu_images"),
        ("menu_items", "image_url", "menu_images"),
        ("portfolio_images", "image_url", "gallery"),
        ("social_posts", "image_url", "gallery"),
        ("identity_verifications", "document_url", "valid_ids"),
        ("identity_verifications", "document_back_url", "valid_ids"),
        ("identity_verifications", "selfie_url", "verification"),
        ("identity_verifications", "selfie_2_url", "verification"),
        ("identity_verifications", "selfie_3_url", "verification"),
        ("bookings", "payment_proof_url", "payment_receipts"),
        ("bookings", "dispatch_proof_url", "verification"),
        ("bookings", "release_photo_url", "verification"),
        ("bookings", "damage_proof_url", "verification"),
        ("billing_invoices", "payment_proof_url", "payment_receipts"),
        ("booking_messages", "attachment_url", "chat_attachments")
    ]

    for table_name, column_name, folder in migration_targets:
        try:
            query = text(f"SELECT id, {column_name} FROM {table_name} WHERE {column_name} LIKE 'data:%'")
            rows = db.execute(query).fetchall()
            
            if not rows:
                continue

            print(f"\nProcessing '{table_name}.{column_name}' ({len(rows)} records found)...")

            for row in rows:
                row_id = row[0]
                data_uri = row[1]

                if not data_uri or not data_uri.startswith("data:"):
                    continue

                file_bytes, _ = decode_base64_data_uri(data_uri)
                if not file_bytes:
                    continue

                cdn_url = upload_file_to_cloudinary(file_bytes, folder=folder)
                if cdn_url:
                    update_stmt = text(f"UPDATE {table_name} SET {column_name} = :url WHERE id = :id")
                    db.execute(update_stmt, {"url": cdn_url, "id": row_id})
                    db.commit()
                    total_migrated += 1
                    print(f"  ✓ {table_name} #{row_id} [{column_name}] → {cdn_url}")

        except Exception as e:
            db.rollback()
            # Non-fatal notice if table or column doesn't exist in local schema
            print(f"  [Skipped] {table_name}.{column_name}: {e}")

    db.close()
    print("\n" + "=" * 60)
    print("SUCCESS: Base64 Migration Complete!")
    print(f"Total Base64 Images Migrated to Cloudinary: {total_migrated}")
    print("=" * 60)


if __name__ == "__main__":
    run_migration()
