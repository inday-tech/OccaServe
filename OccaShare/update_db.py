
import sqlite3
import os

db_path = r'c:\OccaServe\OccaShare\occashare.db'

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(identity_verifications)")
        columns = [column[1] for column in cursor.fetchall()]
        
        needed_columns = [
            ('match_score', 'FLOAT DEFAULT 0.0'),
            ('face_detected', 'BOOLEAN DEFAULT 0'),
            ('id_detected', 'BOOLEAN DEFAULT 0')
        ]
        
        for col_name, col_type in needed_columns:
            if col_name not in columns:
                print(f"Adding column {col_name}...")
                cursor.execute(f"ALTER TABLE identity_verifications ADD COLUMN {col_name} {col_type}")
            else:
                print(f"Column {col_name} already exists.")
        
        conn.commit()
        conn.close()
        print("Database schema updated successfully.")
    except Exception as e:
        print(f"Error updating database: {e}")
