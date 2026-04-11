from sqlalchemy import create_engine, text
from app.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Adding remaining missing columns...")
        
        # Add liveness_verified
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN liveness_verified BOOLEAN DEFAULT FALSE;"))
            conn.commit()
            print("Added column: liveness_verified")
        except Exception as e:
            print(f"Column liveness_verified might already exist or error: {e}")
            
        print("Final verification complete!")

if __name__ == "__main__":
    migrate()
