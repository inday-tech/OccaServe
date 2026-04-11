from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Adding detailed branding columns to 'caterer_profiles'...")
        branding_columns = [
            ("primary_color", "VARCHAR DEFAULT '#2D3748'"),
            ("secondary_color", "VARCHAR DEFAULT '#4A5568'"),
            ("accent_color", "VARCHAR DEFAULT '#48BB78'"),
            ("font_family", "VARCHAR DEFAULT 'Inter'"),
            ("border_radius", "INTEGER DEFAULT 12"),
            ("sidebar_mode", "VARCHAR DEFAULT 'full'"),
            ("show_platform_logo", "BOOLEAN DEFAULT TRUE")
        ]
        
        for col_name, col_type in branding_columns:
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
