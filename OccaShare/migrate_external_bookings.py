import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.db.database import get_db, SQLALCHEMY_DATABASE_URL

print("DATABASE_URL:", SQLALCHEMY_DATABASE_URL)
engine = create_engine(SQLALCHEMY_DATABASE_URL)

with engine.connect() as conn:
    queries = [
        # Bookings table
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS customer_name VARCHAR;",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS customer_email VARCHAR;",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS customer_contact VARCHAR;",
        
        # BookingPaymentRecord table
        """
        CREATE TABLE IF NOT EXISTS booking_payment_records (
            id SERIAL PRIMARY KEY,
            booking_id INTEGER REFERENCES bookings(id) ON DELETE CASCADE,
            amount FLOAT NOT NULL,
            payment_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            payment_method VARCHAR,
            payment_type VARCHAR,
            reference_notes TEXT,
            recorded_by VARCHAR
        );
        """,
        "CREATE INDEX IF NOT EXISTS ix_booking_payment_records_id ON booking_payment_records (id);",
        
        # BookingMenuItem table
        "ALTER TABLE booking_menu_items ADD COLUMN IF NOT EXISTS custom_name VARCHAR;",
        
        # BookingHistory table
        "ALTER TABLE booking_history ADD COLUMN IF NOT EXISTS entry_type VARCHAR DEFAULT 'system_change';",
        "ALTER TABLE booking_history ADD COLUMN IF NOT EXISTS communication_channel VARCHAR;",
        
        # BookingContract table
        "ALTER TABLE booking_contracts ADD COLUMN IF NOT EXISTS contract_history JSONB;"
    ]
    
    for query in queries:
        try:
            conn.execute(text(query))
            print("Executed:", query.strip().split('\\n')[0])
        except Exception as e:
            print("Error executing:", query.strip().split('\\n')[0])
            print(e)
            
    conn.commit()

print("Migration completed successfully.")
