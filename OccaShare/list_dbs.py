import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    hostname = os.getenv("DB_HOST", "localhost")
    database = "postgres" # Connect to default postgres DB to list others
    username = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "2004")
    port_id = os.getenv("DB_PORT", "5432")
    DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"

def list_dbs():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        dbs = [row[0] for row in cur.fetchall()]
        print(f"Available databases: {dbs}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_dbs()
