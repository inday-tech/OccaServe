from app.db import database
from sqlalchemy import text
with database.engine.connect() as conn:
    conn.execute(text('ALTER TABLE services ADD COLUMN IF NOT EXISTS base_duration_hours INTEGER DEFAULT 3;'))
    conn.commit()
