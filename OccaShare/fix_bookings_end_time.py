import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Connection string
hostname = os.getenv("DB_HOST", "localhost")
database = os.getenv("DB_NAME", "occashare")
username = os.getenv("DB_USER", "postgres")
pwd = os.getenv("DB_PASSWORD", "2004")
port_id = os.getenv("DB_PORT", "5432")
DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"

def migrate():
    try:
        print(f"Connecting to {database} as {username}...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Check if 'event_end_time' already exists
        cur.execute("SELECT 1 FROM information_schema.columns WHERE table_name='bookings' AND column_name='event_end_time'")
        if cur.fetchone():
            print("INFO: 'event_end_time' already exists in 'bookings' table.")
        else:
            # Check if 'end_time' exists to rename it
            cur.execute("SELECT 1 FROM information_schema.columns WHERE table_name='bookings' AND column_name='end_time'")
            if cur.fetchone():
                print("ACTION: Renaming 'end_time' to 'event_end_time'...")
                cur.execute("ALTER TABLE bookings RENAME COLUMN end_time TO event_end_time;")
                print("SUCCESS: Renamed successfully.")
            else:
                print("ACTION: Adding 'event_end_time' column...")
                cur.execute("ALTER TABLE bookings ADD COLUMN event_end_time TIME;")
                print("SUCCESS: Added successfully.")
        
        conn.commit()
        cur.close()
        conn.close()
        print("\nMigration complete!")
    except Exception as e:
        print(f"ERROR: Error during migration: {e}")

if __name__ == "__main__":
    migrate()
