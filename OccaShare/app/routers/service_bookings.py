import json
import logging
from datetime import datetime, date, timedelta
from typing import Optional

from fastapi import APIRouter, Request, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db import database, models
from app.core import security as auth
from app.routers.bookings import get_current_user_from_session
from app.core.templates import templates

router = APIRouter(prefix="/services", tags=["service_bookings"])
logger = logging.getLogger(__name__)

customer_only = auth.RoleChecker(["customer"])

@router.get("/checkout/{caterer_id}", response_class=HTMLResponse)
async def service_checkout_page(
    request: Request, 
    caterer_id: int, 
    service_id: int,
    db: Session = Depends(database.get_db)
):
    """
    Renders the standalone service checkout wizard.
    """
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/services/checkout/{caterer_id}?service_id={service_id}")
    
    caterer = db.query(models.CatererProfile).filter(
        models.CatererProfile.id == caterer_id, 
        models.CatererProfile.is_verified == True
    ).first()
    
    if not caterer:
        return RedirectResponse(url="/marketplace?error=Caterer+not+found")
        
    service = db.query(models.Service).filter(
        models.Service.id == service_id, 
        models.Service.caterer_id == caterer_id, 
        models.Service.is_archived == False
    ).first()
    
    if not service:
        return RedirectResponse(url=f"/caterers/{caterer_id}?error=Service+not+available")

    return templates.TemplateResponse("customer/booking_wizard/service_checkout.html", {
        "request": request,
        "user": user,
        "caterer": caterer,
        "service": service,
        "today": date.today(),
        "timedelta": timedelta
    })

@router.post("/checkout/draft")
async def service_checkout_draft(
    request: Request,
    caterer_id: int = Form(...),
    service_id: int = Form(...),
    full_name: str = Form(...),
    event_date: str = Form(...),
    start_time: str = Form(...),
    duration: int = Form(...),
    address: Optional[str] = Form(""),
    db: Session = Depends(database.get_db)
):
    """
    Saves a draft service booking while the customer fills out the wizard.
    """
    user = get_current_user_from_session(request, db)
    if not user: return {"success": False, "message": "Unauthorized"}
    
    try:
        service = db.query(models.Service).get(service_id)
        if not service:
            return {"success": False, "message": "Service not found."}

        event_date_obj = date.fromisoformat(event_date)
        start_time_obj = datetime.strptime(start_time, "%H:%M").time()
        
        # Calculate End Time
        # Start time + duration hours
        start_datetime = datetime.combine(event_date_obj, start_time_obj)
        end_datetime = start_datetime + timedelta(hours=duration)
        end_time_obj = end_datetime.time()

        # Pricing Logic based on duration vs base cost
        total_price = service.selling_price * duration if service.unit_type == 'hourly' else service.selling_price
        
        # Determine strict transaction document type based on settings
        doc_type = "service_agreement" if service.requires_agreement else "invoice"
        transaction_type = "contract_track" if service.requires_agreement else "fast_track"

        new_booking = models.Booking(
            user_id=user.id,
            caterer_id=caterer_id,
            event_name=f"Service Request (Draft): {service.name}",
            event_type="Service Booking",
            event_date=event_date_obj,
            event_time=start_time_obj,
            event_end_time=end_time_obj,
            venue_address=address,
            guest_count=1, # Default placeholder for service
            total_amount=total_price,
            total_price=total_price,
            status="draft",
            transaction_type=transaction_type,
            document_type=doc_type
        )
        db.add(new_booking)
        db.flush()

        # Add Service as Menu Item link
        db.add(models.BookingMenuItem(
            booking_id=new_booking.id, 
            service_id=service.id, 
            price=service.selling_price, 
            quantity=1
        ))
        
        db.commit()
        return {"success": True, "booking_id": new_booking.id}
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating service draft: {e}")
        return {"success": False, "message": str(e)}

@router.post("/checkout/submit")
async def service_checkout_submit(
    request: Request,
    booking_id: int = Form(...),
    payment_method: str = Form(...),
    payment_proof: Optional[UploadFile] = File(None),
    signature: Optional[str] = Form(None), # If required
    db: Session = Depends(database.get_db)
):
    """
    Finalizes the service booking submission.
    """
    # Logic for finalizing the booking, verifying proof, processing signature, etc.
    # We will expand this fully in the next steps based on the blueprint.
    pass
