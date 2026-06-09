import sqlite3
import os

db_path = r'c:\OccaServe\OccaShare\app\database.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE caterer_profiles ADD COLUMN permit_status VARCHAR DEFAULT 'Pending'")
        print("Column added successfully.")
    except Exception as e:
        print("Error:", e)
    conn.commit()
    conn.close()
else:
    print("Database not found at", db_path)
