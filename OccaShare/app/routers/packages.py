from fastapi import APIRouter, Depends, HTTPException, Request, Form
from sqlalchemy.orm import Session
from ..core.templates import templates
from fastapi.responses import HTMLResponse, RedirectResponse
from ..db import database, models
from ..core import security as auth
from typing import Optional

router = APIRouter(prefix="/packages", tags=["packages"])

def get_current_user_from_session(request: Request, db: Session):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        scheme, param = token.split()
        user = auth.verify_token(param, db)
        return user
    except:
        return None

@router.get("/{package_id}", response_class=HTMLResponse)
async def get_package_details(
    package_id: int, 
    request: Request, 
    db: Session = Depends(database.get_db)
):
    package = db.query(models.CateringPackage).get(package_id)
    if not package or not package.is_active:
        raise HTTPException(status_code=404, detail="Package not found")
    
    user = get_current_user_from_session(request, db)
    
    # Categorise menu items
    categorised_menu = {}
    for item in package.menu_items:
        if not item.is_addon:
            cat = item.category or "Others"
            if cat not in categorised_menu:
                categorised_menu[cat] = []
            categorised_menu[cat].append(item)
    
    addons = [item for item in package.menu_items if item.is_addon]
    
    return templates.TemplateResponse("customer/package_details.html", {
        "request": request,
        "package": package,
        "categorised_menu": categorised_menu,
        "addons": addons,
        "user": user
    })

@router.get("/api/check-availability")
async def check_availability(
    caterer_id: int, 
    date_str: str, 
    db: Session = Depends(database.get_db)
):
    from datetime import datetime
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return {"available": False, "error": "Invalid date format"}

    # Check blocked dates
    blocked = db.query(models.Availability).filter(
        models.Availability.caterer_id == caterer_id,
        models.Availability.date == target_date,
        models.Availability.is_available == False
    ).first()
    
    if blocked:
        return {"available": False, "reason": blocked.reason or "Fully Booked"}
    
    # Optional: check if number of bookings on that day exceeds caterer capacity
    # For now, let's keep it simple: if not blocked, it's available.
    return {"available": True}
