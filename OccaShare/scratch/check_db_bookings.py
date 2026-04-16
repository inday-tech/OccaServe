import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Try to get password from env or use the fallback from database.py
hostname = os.getenv("DB_HOST", "localhost")
database = os.getenv("DB_NAME", "occashare")
username = os.getenv("DB_USER", "postgres")
pwd = os.getenv("DB_PASSWORD", "2004") # Fallback to 2004 as seen in database.py
port_id = os.getenv("DB_PORT", "5432")
DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"

def check_columns():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        table = 'bookings'
        print(f"Checking columns for table: {table}")
        
        cur.execute(f"""
            SELECT column_name, data_type 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE table_name = '{table}';
        """)
        
        columns = cur.fetchall()
        for col in columns:
            print(f" - {col[0]} ({col[1]})")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_columns()
