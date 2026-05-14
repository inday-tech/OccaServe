import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Primary connection string
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    hostname = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "occashare")
    username = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "2004")
    port_id = os.getenv("DB_PORT", "5432")
    DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"

def test_query():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("Testing SELECT middle_initial FROM users LIMIT 1...")
        try:
            cur.execute("SELECT middle_initial FROM users LIMIT 1;")
            res = cur.fetchone()
            print(f"Success! Result: {res}")
        except Exception as e:
            print(f"Failed to select middle_initial: {e}")
            conn.rollback()

        print("\nTesting SELECT middle_name FROM users LIMIT 1...")
        try:
            cur.execute("SELECT middle_name FROM users LIMIT 1;")
            res = cur.fetchone()
            print(f"Success! Result: {res}")
        except Exception as e:
            print(f"Failed to select middle_name: {e}")
            conn.rollback()
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    test_query()
