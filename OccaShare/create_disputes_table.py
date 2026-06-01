import os
from app.db.database import engine
from app.db.models import Base

def main():
    Base.metadata.create_all(bind=engine)
    print("Database tables synchronized (DisputeReport added).")

if __name__ == "__main__":
    main()
