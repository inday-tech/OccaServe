import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def check_columns():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        tables = ['catering_packages', 'menu_items']
        
        for table in tables:
            print(f"\nColumns in {table}:")
            cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}';")
            columns = [row[0] for row in cur.fetchall()]
            for col in columns:
                print(f"- {col}")
                
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_columns()
