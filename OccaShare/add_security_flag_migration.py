from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Adding 'security_flag' column to 'users' table...")
        try:
            # First check if it exists to avoid errors
            check_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'security_flag';")
            result = conn.execute(check_sql).fetchone()
            
            if not result:
                conn.execute(text("ALTER TABLE users ADD COLUMN security_flag BOOLEAN DEFAULT FALSE;"))
                conn.commit()
                print("Successfully added 'security_flag'.")
            else:
                print("'security_flag' already exists.")
        except Exception as e:
            print(f"Error adding 'security_flag': {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
