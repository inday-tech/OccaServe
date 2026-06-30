import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))
from app.db.database import SessionLocal
from app.db import models
db = SessionLocal()
item = db.query(models.MenuItem).get(28)
if item:
    print(f"MenuItem 28: {item.name}, price={item.price}")
else:
    print("MenuItem 28 not found")
