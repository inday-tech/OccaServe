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

    packages = db.query(models.CateringPackage).filter(models.CateringPackage.is_active == True).limit(3).all()
    caterers = db.query(models.CatererProfile).order_by(models.CatererProfile.rating.desc()).limit(5).all()

    # Pull highlighted Platform Feedback (testimonials about OccaServe itself)
    highlighted_reviews = db.query(models.PlatformFeedback).filter(
        models.PlatformFeedback.is_highlighted == True,
        models.PlatformFeedback.is_archived == False
    ).order_by(models.PlatformFeedback.created_at.desc()).limit(6).all()

    # Fallback: show highly-rated caterer reviews if no platform feedback is featured yet
    if not highlighted_reviews:
        highlighted_reviews = db.query(models.Review).filter(models.Review.rating >= 4).order_by(models.Review.created_at.desc()).limit(3).all()
    
    # Stats for the "Trust Counter" section
    total_caterers = db.query(models.CatererProfile).count()
    total_packages = db.query(models.CateringPackage).filter(models.CateringPackage.status == 'active').count()
    total_reviews = db.query(models.Review).count()
    
    # Ensuring we have some "impressive" minimums for the design if DB is empty
    stats = {
        "caterers": max(total_caterers, 24),
        "events": max(total_reviews * 3, 120),
        "hosts": max(total_reviews, 85)
    }

    return templates.TemplateResponse("index.html", {
        "request": request, 
        "packages": packages,
        "caterers": caterers,
        "highlighted_reviews": highlighted_reviews,
        "user": user,
        "nav_page": "home",
        "stats": stats
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


