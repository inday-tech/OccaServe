import os
from sqlalchemy import text
from app.db.database import engine

print('Connecting to database...')
try:
    with engine.connect() as conn:
        conn.execute(text('TRUNCATE TABLE bookings CASCADE;'))
        conn.commit()
        print('Successfully truncated bookings and related tables.')
except Exception as e:
    print(f'Error: {e}')
