from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def check_audit():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 10;"))
        print("Recent Audit Logs:")
        for row in result:
            print(row)
        
        result = conn.execute(text("SELECT * FROM identity_verifications ORDER BY created_at DESC LIMIT 5;"))
        print("\nRecent Identity Verifications:")
        for row in result:
            print(row)

if __name__ == "__main__":
    check_audit()
