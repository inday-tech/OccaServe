from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import sys
import os

# Need to append the root directory to sys.path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.db.database import SQLALCHEMY_DATABASE_URL
from app.db.models import Base

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as conn:
        print("Connected to database")
        
        # 1. Add to caterer_profiles
        try:
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN outstanding_balance DOUBLE PRECISION DEFAULT 0.0"))
            print("Added outstanding_balance")
        except Exception as e:
            print("outstanding_balance might already exist:", e)
            
        try:
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN commission_rate DOUBLE PRECISION DEFAULT 0.05"))
            print("Added commission_rate")
        except Exception as e:
            print("commission_rate might already exist:", e)
            
        # 2. Add to bookings
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN commission_calculated BOOLEAN DEFAULT FALSE"))
            print("Added commission_calculated")
        except Exception as e:
            print("commission_calculated might already exist:", e)
            
        conn.commit()
    
    # 3. Create new tables
    Base.metadata.create_all(bind=engine)
    print("Ensured all tables are created (including billing_invoices)")

if __name__ == '__main__':
    migrate()
