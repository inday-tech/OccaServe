import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Primary connection string
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fallback to local development components
    hostname = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "occashare")
    username = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "2004")
    port_id = os.getenv("DB_PORT", "5432")
    DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"

def check_columns():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users';")
        columns = [row[0] for row in cur.fetchall()]
        print(f"Columns in 'users' table: {columns}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_columns()
