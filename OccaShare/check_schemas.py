import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    hostname = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "occashare")
    username = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "2004")
    port_id = os.getenv("DB_PORT", "5432")
    DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"

def check_schemas():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_name = 'users';")
        rows = cur.fetchall()
        print("Schema/Table pairs found for 'users':")
        for row in rows:
            print(f"- {row[0]}.{row[1]}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schemas()
