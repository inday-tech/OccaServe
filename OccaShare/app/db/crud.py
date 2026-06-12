from sqlalchemy.orm import Session
from . import models, schemas

def get_packages(db: Session):
    return db.query(models.CateringPackage).all()

def get_caterers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.CatererProfile).filter(
        models.CatererProfile.status == 'Published',
        models.CatererProfile.is_verified == True,
        models.CatererProfile.account_status == 'Active'
    ).offset(skip).limit(limit).all()

def get_caterer(db: Session, caterer_id: int):
    return db.query(models.CatererProfile).filter(models.CatererProfile.id == caterer_id).first()

def create_inquiry(db: Session, inquiry: schemas.InquiryCreate):
    db_inquiry = models.Inquiry(**inquiry.dict())
    db.add(db_inquiry)
    db.commit()
    db.refresh(db_inquiry)
    return db_inquiry
