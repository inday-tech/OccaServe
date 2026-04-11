import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def migrate():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("Checking for is_archived columns...")
        
        tables = ['payouts', 'reviews', 'bookings', 'inquiries']
        
        for table in tables:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;")
                print(f"Added is_archived to {table}")
            except psycopg2.errors.DuplicateColumn:
                conn.rollback()
                print(f"Column is_archived already exists in {table}")
            except Exception as e:
                conn.rollback()
                print(f"Error adding column to {table}: {e}")
            else:
                conn.commit()
                
        cur.close()
        conn.close()
        print("Migration complete.")
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    migrate()
