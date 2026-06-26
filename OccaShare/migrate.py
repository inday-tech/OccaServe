import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
hostname = os.getenv("DB_HOST", "localhost")
database = os.getenv("DB_NAME", "occashare")
username = os.getenv("DB_USER", "postgres")
pwd = os.getenv("DB_PASSWORD", "2004")
port_id = os.getenv("DB_PORT", "5432")

conn = psycopg2.connect(
    host=hostname,
    database=database,
    user=username,
    password=pwd,
    port=port_id
)
cur = conn.cursor()
try:
    cur.execute("ALTER TABLE equipment ADD COLUMN usage_type VARCHAR DEFAULT 'both';")
    print("Added usage_type to equipment")
except Exception as e:
    print(e)
    conn.rollback()

try:
    cur.execute("ALTER TABLE services ADD COLUMN usage_type VARCHAR DEFAULT 'both';")
    print("Added usage_type to services")
except Exception as e:
    print(e)
    conn.rollback()

conn.commit()
cur.close()
conn.close()
