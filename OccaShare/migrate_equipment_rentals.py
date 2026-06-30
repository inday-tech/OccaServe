import sqlite3

def migrate_equipment_rentals():
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()

    # Add Equipment fields
    try:
        cursor.execute("ALTER TABLE equipment ADD COLUMN security_deposit_pct FLOAT DEFAULT 20.0")
        print("Added security_deposit_pct to equipment")
    except sqlite3.OperationalError as e:
        print(f"Skipped security_deposit_pct: {e}")

    try:
        cursor.execute("ALTER TABLE equipment ADD COLUMN maintenance_buffer_hours INTEGER DEFAULT 12")
        print("Added maintenance_buffer_hours to equipment")
    except sqlite3.OperationalError as e:
        print(f"Skipped maintenance_buffer_hours: {e}")

    try:
        cursor.execute("ALTER TABLE equipment ADD COLUMN requires_kyc BOOLEAN DEFAULT 0")
        print("Added requires_kyc to equipment")
    except sqlite3.OperationalError as e:
        print(f"Skipped requires_kyc: {e}")

    # Add Booking fields
    booking_columns = [
        ("security_deposit_amount", "FLOAT DEFAULT 0.0"),
        ("security_deposit_status", "VARCHAR DEFAULT 'unpaid'"),
        ("damage_deduction_amount", "FLOAT DEFAULT 0.0"),
        ("missing_items_count", "INTEGER DEFAULT 0"),
        ("release_photo_url", "VARCHAR"),
        ("return_photo_url", "VARCHAR"),
        ("damage_proof_url", "VARCHAR"),
        ("rental_disputed", "BOOLEAN DEFAULT 0")
    ]
    
    for col_name, col_type in booking_columns:
        try:
            cursor.execute(f"ALTER TABLE bookings ADD COLUMN {col_name} {col_type}")
            print(f"Added {col_name} to bookings")
        except sqlite3.OperationalError as e:
            print(f"Skipped {col_name}: {e}")

    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate_equipment_rentals()
