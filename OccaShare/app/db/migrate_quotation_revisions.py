from app.db.database import engine
from app.db.models import QuotationRevision


def migrate():
    QuotationRevision.__table__.create(bind=engine, checkfirst=True)
    print("Quotation revision history table is ready.")


if __name__ == "__main__":
    migrate()
