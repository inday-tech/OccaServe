from fastapi import APIRouter, Request, Form, Depends
from jose import JWTError, jwt
from fastapi.responses import HTMLResponse
from ..core.templates import templates
from sqlalchemy.orm import Session
from ..db import crud, schemas, database, models
from ..core import security as auth, utils

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(database.get_db)):
    token = request.cookies.get("access_token")
    user = None
    if token and token.startswith("Bearer "):
        token = token.split(" ")[1]
        try:
            payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
            email: str = payload.get("sub")
            if email:
                user = db.query(models.User).filter(models.User.email == email).first()
        except JWTError:
            pass

    # Temporary Schema Sync
    try:
        from sqlalchemy import text
        db.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS event_address TEXT"))
        db.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS id_address TEXT"))
        db.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS current_address TEXT"))
        db.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS verification_status VARCHAR DEFAULT 'pending'"))
        db.execute(text("ALTER TABLE ocr_verification ADD COLUMN IF NOT EXISTS full_name VARCHAR"))
        db.execute(text("ALTER TABLE ocr_verification ADD COLUMN IF NOT EXISTS birthdate DATE"))
        db.execute(text("ALTER TABLE ocr_verification ADD COLUMN IF NOT EXISTS id_address_extracted TEXT"))
        db.execute(text("ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS permit_status VARCHAR DEFAULT 'Pending'"))
        db.execute(text("UPDATE caterer_profiles SET is_verified = TRUE WHERE verification_status = 'Verified'"))
        db.execute(text("UPDATE users SET is_verified = TRUE WHERE id IN (SELECT user_id FROM caterer_profiles WHERE verification_status = 'Verified')"))
        db.commit()
    except Exception as e:
        print(f"[DB SYNC ERROR] {e}")
        db.rollback()

    packages = db.query(models.CateringPackage).filter(models.CateringPackage.is_active == True).limit(3).all()
    caterers = db.query(models.CatererProfile).filter(
        models.CatererProfile.status == 'Published',
        models.CatererProfile.is_verified == True,
        models.CatererProfile.account_status == 'Active'
    ).order_by(models.CatererProfile.rating.desc()).limit(5).all()

    highlighted_reviews = db.query(models.PlatformFeedback).filter(
        models.PlatformFeedback.is_archived == False
    ).order_by(models.PlatformFeedback.created_at.desc()).limit(15).all()

    # Fallback: show highly-rated caterer reviews if no platform feedback is featured yet
    if not highlighted_reviews:
        highlighted_reviews = db.query(models.Review).filter(models.Review.rating >= 4).order_by(models.Review.created_at.desc()).limit(3).all()
    
    # Stats for the "Trust Counter" section
    total_caterers = db.query(models.CatererProfile).filter(
        models.CatererProfile.status == 'Published',
        models.CatererProfile.is_verified == True,
        models.CatererProfile.account_status == 'Active'
    ).count()
    # Count actual events that are paid or completed


    total_events = db.query(models.Booking).filter(models.Booking.status.in_(['paid', 'completed'])).count()
    # Count unique happy hosts (customers)
    total_hosts = db.query(models.User).filter(models.User.role == 'customer', models.User.status == 'active').count()
    
    stats = {
        "caterers": total_caterers,
        "events": total_events,
        "hosts": total_hosts
    }

    config = db.query(models.WebsiteConfig).first()

    return templates.TemplateResponse("index.html", {
        "request": request, 
        "packages": packages,
        "caterers": caterers,
        "highlighted_reviews": highlighted_reviews,
        "user": user,
        "nav_page": "home",
        "stats": stats,
        "config": config
    })



@router.get("/support/help-center", response_class=HTMLResponse)
async def help_center_page(request: Request):
    return templates.TemplateResponse("support/help_center.html", {"request": request})

@router.get("/support/privacy-policy", response_class=HTMLResponse)
async def privacy_policy_page(request: Request):
    return templates.TemplateResponse("support/privacy_policy.html", {"request": request})

@router.get("/support/terms-of-service", response_class=HTMLResponse)
async def terms_of_service_page(request: Request):
    return templates.TemplateResponse("support/terms_of_service.html", {"request": request})


