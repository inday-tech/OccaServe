import psycopg2
import os

# Connection parameters - ensuring they match what was likely used before or defaults
hostname = "localhost"
database = "occashare"
username = "postgres"
pwd = "1425" # Preserved from original file
port_id = 5432

def init_db():
    conn = None
    try:
        # 1. Connect to PostgreSQL
        print(f"Connecting to database '{database}' at {hostname}...")
        conn = psycopg2.connect(
            host=hostname,
            dbname=database,
            user=username,
            password=pwd,
            port=port_id
        )
        conn.autocommit = True
        cursor = conn.cursor()
        print("Connected successfully!")

        # 2. Read schema.sql
        print("Reading schema.sql...")
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        # 3. Execute Schema
        print("Executing schema...")
        cursor.execute(schema_sql)
        print("Schema executed successfully! Tables created/updated.")
        
        cursor.close()
        conn.close()
        print("Done.")

    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.close()

if __name__ == "__main__":
    init_db()
