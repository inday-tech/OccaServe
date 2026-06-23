import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database.db")

def migrate():
    print(f"Connecting to database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Create portfolios table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caterer_id INTEGER NOT NULL,
                booking_id INTEGER,
                title VARCHAR NOT NULL,
                event_type VARCHAR NOT NULL,
                description TEXT NOT NULL,
                highlights VARCHAR,
                location VARCHAR,
                event_date DATE,
                visibility VARCHAR DEFAULT 'Public',
                is_featured BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (caterer_id) REFERENCES caterer_profiles (id) ON DELETE CASCADE,
                FOREIGN KEY (booking_id) REFERENCES bookings (id) ON DELETE SET NULL
            )
        """)
        print("Created portfolios table.")

        # Create portfolio_images table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL,
                image_url VARCHAR NOT NULL,
                is_cover BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (portfolio_id) REFERENCES portfolios (id) ON DELETE CASCADE
            )
        """)
        print("Created portfolio_images table.")

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_portfolios_id ON portfolios(id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_portfolio_images_id ON portfolio_images(id);")
        print("Created indexes.")

        conn.commit()
        print("Migration successful.")
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
