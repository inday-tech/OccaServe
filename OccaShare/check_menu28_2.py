import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))
from app.db.database import SessionLocal
from app.db import models
db = SessionLocal()
item = db.query(models.MenuItem).get(28)
print(f"MenuItem 28: portion_pricing={item.portion_pricing}, weight_pricing={item.weight_pricing}, sizes={item.sizes}")
