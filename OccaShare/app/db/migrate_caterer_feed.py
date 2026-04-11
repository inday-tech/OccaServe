import sqlite3
import os

# Database Path
DB_PATH = "occaserve.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Creating caterer_posts table...")
    
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS caterer_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caterer_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                post_type TEXT DEFAULT 'general',
                image_url TEXT,
                is_public BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (caterer_id) REFERENCES caterer_profiles(id)
            )
        ''')
        
        # Add index for faster feed loading
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_caterer_posts_caterer_id ON caterer_posts(caterer_id)')
        
        conn.commit()
        print("Migration completed successfully.")
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
