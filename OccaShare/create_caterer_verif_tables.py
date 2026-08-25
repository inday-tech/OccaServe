from app.db.database import engine, Base
from app.db.models import CatererVerification, VerificationDocument, VerificationResult, VerificationAuditLog

def create_tables():
    print("Creating caterer verification tables...")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            CatererVerification.__table__,
            VerificationDocument.__table__,
            VerificationResult.__table__,
            VerificationAuditLog.__table__
        ]
    )
    print("Tables created successfully.")

if __name__ == "__main__":
    create_tables()
