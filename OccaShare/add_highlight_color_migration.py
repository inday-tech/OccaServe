from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Checking for 'highlight_color' in 'caterer_profiles'...")
        col_name = "highlight_color"
        col_type = "VARCHAR DEFAULT '#48BB78'"
        
        try:
            # Check if column exists first to avoid errors
            result = conn.execute(text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='caterer_profiles' AND column_name='{col_name}';
            """))
            if not result.fetchone():
                print(f"Adding column '{col_name}'...")
                conn.execute(text(f"ALTER TABLE caterer_profiles ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Successfully added '{col_name}'.")
            else:
                print(f"Column '{col_name}' already exists.")
        except Exception as e:
            print(f"Error handling '{col_name}': {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
