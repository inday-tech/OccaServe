import sqlite3

def apply_migration(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE portfolios ADD COLUMN is_archived BOOLEAN DEFAULT 0;")
        print(f"Successfully added is_archived to portfolios in {db_name}")
    except sqlite3.OperationalError as e:
        print(f"Migration error in {db_name}: {e}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    apply_migration('app.db')
    apply_migration('occashare.db')
    apply_migration('occaserve.db')
