from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN dti_url VARCHAR;"))
            print("Added dti_url")
        except Exception as e: print(e)
        
        try:
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN bir_url VARCHAR;"))
            print("Added bir_url")
        except Exception as e: print(e)
        
        try:
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN mayors_permit_url VARCHAR;"))
            print("Added mayors_permit_url")
        except Exception as e: print(e)
        
        try:
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN permit_expiry_date DATE;"))
            print("Added permit_expiry_date")
        except Exception as e: print(e)
        
        try:
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN registration_source VARCHAR DEFAULT 'Website';"))
            print("Added registration_source")
        except Exception as e: print(e)
        
        try:
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN admin_remarks TEXT;"))
            print("Added admin_remarks")
        except Exception as e: print(e)
        
        try:
            conn.execute(text("ALTER TABLE identity_verifications ADD COLUMN document_back_url VARCHAR;"))
            print("Added document_back_url")
        except Exception as e: print(e)
        
        conn.commit()
        print("Done!")

if __name__ == "__main__":
    migrate()
