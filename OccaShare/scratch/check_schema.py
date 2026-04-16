import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_db():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )
    cur = conn.cursor()
    
    tables = ["catering_packages", "menu_items", "bookings", "caterer_profiles"]
    
    for table in tables:
        print(f"\nChecking table: {table}")
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'")
        cols = [c[0] for c in cur.fetchall()]
        print(f"Columns: {cols}")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_db()
