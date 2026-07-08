import psycopg2

def apply_migration():
    conn = psycopg2.connect(
        dbname="occashare",
        user="postgres",
        password="2004",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE portfolios ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;")
        print("Successfully added is_archived to portfolios in PostgreSQL")
    except psycopg2.errors.DuplicateColumn:
        print("Column is_archived already exists.")
    except Exception as e:
        print(f"Migration error: {e}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    apply_migration()
