import re
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Read models.py
with open('../app/db/models.py', 'r') as f:
    models_content = f.read()

# Read master_migration.py
with open('../scripts/master_migration.py', 'r') as f:
    migration_content = f.read()

model_cols = re.findall(r'^\s+([a-zA-Z0-9_]+)\s*=\s*Column\(', models_content, re.MULTILINE)
migration_cols = re.findall(r'\("([a-zA-Z0-9_]+)",', migration_content)

missing = set(model_cols) - set(migration_cols)
# ignore common fields that are likely part of initial creation
ignore = {'id', 'user_id', 'caterer_id', 'package_id', 'booking_id', 'payout_id', 'role', 'email', 'password_hash', 'first_name', 'last_name', 'phone_number', 'profile_picture_url', 'business_name', 'slug', 'business_type', 'years_of_operation', 'description', 'logo_url', 'cover_image_url', 'contact_phone', 'contact_address', 'city', 'coverage_area', 'cuisine_types', 'event_types', 'rating', 'review_count', 'payout_method', 'payout_account_name', 'payout_account_number', 'name', 'price', 'price_unit', 'min_guests', 'max_guests', 'image_url', 'category', 'event_name', 'event_type', 'event_date', 'event_time', 'venue_address', 'guest_count', 'total_amount', 'status', 'payment_status', 'payment_method', 'payment_reference', 'payment_proof_url', 'created_at', 'updated_at', 'content', 'post_type', 'viewer_id'}

real_missing = missing - ignore

print("Potentially Missing Columns:")
for m in sorted(real_missing):
    print(m)
