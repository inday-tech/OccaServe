from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

def repair_data():
    hostname = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "occashare")
    username = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "2004")
    port_id = os.getenv("DB_PORT", "5432")

    SQLALCHEMY_DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as conn:
        print("Repairing menu_items.caterer_id for existing items...")
        try:
            # Associate menu items with caterer_id from their packages
            query = text("""
                UPDATE menu_items 
                SET caterer_id = cp.caterer_id 
                FROM catering_packages cp 
                JOIN package_items pi ON cp.id = pi.package_id 
                WHERE pi.menu_item_id = menu_items.id 
                AND menu_items.caterer_id IS NULL;
            """)
            result = conn.execute(query)
            conn.commit()
            print(f"Successfully updated caterer_id for {result.rowcount} menu items.")
        except Exception as e:
            print(f"Error repairing menu_items: {e}")
            conn.rollback()

if __name__ == "__main__":
    repair_data()
