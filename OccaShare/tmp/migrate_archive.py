from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        tables = [
            ("users", "is_archived"),
            ("reviews", "is_archived"),
            ("payouts", "is_archived"),
            ("identity_verifications", "is_archived")
        ]
        
        for table, column in tables:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} BOOLEAN DEFAULT FALSE"))
                conn.commit()
                print(f"Added {column} to {table}")
            except Exception as e:
                print(f"Skipping {table}.{column}: {e}")

if __name__ == "__main__":
    migrate()
