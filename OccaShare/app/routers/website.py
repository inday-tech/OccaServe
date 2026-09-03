from fastapi import APIRouter, Request, Form, Depends
from jose import JWTError, jwt
from fastapi.responses import HTMLResponse
from ..core.templates import templates
from sqlalchemy.orm import Session
from sqlalchemy import func
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

    # NOTE: Schema sync (ALTER TABLE) has been moved to app startup (main.py).
    # Running DDL per-request holds AccessExclusiveLock on tables and causes deadlocks.

    packages = db.query(models.CateringPackage).filter(models.CateringPackage.is_active == True).limit(3).all()
    caterers = db.query(models.CatererProfile).filter(
        models.CatererProfile.status == 'Published',
        models.CatererProfile.verification_status == 'Verified',
        models.CatererProfile.account_status == 'Active'
    ).order_by(models.CatererProfile.rating.desc()).limit(5).all()

    highlighted_reviews = db.query(models.PlatformFeedback).filter(
        models.PlatformFeedback.is_archived == False
    ).order_by(models.PlatformFeedback.created_at.desc()).limit(15).all()

    # Fallback: show highly-rated caterer reviews if no platform feedback is featured yet
    if not highlighted_reviews:
        highlighted_reviews = db.query(models.Review).filter(models.Review.rating >= 4).order_by(models.Review.created_at.desc()).limit(3).all()

    # Stats for the "Trust Counter" section
    # Use func.count(Model.id) instead of ORM .count() to avoid the full-column subquery
    # that .count() generates — it selects all 60+ columns and holds locks longer.
    try:
        total_caterers = db.query(func.count(models.CatererProfile.id)).filter(
            models.CatererProfile.status == 'Published',
            models.CatererProfile.verification_status == 'Verified',
            models.CatererProfile.account_status == 'Active'
        ).scalar() or 0

        total_events = db.query(func.count(models.Booking.id)).filter(
            models.Booking.status.in_(['paid', 'completed'])
        ).scalar() or 0

        total_hosts = db.query(func.count(models.User.id)).filter(
            models.User.role == 'customer',
            models.User.status == 'active'
        ).scalar() or 0
    except Exception as e:
        print(f"[STATS ERROR] Failed to load homepage stats: {e}")
        db.rollback()
        total_caterers = total_events = total_hosts = 0

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
