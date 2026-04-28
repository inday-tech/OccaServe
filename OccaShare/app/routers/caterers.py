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
    
    # Unique views per account — only count once per logged-in user
    if user:
        existing_view = db.query(models.ProfileView).filter(
            models.ProfileView.caterer_id == caterer_id,
            models.ProfileView.viewer_id == user.id
        ).first()
        if not existing_view:
            new_view = models.ProfileView(caterer_id=caterer_id, viewer_id=user.id)
            db.add(new_view)
            caterer.profile_views = (caterer.profile_views or 0) + 1
            db.commit()
    else:
        # Guest views still increment (no account to track)
        caterer.profile_views = (caterer.profile_views or 0) + 1
        db.commit()
    
    # If the user is a logged-in customer, show the dashboard-integrated view
    if user and user.role == "customer":
        return templates.TemplateResponse("customer/caterer_profile_view.html", {
            "request": request, 
            "caterer": caterer,
            "packages": [p for p in caterer.packages if p.is_active and p.status == 'active'],
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
        "nav_page": "caterers"
    })

@router.get("/api/search", response_class=HTMLResponse)
def unified_search_api(request: Request, q: str = "", db: Session = Depends(database.get_db)):
    """Unified deep search across all caterer-related fields with real pricing."""
    from sqlalchemy import or_, func, distinct

    # Subquery for minimum active package price per caterer
    price_sq = db.query(
        models.CateringPackage.caterer_id,
        func.min(models.CateringPackage.price).label("min_price")
    ).filter(
        models.CateringPackage.is_active == True,
        models.CateringPackage.status == 'active'
    ).group_by(models.CateringPackage.caterer_id).subquery()

    query = db.query(
        models.CatererProfile, price_sq.c.min_price
    ).outerjoin(
        price_sq, models.CatererProfile.id == price_sq.c.caterer_id
    )

    if q and q.strip():
        search_term = f"%{q.strip()}%"

        # Subquery: caterer IDs matching via menu item names
        menu_match = db.query(
            distinct(models.MenuItem.caterer_id)
        ).filter(
            models.MenuItem.name.ilike(search_term),
            models.MenuItem.is_archived == False
        ).subquery()

        # Subquery: caterer IDs matching via package name or service_type
        pkg_match = db.query(
            distinct(models.CateringPackage.caterer_id)
        ).filter(
            or_(
                models.CateringPackage.name.ilike(search_term),
                models.CateringPackage.service_type.ilike(search_term)
            ),
            models.CateringPackage.is_active == True
        ).subquery()

        # Main filter: OR across all caterer fields + subquery matches
        query = query.filter(
            or_(
                models.CatererProfile.business_name.ilike(search_term),
                models.CatererProfile.description.ilike(search_term),
                models.CatererProfile.city.ilike(search_term),
                models.CatererProfile.contact_address.ilike(search_term),
                models.CatererProfile.coverage_area.ilike(search_term),
                # PostgreSQL ARRAY search via array_to_string
                func.coalesce(func.array_to_string(models.CatererProfile.event_types, ','), '').ilike(search_term),
                func.coalesce(func.array_to_string(models.CatererProfile.cuisine_types, ','), '').ilike(search_term),
                # Related entity matches
                models.CatererProfile.id.in_(menu_match),
                models.CatererProfile.id.in_(pkg_match),
            )
        )

    results = query.order_by(models.CatererProfile.rating.desc()).all()

    # Attach computed min price to each caterer object
    caterers = []
    for profile, min_p in results:
        profile.min_package_price = min_p or profile.starting_price or 0
        caterers.append(profile)

    return templates.TemplateResponse("caterer/components/caterer_card_grid.html", {
        "request": request,
        "caterers": caterers
    })

@router.get("/api/filter", response_class=HTMLResponse)
def filter_caterers_api(request: Request, type: str = None, q: str = None, location: str = None, db: Session = Depends(database.get_db)):
    """Legacy filter endpoint — redirects to unified search."""
    combined = " ".join(filter(None, [q, location, type]))
    return unified_search_api(request=request, q=combined, db=db)
