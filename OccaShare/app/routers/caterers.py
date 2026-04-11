from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..core.templates import templates
from fastapi.responses import HTMLResponse, RedirectResponse
from ..db import database, models, crud
from ..core import security as auth

router = APIRouter(prefix="/caterers", tags=["caterers"])

@router.get("/", response_class=HTMLResponse)
def list_caterers(request: Request, db: Session = Depends(database.get_db)):
    token = request.cookies.get("access_token")
    user = None
    if token:
        try:
            scheme, param = token.split()
            user = auth.verify_token(param, db)
            if user and user.role == "customer":
                return RedirectResponse(url="/customer/marketplace")
        except: pass
    
    caterers = crud.get_caterers(db)
    return templates.TemplateResponse("customer/caterers_list.html", {
        "request": request, 
        "caterers": caterers, 
        "user": user,
        "active_page": "marketplace",
        "nav_page": "caterers"
    })

@router.get("/{caterer_id}", response_class=HTMLResponse)
def get_caterer_profile(request: Request, caterer_id: int, db: Session = Depends(database.get_db)):
    token = request.cookies.get("access_token")
    user = None
    if token:
        try:
            scheme, param = token.split()
            user = auth.verify_token(param, db)
        except: pass

    caterer = crud.get_caterer(db, caterer_id=caterer_id)
    if not caterer:
        raise HTTPException(status_code=404, detail="Caterer not found")
    
    # If the user is a logged-in customer, show the dashboard-integrated view
    if user and user.role == "customer":
        return templates.TemplateResponse("customer/caterer_profile_view.html", {
            "request": request, 
            "caterer": caterer,
            "packages": caterer.packages,
            "gallery_items": caterer.gallery_items,
            "reviews": caterer.reviews,
            "user": user,
            "active_page": "marketplace",
            "nav_page": "caterers"
        })
    
    # Otherwise, show the standalone profile (e.g., for guests or other roles)
    return templates.TemplateResponse("caterer/profile.html", {
        "request": request, 
        "caterer": caterer,
        "packages": caterer.packages,
        "gallery_items": caterer.gallery_items,
        "reviews": caterer.reviews,
        "user": user,
        "nav_page": "caterers"
    })

@router.get("/caterer/{slug}", response_class=HTMLResponse)
def get_caterer_by_slug(request: Request, slug: str, db: Session = Depends(database.get_db)):
    caterer = db.query(models.CatererProfile).filter(models.CatererProfile.slug == slug).first()
    if not caterer:
        # Fallback: check if slug is actually an ID
        if slug.isdigit():
            caterer = crud.get_caterer(db, caterer_id=int(slug))
    
    if not caterer:
        raise HTTPException(status_code=404, detail="Caterer not found")

    token = request.cookies.get("access_token")
    user = None
    if token:
        try:
            scheme, param = token.split()
            user = auth.verify_token(param, db)
        except: pass

    return templates.TemplateResponse("caterer/profile.html", {
        "request": request, 
        "caterer": caterer,
        "packages": caterer.packages,
        "gallery_items": caterer.gallery_items,
        "reviews": caterer.reviews,
        "user": user,
        "nav_page": "caterers"
    })
