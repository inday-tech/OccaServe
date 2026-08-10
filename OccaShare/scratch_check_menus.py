import asyncio
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.db.database import SQLALCHEMY_DATABASE_URL
from app.db import models

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_menus():
    db = SessionLocal()
    menus = db.query(models.MenuItem).order_by(models.MenuItem.id.desc()).limit(5).all()
    for m in menus:
        print(f"ID: {m.id}, Name: {m.name}, Serving Style: {m.serving_style}, Upgrade Fee: {m.upgrade_fee}")
    db.close()

if __name__ == "__main__":
    check_menus()
