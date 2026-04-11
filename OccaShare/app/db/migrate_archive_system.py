from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print(f"Connecting to database...")

        # Add is_archived to menu_items
        print("Adding 'is_archived' to 'menu_items'...")
        try:
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;"))
            conn.commit()
            print("Successfully added 'is_archived' to 'menu_items'.")
        except Exception as e:
            print(f"menu_items migration skipped or failed: {e}")
            conn.rollback()

        # Add is_archived to caterer_gallery
        print("Adding 'is_archived' to 'caterer_gallery'...")
        try:
            conn.execute(text("ALTER TABLE caterer_gallery ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;"))
            conn.commit()
            print("Successfully added 'is_archived' to 'caterer_gallery'.")
        except Exception as e:
            print(f"caterer_gallery migration skipped or failed: {e}")
            conn.rollback()

        # Add is_archived to bookings
        print("Adding 'is_archived' to 'bookings'...")
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;"))
            conn.commit()
            print("Successfully added 'is_archived' to 'bookings'.")
        except Exception as e:
            print(f"bookings migration skipped or failed: {e}")
            conn.rollback()

    print("Migration attempt complete!")

if __name__ == "__main__":
    migrate()
