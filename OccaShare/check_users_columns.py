
from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def check():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users';"))
        columns = [row[0] for row in result]
        print("Columns in 'users' table:")
        for col in columns:
            print(f" - {col}")

if __name__ == "__main__":
    check()
