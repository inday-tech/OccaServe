from app.db.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text('ALTER TABLE services ADD COLUMN requires_agreement BOOLEAN DEFAULT FALSE;'))
    except Exception as e:
        print(f"Error requires_agreement: {e}")
        
    try:
        conn.execute(text('ALTER TABLE services ADD COLUMN downpayment_percentage INTEGER DEFAULT 50;'))
    except Exception as e:
        print(f"Error downpayment_percentage: {e}")
        
    try:
        conn.execute(text('ALTER TABLE services ADD COLUMN minimum_hours INTEGER DEFAULT 1;'))
    except Exception as e:
        print(f"Error minimum_hours: {e}")
        
    conn.commit()
    print("Columns added to services table")
