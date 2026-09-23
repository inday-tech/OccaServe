from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional
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
        
    # Check if profile is public, otherwise restrict to owner
    is_verified = (caterer.verification_status == 'Verified') or (caterer.is_verified == True)
    is_public = (caterer.status == 'Published' and is_verified and caterer.account_status == 'Active')
    if not is_public:
        if not user or user.id != caterer.user_id:
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
    
    # Calculate active menu & inventory
    def is_item_active(item):
        if getattr(item, 'is_archived', False):
            return False
        if getattr(item, 'is_hidden', False):
            return False
        status = (getattr(item, 'status', '') or '').lower()
        if status in ['unavailable', 'maintenance', 'draft', 'archived', 'hidden']:
            return False
        return True

    active_menu = [
        m for m in caterer.menu_items
        if is_item_active(m)
        and m.category not in ['Rentals', 'Services', 'Event Styling', 'Event Rental', 'Entertainment', 'Event Coordination', 'Food Cart', 'Equipment Rental', 'Staffing Services', 'Packages']
        and getattr(m, 'usage_type', '') != 'package_only'
    ]
    active_services = [
        s for s in getattr(caterer, 'service_items', [])
        if is_item_active(s) and getattr(s, 'usage_type', 'both') != 'package_only'
    ]
    raw_equipment = db.query(models.Equipment).filter(models.Equipment.caterer_id == caterer.id).all()
    active_equipment = [
        e for e in raw_equipment
        if is_item_active(e) and getattr(e, 'usage_type', 'both') != 'package_only'
    ]
    
    # Ensure legacy rental items from menu_items table are also included
    legacy_equipment = [
        m for m in getattr(caterer, 'menu_items', [])
        if is_item_active(m) and m.category in ['Rentals', 'Equipment Rental', 'Event Rental']
    ]
    for leg in legacy_equipment:
        leg.equipment_type = getattr(leg, 'equipment_type', 'Equipment') or 'Equipment'
        leg.rental_price = getattr(leg, 'rental_price', leg.price)
        leg.unit_type = getattr(leg, 'unit_type', getattr(leg, 'pricing_unit', 'piece')) or 'piece'
        leg.available_qty = getattr(leg, 'available_qty', getattr(leg, 'max_stock_quantity', 1)) or 1
        if leg not in active_equipment:
            active_equipment.append(leg)

    legacy_services = [
        m for m in getattr(caterer, 'menu_items', [])
        if is_item_active(m) and m.category in ['Services', 'Event Styling', 'Entertainment', 'Event Coordination', 'Food Cart', 'Staffing Services']
    ]
    for leg in legacy_services:
        leg.selling_price = getattr(leg, 'selling_price', leg.price)
        leg.unit_type = getattr(leg, 'unit_type', getattr(leg, 'pricing_unit', 'per_event')) or 'per_event'
        leg.max_available = getattr(leg, 'max_available', getattr(leg, 'max_stock_quantity', 1)) or 1
        if leg not in active_services:
            active_services.append(leg)

    active_inventory = active_services + active_equipment

    for item in active_inventory:
        is_equip = (
            hasattr(item, 'rental_price') or 
            hasattr(item, 'equipment_type') or 
            getattr(item, 'equipment_type', None) is not None or 
            item in active_equipment
        )
        item.display_price = getattr(item, 'rental_price', getattr(item, 'selling_price', getattr(item, 'price', 0.0)))
        item.display_type = 'Equipment' if is_equip else 'Service'
        item.display_qty = getattr(item, 'available_qty', getattr(item, 'max_available', getattr(item, 'max_stock_quantity', 1)))
        item.deposit_pct = getattr(item, 'security_deposit_pct', 0)
        item.needs_kyc = getattr(item, 'requires_kyc', False)
        item.min_hours = getattr(item, 'minimum_hours', getattr(item, 'base_duration_hours', None))
        if is_equip and not getattr(item, 'equipment_type', None):
            item.equipment_type = 'Equipment'

    active_packages = [p for p in caterer.packages if p.is_active and p.status == 'active']
    import json
    for p in active_packages:
        raw_inclusions = []
        if p.inclusions:
            if isinstance(p.inclusions, str):
                try:
                    parsed = json.loads(p.inclusions)
                    if isinstance(parsed, list):
                        raw_inclusions = [i for i in parsed if i]
                    elif isinstance(parsed, dict):
                        raw_inclusions = [k for k, v in parsed.items() if v]
                    else:
                        raw_inclusions = [str(parsed)]
                except:
                    raw_inclusions = [i.strip() for i in p.inclusions.split(',') if i.strip()]
            elif isinstance(p.inclusions, list):
                raw_inclusions = [i for i in p.inclusions if i]
            elif isinstance(p.inclusions, dict):
                raw_inclusions = [k for k, v in p.inclusions.items() if v]
        
        flat_list = []
        for inc in raw_inclusions:
            if isinstance(inc, dict):
                name = inc.get('name') or ''
                if name:
                    qty = inc.get('quantity')
                    flat_list.append(f"{name} ({qty})" if qty else name)
            elif isinstance(inc, str) and inc.strip():
                flat_list.append(inc.strip())
        
        if getattr(p, 'linked_inventory', None) and isinstance(p.linked_inventory, list):
            for i in p.linked_inventory:
                if i and i not in flat_list:
                    flat_list.append(i)
        
        p.parsed_inclusions = flat_list

    public_portfolios = [p for p in getattr(caterer, 'portfolios', []) if getattr(p, 'visibility', 'Public') == 'Public' and not getattr(p, 'is_archived', False)]

    db.refresh(caterer)
    response = templates.TemplateResponse("caterer/profile.html", {
        "request": request, 
        "caterer": caterer,
        "packages": active_packages,
        "active_menu": active_menu,
        "active_inventory": active_inventory,
        "active_equipment": active_equipment,
        "active_services": active_services,
        "public_portfolios": public_portfolios,
        "gallery_items": [g for g in caterer.gallery_items if not getattr(g, 'is_archived', False)],
        "reviews": caterer.reviews,
        "user": user,
        "active_page": "caterers",
        "nav_page": "caterers"
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

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

    # Check if profile is public, otherwise restrict to owner
    is_verified = (caterer.verification_status == 'Verified') or (caterer.is_verified == True)
    is_public = (caterer.status == 'Published' and is_verified and caterer.account_status == 'Active')
    if not is_public:
        if not user or user.id != caterer.user_id:
            raise HTTPException(status_code=404, detail="Caterer not found")

    def is_item_active(item):
        if getattr(item, 'is_archived', False):
            return False
        if getattr(item, 'is_hidden', False):
            return False
        status = (getattr(item, 'status', '') or '').lower()
        if status in ['unavailable', 'maintenance', 'draft', 'archived', 'hidden']:
            return False
        return True

    active_packages = [p for p in caterer.packages if p.is_active and p.status == 'active']
    import json
    for p in active_packages:
        raw_inclusions = []
        if p.inclusions:
            if isinstance(p.inclusions, str):
                try:
                    parsed = json.loads(p.inclusions)
                    if isinstance(parsed, list):
                        raw_inclusions = [i for i in parsed if i]
                    elif isinstance(parsed, dict):
                        raw_inclusions = [k for k, v in parsed.items() if v]
                    else:
                        raw_inclusions = [str(parsed)]
                except:
                    raw_inclusions = [i.strip() for i in p.inclusions.split(',') if i.strip()]
            elif isinstance(p.inclusions, list):
                raw_inclusions = [i for i in p.inclusions if i]
            elif isinstance(p.inclusions, dict):
                raw_inclusions = [k for k, v in p.inclusions.items() if v]
        
        flat_list = []
        for inc in raw_inclusions:
            if isinstance(inc, dict):
                name = inc.get('name') or ''
                if name:
                    qty = inc.get('quantity')
                    flat_list.append(f"{name} ({qty})" if qty else name)
            elif isinstance(inc, str) and inc.strip():
                flat_list.append(inc.strip())
        
        if getattr(p, 'linked_inventory', None) and isinstance(p.linked_inventory, list):
            for i in p.linked_inventory:
                if i and i not in flat_list:
                    flat_list.append(i)
        
        p.parsed_inclusions = flat_list

    active_menu = [
        m for m in caterer.menu_items
        if is_item_active(m)
        and m.category not in ['Rentals', 'Services', 'Event Styling', 'Event Rental', 'Entertainment', 'Event Coordination', 'Food Cart', 'Equipment Rental', 'Staffing Services', 'Packages']
        and getattr(m, 'usage_type', '') != 'package_only'
    ]
    active_services = [
        s for s in getattr(caterer, 'service_items', [])
        if is_item_active(s) and getattr(s, 'usage_type', 'both') != 'package_only'
    ]
    raw_equipment = db.query(models.Equipment).filter(models.Equipment.caterer_id == caterer.id).all()
    active_equipment = [
        e for e in raw_equipment
        if is_item_active(e) and getattr(e, 'usage_type', 'both') != 'package_only'
    ]
    
    legacy_equipment = [
        m for m in getattr(caterer, 'menu_items', [])
        if is_item_active(m) and m.category in ['Rentals', 'Equipment Rental', 'Event Rental']
    ]
    for leg in legacy_equipment:
        leg.equipment_type = getattr(leg, 'equipment_type', 'Equipment') or 'Equipment'
        leg.rental_price = getattr(leg, 'rental_price', leg.price)
        leg.unit_type = getattr(leg, 'unit_type', getattr(leg, 'pricing_unit', 'piece')) or 'piece'
        leg.available_qty = getattr(leg, 'available_qty', getattr(leg, 'max_stock_quantity', 1)) or 1
        if leg not in active_equipment:
            active_equipment.append(leg)

    legacy_services = [
        m for m in getattr(caterer, 'menu_items', [])
        if is_item_active(m) and m.category in ['Services', 'Event Styling', 'Entertainment', 'Event Coordination', 'Food Cart', 'Staffing Services']
    ]
    for leg in legacy_services:
        leg.selling_price = getattr(leg, 'selling_price', leg.price)
        leg.unit_type = getattr(leg, 'unit_type', getattr(leg, 'pricing_unit', 'per_event')) or 'per_event'
        leg.max_available = getattr(leg, 'max_available', getattr(leg, 'max_stock_quantity', 1)) or 1
        if leg not in active_services:
            active_services.append(leg)

    active_inventory = active_services + active_equipment

    for item in active_inventory:
        is_equip = (
            hasattr(item, 'rental_price') or 
            hasattr(item, 'equipment_type') or 
            getattr(item, 'equipment_type', None) is not None or 
            item in active_equipment
        )
        item.display_price = getattr(item, 'rental_price', getattr(item, 'selling_price', getattr(item, 'price', 0.0)))
        item.display_type = 'Equipment' if is_equip else 'Service'
        item.display_qty = getattr(item, 'available_qty', getattr(item, 'max_available', getattr(item, 'max_stock_quantity', 1)))
        item.deposit_pct = getattr(item, 'security_deposit_pct', 0)
        item.needs_kyc = getattr(item, 'requires_kyc', False)
        item.min_hours = getattr(item, 'minimum_hours', getattr(item, 'base_duration_hours', None))
        if is_equip and not getattr(item, 'equipment_type', None):
            item.equipment_type = 'Equipment'

    public_portfolios = [p for p in getattr(caterer, 'portfolios', []) if getattr(p, 'visibility', 'Public') == 'Public' and not getattr(p, 'is_archived', False)]

    db.refresh(caterer)
    response = templates.TemplateResponse("caterer/profile.html", {
        "request": request, 
        "caterer": caterer,
        "packages": active_packages,
        "active_menu": active_menu,
        "active_inventory": active_inventory,
        "active_equipment": active_equipment,
        "active_services": active_services,
        "public_portfolios": public_portfolios,
        "gallery_items": [g for g in caterer.gallery_items if not getattr(g, 'is_archived', False)],
        "reviews": caterer.reviews,
        "user": user,
        "active_page": "caterers",
        "nav_page": "caterers"
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@router.get("/api/search", response_class=HTMLResponse)
def unified_search_api(request: Request, q: str = "", lat: Optional[float] = None, lon: Optional[float] = None, db: Session = Depends(database.get_db)):
    """Unified deep search across all caterer-related fields with proximity sorting."""
    from sqlalchemy import or_, func, distinct, text, literal_column

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
    ).filter(
        models.CatererProfile.status == 'Published',
        models.CatererProfile.verification_status == 'Verified',
        models.CatererProfile.account_status == 'Active'
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
        conditions = [
            models.CatererProfile.business_name.ilike(search_term),
            models.CatererProfile.description.ilike(search_term),
            models.CatererProfile.city.ilike(search_term),
            models.CatererProfile.contact_address.ilike(search_term),
            models.CatererProfile.coverage_area.ilike(search_term),
            func.coalesce(func.array_to_string(models.CatererProfile.event_types, ','), '').ilike(search_term),
            func.coalesce(func.array_to_string(models.CatererProfile.cuisine_types, ','), '').ilike(search_term),
            models.CatererProfile.id.in_(menu_match),
            models.CatererProfile.id.in_(pkg_match),
        ]

        if "multi-cuisine" in q.lower() or "international" in q.lower() or "fusion" in q.lower() or "multi" in q.lower():
            conditions.append(func.array_length(models.CatererProfile.cuisine_types, 1) >= 3)

        query = query.filter(or_(*conditions))

    # Proximity sorting if lat/lon provided
    if lat is not None and lon is not None:
        # Haversine formula in SQL
        distance_query = text("""
            CASE 
                WHEN latitude IS NULL OR longitude IS NULL THEN 99999
                ELSE (
                    6371 * 2 * ASIN(SQRT(
                        POWER(SIN((radians(latitude) - radians(:lat)) / 2), 2) +
                        COS(radians(:lat)) * COS(radians(latitude)) *
                        POWER(SIN((radians(longitude) - radians(:lon)) / 2), 2)
                    ))
                )
            END
        """).bindparams(lat=lat, lon=lon)
        
        query = query.add_columns(distance_query).order_by(distance_query)
    else:
        query = query.add_columns(literal_column("NULL")).order_by(models.CatererProfile.rating.desc())

    results = query.all()

    # Attach computed min price to each caterer object
    caterers = []
    for row in results:
        profile = row[0]
        min_p = row[1]
        dist = row[2]
        profile.min_package_price = min_p or profile.starting_price or 0
        profile.distance_km = dist
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
