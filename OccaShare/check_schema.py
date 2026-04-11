from sqlalchemy import create_engine, inspect
from app.db.database import SQLALCHEMY_DATABASE_URL

def check_schema():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    inspector = inspect(engine)
    
    tables_to_check = ["catering_packages", "identity_verifications", "caterer_profiles", "availability"]
    
    for table in tables_to_check:
        print(f"\nColumns in '{table}':")
        columns = inspector.get_columns(table)
        for column in columns:
            print(f" - {column['name']} ({column['type']})")

if __name__ == "__main__":
    check_schema()
