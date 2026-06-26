from .database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        print("Migrating CatererProfile table...")
        commands = [
            "ALTER TABLE caterer_profiles ADD COLUMN default_labor_cost FLOAT DEFAULT 0.0;",
            "ALTER TABLE caterer_profiles ADD COLUMN default_utility_cost FLOAT DEFAULT 0.0;",
            "ALTER TABLE caterer_profiles ADD COLUMN default_transport_cost FLOAT DEFAULT 0.0;",
            "ALTER TABLE caterer_profiles ADD COLUMN default_reservation_type VARCHAR DEFAULT 'fixed';",
            "ALTER TABLE caterer_profiles ADD COLUMN default_reservation_value FLOAT DEFAULT 0.0;"
        ]
        
        for cmd in commands:
            try:
                conn.execute(text(cmd))
                print(f"Executed: {cmd}")
            except Exception as e:
                print(f"Failed (might already exist): {e}")
        
        conn.commit()
        print("Migration complete.")

if __name__ == '__main__':
    migrate()
