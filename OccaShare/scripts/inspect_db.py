from sqlalchemy import create_engine, inspect
from app.db.database import SQLALCHEMY_DATABASE_URL

def inspect_db():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    inspector = inspect(engine)
    
    table_name = "identity_verifications"
    if table_name in inspector.get_table_names():
        print(f"Columns in {table_name}:")
        for column in inspector.get_columns(table_name):
            print(f"- {column['name']} ({column['type']})")
    else:
        print(f"Table {table_name} does not exist.")

if __name__ == "__main__":
    inspect_db()
