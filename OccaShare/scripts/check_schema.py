import sys
import os
from sqlalchemy import inspect, text

# Add the project root to sys.path to allow importing from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import engine

def check_quotations_schema():
    inspector = inspect(engine)
    if 'quotations' not in inspector.get_table_names():
        print("Table 'quotations' does not exist.")
        return

    print("Columns in 'quotations' table:")
    for column in inspector.get_columns('quotations'):
        print(f"- {column['name']}: {column['type']}")

if __name__ == "__main__":
    check_quotations_schema()
