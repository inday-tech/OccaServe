import os
import sys
from sqlalchemy import create_engine, inspect

# Assuming the app.db.database has the connection string
try:
    from app.db.database import engine
except Exception as e:
    print(f"Error importing engine: {e}")
    sys.exit(1)

def check_schema():
    inspector = inspect(engine)
    if 'identity_verifications' in inspector.get_table_names():
        print("identity_verifications exists.")
        columns = inspector.get_columns('identity_verifications')
        for col in columns:
            print(f"- {col['name']} ({col['type']})")
    else:
        print("identity_verifications does NOT exist.")

if __name__ == '__main__':
    check_schema()
