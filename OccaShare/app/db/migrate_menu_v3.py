import sys
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.db.database import SQLALCHEMY_DATABASE_URL, engine

def migrate_v3():
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    print("Starting MenuItem V3 Migration (Single Serving Style)...")
    
    with engine.begin() as conn:
        print("Checking for serving_style column...")
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='menu_items' AND column_name='serving_style';
        """))
        if not result.fetchone():
            print("Adding serving_style column...")
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN serving_style VARCHAR;"))
        else:
            print("serving_style column already exists.")

    with SessionLocal() as session:
        # Transfer data if serving_styles exists
        result = session.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='menu_items' AND column_name='serving_styles';
        """))
        if result.fetchone():
            print("Migrating data from serving_styles array to serving_style string...")
            # Take the first element of the array if it has one
            session.execute(text("""
                UPDATE menu_items 
                SET serving_style = serving_styles[1] 
                WHERE serving_styles IS NOT NULL AND array_length(serving_styles, 1) > 0;
            """))
            session.commit()
            print("Data migrated.")
            
            # Drop the array column to clean up
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE menu_items DROP COLUMN serving_styles;"))
                print("Dropped old serving_styles column.")
                
    engine.dispose()
    print("Migration V3 Complete!")

if __name__ == "__main__":
    migrate_v3()
