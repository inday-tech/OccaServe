from sqlalchemy import create_engine, inspect
from app.database import SQLALCHEMY_DATABASE_URL

def check_schema():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    inspector = inspect(engine)
    columns = inspector.get_columns('bookings')
    print("Columns in 'bookings' table:")
    for column in columns:
        print(f"- {column['name']} ({column['type']})")

if __name__ == "__main__":
    check_schema()
