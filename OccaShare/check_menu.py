import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from app.db.database import SessionLocal
from app.db import models

db = SessionLocal()
menu_items = db.query(models.MenuItem).filter(models.MenuItem.id.in_([22, 34, 30, 26, 20, 27])).all()
for m in menu_items:
    print(f"MenuItem {m.id}: {m.name}, price={m.price}")
