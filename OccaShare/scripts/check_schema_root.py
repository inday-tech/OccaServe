import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    res = conn.execute(text("SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name = 'identity_verifications';"))
    for row in res:
        print(f"Column: {row[0]}, Nullable: {row[1]}")
