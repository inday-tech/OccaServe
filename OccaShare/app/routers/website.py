from fastapi import APIRouter, Request, Form, Depends
from jose import JWTError, jwt
from fastapi.responses import HTMLResponse, JSONResponse
from ..core.templates import templates
from sqlalchemy.orm import Session
from ..db import crud, schemas, database, models
from ..core import security as auth, utils
import logging

logger = logging.getLogger(__name__)

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

    packages = []
    caterers = []
    highlighted_reviews = []
    stats = {"caterers": 0, "events": 0, "hosts": 0}
    db_error = None

    try:
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
        total_caterers = db.query(models.CatererProfile).filter(models.CatererProfile.is_verified == True).count()
        # Count actual events that are paid or completed
        total_events = db.query(models.Booking).filter(models.Booking.status.in_(['paid', 'completed'])).count()
        # Count unique happy hosts (customers)
        total_hosts = db.query(models.User).filter(models.User.role == 'customer', models.User.status == 'active').count()

        stats = {
            "caterers": total_caterers,
            "events": total_events,
            "hosts": total_hosts
        }
    except Exception as e:
        logger.error(f"Database error on root endpoint: {e}", exc_info=True)
        db_error = str(e)

    if db_error:
        # Return a minimal JSON response so the site doesn't 502 — the error
        # will appear in Railway logs and help diagnose the root cause.
        return JSONResponse(
            status_code=200,
            content={
                "status": "degraded",
                "message": "The site is up but encountered a database error. Please try again shortly.",
                "error": db_error,
            },
        )

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


