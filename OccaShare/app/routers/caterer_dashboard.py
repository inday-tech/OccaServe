from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, UploadFile, File, Body, BackgroundTasks
from typing import Optional, List
from datetime import datetime, date, timedelta
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from ..core.templates import templates
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..db import database, models, schemas
from ..core import security as auth
import json
import os
import shutil
import uuid
from ..services.realtime import manager
from ..services.payment_verification import payment_verification_service
from ..services.notification import NotificationService

router = APIRouter(prefix="/caterer", tags=["caterer"])

UPLOAD_DIR = "app/static/uploads/caterer"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Standard dependency for caterer access
caterer_only = auth.RoleChecker(["caterer"])


def process_base64_image(content_bytes: bytes, max_size=(600, 600), quality=75) -> str:
    """Compresses image and returns a base64 Data URI."""
    import io
    import base64
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(content_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=quality)
        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        return f"data:image/webp;base64,{b64}"
    except Exception:
        # Fallback to direct base64 if not an image
        b64 = base64.b64encode(content_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{b64}"

def create_default_booking_tasks(db: Session, booking_id: int):
    # Idempotency check: Don't add if tasks already exist
    existing_count = db.query(models.BookingTask).filter(models.BookingTask.booking_id == booking_id).count()
    if existing_count > 0:
        return

    default_tasks = [
        "Ingredient Sourcing & Procurement",
        "Kitchen Preparation & Prep-work",
        "Equipment & Logistics Loading",
        "On-site Setup & Table Management",
        "Service Execution & Food Serving",
        "Post-event Cleanup & Packing"
    ]
    for title in default_tasks:
        db.add(models.BookingTask(booking_id=booking_id, title=title))


@router.post("/platform-feedback")
async def submit_platform_feedback_caterer(
    rating: int = Form(...),
    comment: str = Form(...),
    attachment_base64: str = Form(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    # Prevent duplicate submissions
    existing_fb = db.query(models.PlatformFeedback).filter_by(user_id=user.id).first()
    if existing_fb:
        error_msg = "You have already submitted feedback. Thank you!"
        return RedirectResponse(url="/caterer/dashboard?error_msg=" + error_msg, status_code=303)

    if rating < 1 or rating > 5:
        return RedirectResponse(url="/caterer/dashboard?error_msg=Invalid+rating", status_code=303)
    if not comment or len(comment.strip()) < 10:
        return RedirectResponse(url="/caterer/dashboard?error_msg=Feedback+too+short", status_code=303)

    fb = models.PlatformFeedback(
        user_id=user.id,
        rating=rating,
        comment=comment.strip(),
        attachment_base64=attachment_base64,
        role="caterer"
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)

    # Broadcast real-time update to all connected admins
    await manager.broadcast_to_role("admin", {
        "type": "new_platform_feedback",
        "id": fb.id,
        "rating": fb.rating,
        "comment": fb.comment,
        "role": "caterer",
        "user_name": (user.caterer_profile.business_name if user.caterer_profile else None) or f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
        "user_email": user.email,
        "created_at": fb.created_at.strftime('%b %d, %Y') if fb.created_at else 'Just now'
    })

    return RedirectResponse(url="/caterer/dashboard?success_msg=Thank+you+for+your+feedback!", status_code=303)

@router.post("/api/validate-package-name")
async def validate_package_name(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    data = await request.json()
    name = data.get("name", "").strip()
    exclude_id = data.get("exclude_id")
    
    if not name:
        return {"exists": False}

    query = db.query(models.CateringPackage).filter(
        models.CateringPackage.caterer_id == user.caterer_profile.id,
        func.lower(models.CateringPackage.name) == name.lower(),
        models.CateringPackage.status != "archived"
    )
    
    if exclude_id:
        query = query.filter(models.CateringPackage.id != int(exclude_id))
        
    exists = query.first() is not None
    return {"exists": exists}

@router.post("/api/validate-dish-name")
async def validate_dish_name(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    data = await request.json()
    name = data.get("name", "").strip()
    exclude_id = data.get("exclude_id")
    
    if not name:
        return {"exists": False}

    query = db.query(models.MenuItem).filter(
        models.MenuItem.caterer_id == user.caterer_profile.id,
        func.lower(models.MenuItem.name) == name.lower(),
        models.MenuItem.is_archived == False
    )
    
    if exclude_id:
        query = query.filter(models.MenuItem.id != int(exclude_id))
        
    exists = query.first() is not None
    return {"exists": exists}

class DeliveryZoneSchema(BaseModel):
    province: str
    city_municipality: str
    is_manual_quote: bool = False
    fee: float = 0.0

@router.post("/api/delivery-zones")
async def add_delivery_zone(
    zone: DeliveryZoneSchema,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Check for duplicate zone
    existing = db.query(models.DeliveryZone).filter(
        models.DeliveryZone.caterer_id == profile.id,
        models.DeliveryZone.province == zone.province,
        models.DeliveryZone.city_municipality == zone.city_municipality
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Delivery zone for this municipality already exists")

    new_zone = models.DeliveryZone(
        caterer_id=profile.id,
        province=zone.province,
        city_municipality=zone.city_municipality,
        fee=zone.fee if not zone.is_manual_quote else 0.0,
        is_manual_quote=zone.is_manual_quote
    )
    db.add(new_zone)
    db.commit()
    return {"status": "success", "message": "Delivery zone added"}

@router.delete("/api/delivery-zones/{zone_id}")
async def delete_delivery_zone(
    zone_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    zone = db.query(models.DeliveryZone).filter(
        models.DeliveryZone.id == zone_id,
        models.DeliveryZone.caterer_id == profile.id
    ).first()
    
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
        
    db.delete(zone)
    db.commit()
    return {"status": "success", "message": "Delivery zone deleted"}

class DeliveryZoneUpdateSchema(BaseModel):
    is_manual_quote: bool = False
    fee: float = 0.0

@router.put("/api/delivery-zones/{zone_id}")
async def edit_delivery_zone(
    zone_id: int,
    zone_data: DeliveryZoneUpdateSchema,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    zone = db.query(models.DeliveryZone).filter(
        models.DeliveryZone.id == zone_id,
        models.DeliveryZone.caterer_id == profile.id
    ).first()
    
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
        
    zone.is_manual_quote = zone_data.is_manual_quote
    zone.fee = zone_data.fee if not zone_data.is_manual_quote else 0.0
    
    db.commit()
    return {"status": "success", "message": "Delivery zone updated"}

@router.get("/api/availability/check")
async def check_availability(
    date: str,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return {"is_available": False, "reason": "Invalid date format", "booking_count": 0, "max_capacity": 1, "is_manual_block": False}
        
    if target_date < datetime.today().date():
        return {"is_available": False, "reason": "Past date", "booking_count": 0, "max_capacity": 1, "is_manual_block": False}
    
    profile = user.caterer_profile
    max_capacity = profile.max_bookings_per_day or 1
    auto_block = profile.auto_block_enabled if profile.auto_block_enabled is not None else True
        
    # Check if explicitly blocked
    block = db.query(models.Availability).filter(
        models.Availability.caterer_id == profile.id,
        models.Availability.date == target_date
    ).first()
    
    if block and not block.is_available:
        return {"is_available": False, "reason": block.reason or "Manually blocked", "booking_count": 0, "max_capacity": max_capacity, "is_manual_block": True}
        
    # Count active bookings on that date
    existing_on_date = db.query(models.Booking).filter(
        models.Booking.caterer_id == profile.id,
        models.Booking.event_date == target_date,
        models.Booking.status != 'cancelled',
        models.Booking.is_archived == False
    ).count()
    
    if auto_block and existing_on_date >= max_capacity:
        return {"is_available": False, "reason": f"Capacity full ({existing_on_date}/{max_capacity} slots used)", "booking_count": existing_on_date, "max_capacity": max_capacity, "is_manual_block": False}
        
    return {"is_available": True, "reason": "", "booking_count": existing_on_date, "max_capacity": max_capacity, "is_manual_block": False}

@router.get("/api/customers/check_duplicate")
async def check_customer_duplicate(
    email: Optional[str] = None,
    contact: Optional[str] = None,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    """Real-time duplicate check for walk-in bookings."""
    if not email and not contact:
        return {"exists": False}
        
    query = db.query(models.User)
    
    if email:
        query = query.filter(models.User.email == email)
    elif contact:
        # Exact match or endswith for contact
        query = query.filter(models.User.phone_number.like(f"%{contact[-10:]}"))
        
    existing_user = query.first()
    
    if existing_user:
        return {
            "exists": True, 
            "name": f"{existing_user.first_name} {existing_user.last_name}".strip(),
            "email": existing_user.email,
            "contact": existing_user.phone_number,
            "role": existing_user.role
        }
    return {"exists": False}

@router.post("/api/bookings/manual")
async def create_manual_booking(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    try:
        data = await request.json()
        customer_email = data.get("customer_email", "").strip()
        customer_contact = data.get("customer_contact", "").strip()
        
        # Security: Prevent Caterer Self-Booking
        if customer_email.lower() == user.email.lower() or (customer_contact and customer_contact == user.phone_number):
            raise HTTPException(status_code=400, detail="manCustEmail|Security Violation: You cannot create a booking using your own caterer email or contact number.")
        
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        middle_name = data.get("middle_name", "").strip()
        
        if not first_name or not last_name:
            raise HTTPException(status_code=400, detail="manFirstName|First name and Last name are required")
            
        # Enterprise-Grade Name Validation (No John John John)
        fname_lower = first_name.lower()
        lname_lower = last_name.lower()
        mname_lower = middle_name.lower()
        if fname_lower == lname_lower or (middle_name and fname_lower == mname_lower):
            raise HTTPException(status_code=400, detail="manLastName|Invalid name format: First, middle, and last names cannot be identical.")

        customer_name = f"{first_name} {middle_name} {last_name}".replace("  ", " ").strip()
        
        province = data.get("province", "").strip()
        municipality = data.get("municipality", "").strip()
        barangay = data.get("barangay", "").strip()
        landmark = data.get("landmark", "").strip()
        
        if not province or not municipality or not barangay:
            raise HTTPException(status_code=400, detail="manProvince|Complete address (Province, Municipality, Barangay) is required")
            
        venue_address = f"{landmark + ', ' if landmark else ''}{barangay}, {municipality}, {province}"

        # 1. Handle User (Customer)
        target_user = None
        if "@" in customer_email:
            # Gmail Only Policy
            if not customer_email.lower().endswith("@gmail.com"):
                 raise HTTPException(status_code=400, detail="manCustEmail|For security and reliability, only Gmail accounts are supported for customer records.")
            target_user = db.query(models.User).filter(models.User.email == customer_email).first()
            if target_user and target_user.role != "customer":
                raise HTTPException(status_code=400, detail="manCustEmail|Security Violation: This email is registered to a Caterer or Admin account. Only customer accounts can be used for bookings.")
        
        # Contact Validation
        if customer_contact:
            clean_contact = "".join(filter(str.isdigit, customer_contact))
            if not clean_contact.startswith("09") or len(clean_contact) != 11:
                raise HTTPException(status_code=400, detail="manCustContact|Invalid contact number. Must be a valid 11-digit PH mobile number (09xx).")
            # Repetitive check (e.g. 09111111111)
            if len(set(clean_contact[2:])) <= 2:
                 raise HTTPException(status_code=400, detail="manCustContact|Invalid contact number pattern detected. Please use a real mobile number.")

        if not target_user:
            # Create a shadow/guest user
            temp_pass = auth.pwd_context.hash(str(uuid.uuid4()))
            target_user = models.User(
                email=customer_email if "@" in customer_email else f"walkin_{uuid.uuid4().hex[:8]}@guest.occashare.com",
                first_name=customer_name,
                phone_number=customer_contact,
                password_hash=temp_pass,
                role="customer",
                status="active"
            )
            db.add(target_user)
            db.flush() 

        # 2. Check Availability & Constraints
        event_date_str = data.get("event_date", "")[:10]
        if not event_date_str:
            raise HTTPException(status_code=400, detail="manDate|Event date is required.")
            
        event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
        
        # Lead Time & Past Date Check
        today = date.today()
        if event_date <= today + timedelta(days=1):
            raise HTTPException(status_code=400, detail="manDate|Bookings must be made at least 2 days in advance. Bookings for today or tomorrow are not allowed.")

        # Anti-Double Booking Validation (Duplicate Detection)
        event_type = data.get("event_type", "").strip()
        duplicate_check = db.query(models.Booking).filter(
            models.Booking.user_id == target_user.id,
            models.Booking.event_date == event_date,
            models.Booking.caterer_id == user.caterer_profile.id,
            models.Booking.status != 'cancelled'
        ).first()
        
        if duplicate_check:
            raise HTTPException(status_code=400, detail=f"manDate|Duplicate Error: The customer '{target_user.first_name}' already has an active booking registered on {event_date.strftime('%b %d, %Y')}. Double-booking the same customer on the exact same day is prohibited to prevent data redundancy.")

        # Package Constraint Check
        package_id = data.get("package_id")
        guest_count = int(data.get("guest_count", 0))
        if package_id:
            package = db.query(models.CateringPackage).get(package_id)
            if package:
                min_guests = package.min_guests or 1
                if guest_count < min_guests:
                    raise HTTPException(status_code=400, detail=f"manGuests|The selected package '{package.name}' requires a minimum of {min_guests} guests.")

        existing_on_date = db.query(models.Booking).filter(
            models.Booking.caterer_id == user.caterer_profile.id,
            models.Booking.event_date == event_date,
            models.Booking.status != 'cancelled',
            models.Booking.is_archived == False
        ).count()
        
        # Check manual block first
        manual_block = db.query(models.Availability).filter(
            models.Availability.caterer_id == user.caterer_profile.id,
            models.Availability.date == event_date,
            models.Availability.is_available == False
        ).first()
        
        if manual_block:
            raise HTTPException(status_code=400, detail=f"manDate|This date is manually blocked: {manual_block.reason or 'No reason provided'}. Unblock it first before adding bookings.")
        
        # Configurable capacity limit (caterer can override via force flag)
        max_cap = user.caterer_profile.max_bookings_per_day or 1
        force_override = data.get("force_override", False)
        auto_block = user.caterer_profile.auto_block_enabled if user.caterer_profile.auto_block_enabled is not None else True
        
        if auto_block and existing_on_date >= max_cap and not force_override:
            raise HTTPException(status_code=409, detail=f"manDate|Capacity Reached: You already have {existing_on_date}/{max_cap} active bookings on {event_date}. You can override this by confirming in the capacity warning dialog.")

        # 3. Create Booking
        event_time_str = data.get("event_time")
        if event_time_str:
            try:
                event_time = datetime.strptime(event_time_str[:5], "%H:%M").time()
            except ValueError:
                event_time = None
        else:
            event_time = None

        # Build special requests from notes
        special_notes = data.get("special_notes", "").strip()
        special_requests = f"Walk-in Booking{(' — ' + special_notes) if special_notes else ''}"
        
        # Payment handling
        payment_method = data.get("payment_method", "Cash")
        payment_status = data.get("payment_status", "paid")
        
        new_booking = models.Booking(
            user_id=target_user.id,
            caterer_id=user.caterer_profile.id,
            package_id=package_id or None,
            event_name=data.get("event_name"),
            event_type=data.get("event_type"),
            event_date=event_date,
            event_time=event_time,
            guest_count=guest_count,
            total_amount=data.get("total_amount", 0),
            total_price=data.get("total_amount", 0),
            venue_address=venue_address,
            status="confirmed", 
            payment_status=payment_status, 
            payment_method=payment_method,
            special_requests=special_requests,
            booking_source=data.get("booking_source", "OccaServe")
        )
        db.add(new_booking)
        db.flush()

        # 3. Handle Selected Menu Items (Add-ons or Package items)
        menu_item_ids = data.get("menu_items", [])
        if menu_item_ids:
            for mi_id in menu_item_ids:
                mi = db.query(models.MenuItem).get(mi_id)
                if mi:
                    sel_item = models.BookingMenuItem(
                        booking_id=new_booking.id,
                        menu_item_id=mi.id,
                        quantity=1,
                        price=mi.addon_price or mi.price or 0
                    )
                    db.add(sel_item)
        
        # 4. Add History
        history = models.BookingHistory(
            booking_id=new_booking.id,
            status="confirmed",
            notes="Manual walk-in booking created by caterer."
        )
        db.add(history)
        
        # 5. Add Operations Checklist
        create_default_booking_tasks(db, new_booking.id)
        
        db.commit()
        return {"status": "success", "booking_id": new_booking.id}
    except HTTPException as he:
        # Re-raise so FastAPI handles it correctly
        raise he
    except Exception as e:
        db.rollback()
        print(f"[CATERER MANUAL BOOKING ERROR] {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bookings/{booking_id}/dispatch-proof")
async def upload_dispatch_proof(
    booking_id: int,
    stage: str = Form(...),
    proof_image: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    if not proof_image.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    import base64
    content_bytes = await proof_image.read()
    b64 = base64.b64encode(content_bytes).decode('utf-8')
    mime = proof_image.content_type or 'image/jpeg'
    booking.dispatch_proof_url = f"data:{mime};base64,{b64}"
    
    # Update status simultaneously
    allowed_statuses = ["ready_for_delivery", "ready_for_pickup", "on_the_way"]
    if stage in allowed_statuses:
        booking.status = stage
        history = models.BookingHistory(
            booking_id=booking.id,
            status=stage,
            notes=f"Order marked as {stage}. Dispatch proof uploaded."
        )
        db.add(history)

        import asyncio
        asyncio.create_task(manager.broadcast_to_user(booking.user_id, {
            "type": "booking_update",
            "message": f"Your order for {booking.event_name} is dispatching!",
            "booking_id": booking.id,
            "status": stage
        }))

    db.commit()
    return {"status": "success", "message": "Dispatch proof uploaded"}

class StatusUpdateSchema(BaseModel):
    status: str

@router.post("/bookings/{booking_id}/update-status")
async def update_booking_status(
    booking_id: int,
    data: StatusUpdateSchema,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    new_status = data.status
    allowed_statuses = ["preparing", "ready_for_delivery", "on_the_way", "arrived", "setup_ongoing", "completed", "cancelled"]
    
    if new_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    # --- STRICT STATE MACHINE ENFORCEMENT ---
    # Define valid linear transitions to prevent status jumping
    valid_transitions = {
        "confirmed": ["preparing", "cancelled"],
        "preparing": ["ready_for_delivery", "cancelled"],
        "ready_for_delivery": ["on_the_way", "cancelled"],
        "on_the_way": ["arrived", "cancelled"],
        "arrived": ["setup_ongoing", "completed", "cancelled"],
        "setup_ongoing": ["completed", "cancelled"],
        "completed": [],
        "cancelled": []
    }
    
    current_status = booking.status
    if new_status != "cancelled":
        allowed_next = valid_transitions.get(current_status, allowed_statuses)
        if new_status not in allowed_next:
            raise HTTPException(status_code=400, detail=f"Cannot transition directly from '{current_status}' to '{new_status}'. Please follow proper status progression.")

    # --- PAYMENT VERIFICATION & CASH HANDLING ---
    if new_status == "completed":
        if booking.payment_method == "Cash":
            # For Cash payments, caterer completing it implies they collected the physical cash
            booking.payment_status = "paid"
            cash_log = models.AuditLog(
                user_id=user.id,
                action="CASH_RECEIVED_ACKNOWLEDGED",
                notes=f"Caterer marked booking #{booking.id} completed, acknowledging receipt of Cash/COD."
            )
            db.add(cash_log)
        elif booking.payment_status != "paid":
            # Removed the `payment_plan != "full"` loophole that allowed bypassing verification
            raise HTTPException(status_code=400, detail="You can only mark this as Completed once the booking is Fully Paid and verified by Admin.")

    old_status = booking.status
    booking.status = new_status
    
    # Log History
    history = models.BookingHistory(
        booking_id=booking.id,
        status=new_status,
        notes=f"Status changed from {old_status} to {new_status} by caterer."
    )
    db.add(history)

    # BILLING: Calculate Commission and Add to Outstanding Balance
    if new_status == "completed" and not booking.commission_calculated:
        caterer_prof = user.caterer_profile
        
        # Use Global Admin Commission Setting
        config = db.query(models.AdminSettings).first()
        commission_rate = (config.commission_rate / 100.0) if config and config.commission_rate else 0.10
        commission_amount = float(booking.total_amount or 0.0) * commission_rate
        
        caterer_prof.outstanding_balance = float(caterer_prof.outstanding_balance or 0.0) + commission_amount
        booking.commission_calculated = True
        
        billing_audit = models.AuditLog(
            user_id=user.id,
            action="COMMISSION_BILLED",
            notes=f"Billed PHP {commission_amount:.2f} commission for completed booking #{booking.id}."
        )
        db.add(billing_audit)
            
    db.commit()

    # Trigger Notifications
    from ..services.notification import NotificationService
    title = ""
    message = ""
    
    is_food_order = (booking.document_type == 'invoice')
    ref_id = f"ORD-{booking.id:03d}" if is_food_order else f"BK-{booking.id:03d}"
    item_type = "food order" if is_food_order else "booking"
    caterer_name = user.caterer_profile.business_name
    event_date_str = booking.event_date.strftime('%B %d, %Y') if booking.event_date else 'TBD'
    
    if new_status == "preparing":
        title = "Preparation Started!" if not is_food_order else "Order is Preparing!"
        message = f"{caterer_name} has started preparing your {item_type} '{booking.event_name}' ({ref_id}) scheduled on {event_date_str}."
    elif new_status == "ready_for_delivery":
        title = "Ready for Delivery!" if not is_food_order else "Order Ready for Dispatch!"
        message = f"Your {item_type} '{booking.event_name}' ({ref_id}) from {caterer_name} is now packed and ready for dispatch to your location."
    elif new_status == "on_the_way":
        title = "In Transit!" if not is_food_order else "Your Order is Dispatched!"
        message = f"{caterer_name}'s delivery team is now on the way to your location for '{booking.event_name}' ({ref_id})."
    elif new_status == "arrived":
        title = "Caterer has Arrived!" if not is_food_order else "Order Delivered!"
        message = f"{caterer_name} has arrived at your location for '{booking.event_name}' ({ref_id}). Please be ready to receive your {item_type}."
    elif new_status == "setup_ongoing":
        title = "Dining Setup Ongoing"
        message = f"{caterer_name} is currently setting up your food service for '{booking.event_name}' ({ref_id}). We are almost ready to serve!"
    elif new_status == "completed":
        title = "Transaction Completed!" if not is_food_order else "Order Completed!"
        message = f"Your {item_type} '{booking.event_name}' ({ref_id}) from {caterer_name} has been successfully completed. Thank you for choosing OccaServe!"

    # Route to the correct page based on booking type
    notif_link = f"/customer/bookings/manage/{booking.id}" if not is_food_order else f"/customer/orders/manage/{booking.id}"

    if title and message:
        await NotificationService.notify_status_update(
            db, 
            booking.user_id, 
            title, 
            message, 
            notif_link
        )

    # 4. WebSocket Update to Caterer
    status_class_map = {
        'pending_quotation': 'ps-badge-draft',
        'awaiting_caterer': 'ps-badge-pending',
        'awaiting_payment': 'ps-badge-payment',
        'pending': 'ps-badge-pending',
        'confirmed': 'ps-badge-confirmed',
        'preparing': 'ps-badge-preparing',
        'ready_for_delivery': 'ps-badge-ready',
        'on_the_way': 'ps-badge-transit',
        'arrived': 'ps-badge-arrived',
        'setup_ongoing': 'ps-badge-ongoing',
        'completed': 'ps-badge-completed',
        'cancelled': 'ps-badge-cancelled'
    }
    status_label_map = {
        'pending_quotation': 'Draft',
        'awaiting_caterer': 'To Sign',
        'awaiting_payment': 'Payment',
        'ready_for_delivery': 'Ready',
        'on_the_way': 'In Transit',
        'arrived': 'Arrived',
        'setup_ongoing': 'Fixing Setup',
    }
    
    await manager.broadcast_to_user(user.id, {
        "type": "booking_update",
        "booking_id": booking.id,
        "new_status": new_status,
        "status_label": status_label_map.get(new_status, new_status.replace('_', ' ').capitalize()),
        "status_class": status_class_map.get(new_status, 'ps-badge-draft'),
        "message": f"Status updated to {new_status}"
    })

    return {"status": "success", "new_status": new_status}

def _get_caterer_stats(profile, bookings, timeframe='month', start_date=None, end_date=None):
    from datetime import datetime, date, timedelta
    from dateutil.relativedelta import relativedelta
    
    today = date.today()
    
    # 1. Define Timeframe Bounds for TOP STATS
    if timeframe == 'custom' and start_date and end_date:
        try:
            stats_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            stats_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            stats_start = today.replace(day=1)
            stats_end = today
            
        days_diff = (stats_end - stats_start).days
        if days_diff < 0: # Validation fallback
            stats_start, stats_end = stats_end, stats_start
            days_diff = abs(days_diff)
            
        if days_diff <= 31:
            chart_points = [stats_start + timedelta(days=i) for i in range(days_diff + 1)]
            date_format = "%Y-%m-%d"
        else:
            months_diff = (stats_end.year - stats_start.year) * 12 + stats_end.month - stats_start.month + 1
            chart_points = [stats_start.replace(day=1) + relativedelta(months=i) for i in range(months_diff)]
            date_format = "%Y-%m"
    elif timeframe == 'day':
        stats_start = today
        stats_end = today
        chart_points = [(today - timedelta(days=i)) for i in range(6, -1, -1)] # Last 7 days for trend
        date_format = "%Y-%m-%d"
    elif timeframe == 'week':
        stats_start = today - timedelta(days=today.weekday()) # Current Week start (Monday)
        stats_end = stats_start + timedelta(days=6) # Current Week end (Sunday)
        chart_points = [(today - timedelta(days=i)) for i in range(13, -1, -1)] # Last 14 days for trend
        date_format = "%Y-%m-%d"
    elif timeframe == 'year':
        stats_start = today.replace(month=1, day=1) # Current Year start
        stats_end = today.replace(month=12, day=31) # Current Year end
        chart_points = [today.replace(month=1, day=1) + relativedelta(months=i) for i in range(12)] # All months of the year
        date_format = "%Y-%m"
    else: # Default: Monthly
        stats_start = today.replace(day=1) # Current Month start
        stats_end = (stats_start + relativedelta(months=1)) - timedelta(days=1) # Current Month end
        chart_points = [(today - relativedelta(months=5)).replace(day=1) + relativedelta(months=i) for i in range(6)]
        date_format = "%Y-%m"

    chart_keys = [d.strftime(date_format) for d in chart_points]
    
    # Stats Counters (FOR TOP CARDS - FILTERED)
    total_realized_revenue = 0
    total_projected_revenue = 0
    total_actual_expenses = 0
    total_projected_expenses = 0
    unique_customers = set()
    active_bookings = 0
    
    # Chart Data Pools (FOR TREND)
    period_revenue = {k: 0.0 for k in chart_keys}
    period_expenses = {k: 0.0 for k in chart_keys}
    period_bookings = {k: {'completed': 0, 'pending': 0} for k in chart_keys}
    
    package_stats = {} # {id: {revenue: 0, expenses: 0, orders: 0}}
    customer_stats = {} # {user_id: {...}}
    revenue_by_event = {} # {event_type: revenue}
    
    for b in bookings:
        if not b.event_date: continue
        
        amount = float(b.total_amount or b.total_price or 0)
        
        # Determine Cost Baseline
        base_cost_price = 0
        if b.package and b.package.cost_price:
            if b.package.price_unit == "per_guest":
                base_cost_price = (b.package.cost_price) * (b.guest_count or 1)
            else:
                base_cost_price = b.package.cost_price
        else:
            base_cost_price = amount * 0.60 # Standard 60% fallback
        
        actual_cost = b.actual_cost if b.actual_cost and b.actual_cost > 0 else base_cost_price
        
        # --- A. TOP STATS FILTERING ---
        if b.event_date >= stats_start and b.event_date <= stats_end:
            unique_customers.add(b.user_id)
            
            if b.status in ['confirmed', 'preparing', 'on_the_way', 'in_progress', 'completed']:
                total_projected_revenue += amount
                total_projected_expenses += actual_cost
                if b.status != 'completed': active_bookings += 1

            # Realized Revenue Computation
            cleared_amount = 0
            if b.payment_status == 'paid':
                cleared_amount = amount
            elif b.payment_status == 'deposit_paid':
                dep_pct = 20
                if b.quotation: dep_pct = b.quotation.downpayment_percent
                cleared_amount = amount * (dep_pct / 100)
            
            total_realized_revenue += cleared_amount
            total_actual_expenses += actual_cost if b.status in ['confirmed', 'completed', 'in_progress'] else 0

            # Loyalty & Spenders Tracking
            if b.user_id:
                if b.user_id not in customer_stats:
                    c_first = b.user.first_name if b.user and b.user.first_name else ""
                    c_last = b.user.last_name if b.user and b.user.last_name else ""
                    c_init = (c_first[0].upper() if c_first else "") + (c_last[0].upper() if c_last else "")
                    customer_stats[b.user_id] = {
                        "id": b.user_id,
                        "name": f"{c_first} {c_last}".strip() if b.user else "Walk-in",
                        "initials": c_init if c_init else "WI",
                        "spent": 0,
                        "orders": 0
                    }
                customer_stats[b.user_id]['orders'] += 1
                customer_stats[b.user_id]['spent'] += cleared_amount

            # Event Type Revenue Mapping
            evt_type = b.event_type or 'Other'
            if evt_type not in revenue_by_event:
                revenue_by_event[evt_type] = 0
            revenue_by_event[evt_type] += cleared_amount

        # --- B. TREND CHART AGGREGATION ---
        date_key = b.event_date.strftime(date_format)
        if date_key in period_revenue:
            cleared_chart = 0
            if b.payment_status == 'paid': cleared_chart = amount
            elif b.payment_status == 'deposit_paid':
                dep_pct = 20
                if b.quotation: dep_pct = b.quotation.downpayment_percent
                cleared_chart = amount * (dep_pct / 100)
                
            period_revenue[date_key] += cleared_chart
            period_expenses[date_key] += actual_cost
            
            if b.status in ['completed', 'confirmed', 'in_progress']:
                period_bookings[date_key]['completed'] += 1
            elif b.status != 'cancelled':
                period_bookings[date_key]['pending'] += 1

        # --- C. PACKAGE EFFICIENCY ---
        if b.package_id and b.event_date >= stats_start and b.event_date <= stats_end:
            if b.package_id not in package_stats:
                package_stats[b.package_id] = {'revenue': 0, 'expenses': 0, 'orders': 0}
            package_stats[b.package_id]['orders'] += 1
            if b.status in ['confirmed', 'completed']:
                package_stats[b.package_id]['revenue'] += amount
                package_stats[b.package_id]['expenses'] += actual_cost

    # Calculation Summary (With Zero-Division Guard)
    projected_net_profit = total_projected_revenue - total_projected_expenses
    projected_roi = ((projected_net_profit / total_projected_expenses) * 100) if total_projected_expenses > 0 else (100 if total_projected_revenue > 0 else 0)
    
    realized_net_profit = total_realized_revenue - total_actual_expenses
    realized_roi = ((realized_net_profit / total_actual_expenses) * 100) if total_actual_expenses > 0 else (100 if total_realized_revenue > 0 else 0)

    # Format Chart Data
    chart_data = []
    roi_trend_data = []
    bookings_chart_data = []
    
    for k in chart_keys:
        rev = period_revenue[k]
        exp = period_expenses[k]
        roi = ((rev - exp) / exp * 100) if exp > 0 else (100 if rev > 0 else 0)
        
        try:
            if date_format == "%Y-%m-%d":
                label = datetime.strptime(k, date_format).strftime("%b %d")
            else:
                label = datetime.strptime(k, date_format).strftime("%b %Y")
        except:
            label = k

        chart_data.append({"date": k, "revenue": rev, "label": label})
        roi_trend_data.append({"date": k, "roi": round(roi, 1), "label": label})
        bookings_chart_data.append({
            "date": k, "completed": period_bookings[k]['completed'], "pending": period_bookings[k]['pending'], "label": label
        })
    
    active_op_statuses = ['confirmed', 'preparing', 'on_the_way', 'in_progress']
    upcoming_events = sorted([b for b in bookings if b.status in active_op_statuses and b.event_date and b.event_date >= today], key=lambda x: x.event_date)[:4]
    
    popular_packages = []
    for pkg in profile.packages:
        if pkg.id in package_stats:
            stats = package_stats[pkg.id]
            pkg_roi = ((stats['revenue'] - stats['expenses']) / stats['expenses'] * 100) if stats['expenses'] > 0 else 0
            popular_packages.append({
                "id": pkg.id, "name": pkg.name, "price": float(pkg.price_per_head or pkg.price or 0), 
                "orders": stats['orders'], "roi": round(pkg_roi, 1)
            })
    popular_packages.sort(key=lambda x: x['orders'], reverse=True)

    top_spenders = sorted([v for k,v in customer_stats.items()], key=lambda x: x['spent'], reverse=True)[:5]
    revenue_by_event_list = sorted([{"event_type": k, "revenue": v} for k,v in revenue_by_event.items()], key=lambda x: x['revenue'], reverse=True)

    
    # Calculate Pending Actions
    pending_approvals = sum(1 for b in bookings if b.status in ['pending_quotation', 'pending_review'])
    pending_payments = sum(1 for b in bookings if b.payment_status == 'pending_verification')
    identity_requests = sum(1 for b in bookings if not getattr(b.user, 'is_verified', True))
    pending_contracts = sum(1 for b in bookings if getattr(b, 'contract_status', '') == 'awaiting_signature')
    
    # Count unread messages (assuming message relation exists, or we just mock/query it, here we mock it to 0 as we don't have direct access in bookings list)
    customer_messages = 0
    for b in bookings:
        for m in getattr(b, 'messages', []):
            if not getattr(m, 'is_read', True) and getattr(m, 'sender_id') != profile.user_id:
                customer_messages += 1

    pending_actions = {
        "approvals": pending_approvals,
        "payments": pending_payments,
        "identity": identity_requests,
        "contracts": pending_contracts,
        "messages": customer_messages,
        "total": pending_approvals + pending_payments + identity_requests + pending_contracts + customer_messages
    }

    # Today's Schedule
    today_schedule = [b for b in bookings if b.event_date == today and b.status not in ['cancelled', 'draft']]
    today_schedule.sort(key=lambda x: x.event_time.hour if x.event_time else 0)
    
    return {
        "total_revenue": total_realized_revenue, 
        "projected_revenue": total_projected_revenue,
        "net_profit": realized_net_profit,
        "projected_profit": projected_net_profit,
        "estimated_expenses": total_projected_expenses,
        "actual_expenses": total_actual_expenses,
        "roi_percentage": round(realized_roi, 1),
        "projected_roi": round(projected_roi, 1),
        "total_customers": len(unique_customers),
        "chart_data": chart_data,
        "roi_trend_data": roi_trend_data,
        "bookings_chart_data": bookings_chart_data,
        "upcoming_events": upcoming_events,
        "popular_packages": popular_packages[:4],
        "recent_orders": sorted([b for b in bookings if b.event_date and b.event_date >= stats_start and b.event_date <= stats_end], key=lambda x: x.id, reverse=True)[:5],
        "top_spenders": top_spenders,
        "revenue_by_event": revenue_by_event_list,
        "timeframe": timeframe,
        "active_bookings": active_bookings,
        "upcoming_events_count": len([b for b in bookings if b.event_date and today < b.event_date <= today + timedelta(days=7)]),
        "pending_actions": pending_actions,
        "today_schedule": today_schedule
    }

@router.get("/api/bookings/urgent-check")
async def check_urgent_bookings(
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    if not profile:
        return {"has_urgent": False}
        
    today = date.today()
    urgent_found = False
    
    for b in profile.bookings:
        caterer_action_needed = False
        
        is_early_stage = b.status in ['draft', 'pending', 'awaiting_caterer', 'awaiting_payment', 'pending_payment', 'pending_review']
        
        if b.status in ['pending', 'awaiting_caterer', 'pending_review']:
            caterer_action_needed = True
            
        # If waiting for customer to re-upload, it is NOT urgent for the caterer
        if b.payment_status in ['reupload_requested', 'balance_reupload_requested']:
            caterer_action_needed = False
            
        # If customer submitted initial proof and it's still in early stages, caterer MUST act
        if b.payment_status == 'proof_submitted' and is_early_stage:
            caterer_action_needed = True
            
        if not b.is_archived and caterer_action_needed and b.event_date:
            if (b.event_date - today).days <= 2:
                urgent_found = True
                break
                
    return {"has_urgent": urgent_found}

@router.get("/dashboard", response_class=HTMLResponse)
async def caterer_dashboard(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    bookings = [b for b in profile.bookings if b.status not in ['draft', 'pending_quotation', 'pending_review', 'inquiry', 'negotiating', 'quoted'] and not b.is_archived]
    
    timeframe = request.query_params.get('timeframe', 'month')
    stats = _get_caterer_stats(profile, bookings, timeframe=timeframe)
    
    # Calculate profile completion dynamically
    has_logo = bool(profile.logo_url and profile.logo_url != "/static/images/default_caterer.png")
    has_cover = bool(profile.cover_image_url)
    has_description = bool(profile.description and profile.description.strip())
    has_packages = len([p for p in profile.packages if getattr(p, 'is_archived', False) == False]) >= 1
    has_portfolio = len([p for p in profile.portfolios if getattr(p, 'visibility', 'Public') == 'Public']) >= 1
    has_starting_price = bool(profile.starting_price and profile.starting_price > 0)
    has_menu = len([m for m in profile.menu_items if getattr(m, 'is_archived', False) == False]) > 0
    has_permit = bool(profile.permit_url)
    
    # Check eligibility to publish: Identity Verified + 1 Package + 3 Photos + Description
    is_identity_verified = profile.verification_status == 'Verified' and profile.user.is_verified
    can_publish = is_identity_verified and has_packages and has_portfolio and has_description

    completion_pct = 0
    if is_identity_verified: completion_pct += 40
    if has_logo: completion_pct += 10
    if has_cover: completion_pct += 5
    if has_description: completion_pct += 5
    if has_packages: completion_pct += 15
    if has_portfolio: completion_pct += 10
    if has_starting_price: completion_pct += 5
    if has_menu: completion_pct += 5
    if has_permit: completion_pct += 5
    
    # Next Recommended Action Logic
    next_action = None
    if not is_identity_verified:
        next_action = {"title": "Verify Business Identity", "desc": "Upload your valid ID to verify your catering business.", "url": "/caterer/profile#verification", "btn": "Verify Now"}
    elif not has_description:
        next_action = {"title": "Add Business Description", "desc": "Tell customers about your catering services and specialties.", "url": "/caterer/profile#general", "btn": "Add Description"}
    elif not has_permit:
        next_action = {"title": "Upload Business Permit", "desc": "Upload your permit to increase your trust rating.", "url": "/caterer/profile#verification", "btn": "Upload Permit"}
    elif not has_logo:
        next_action = {"title": "Upload Business Logo", "desc": "Make your profile stand out with a professional logo.", "url": "/caterer/profile#general", "btn": "Upload Logo"}
    elif not has_cover:
        next_action = {"title": "Upload Cover Image", "desc": "Add a beautiful banner image to attract customers.", "url": "/caterer/profile#general", "btn": "Upload Cover"}
    elif not has_menu:
        next_action = {"title": "Create Sample Menu", "desc": "Add at least one menu item that customers can choose from.", "url": "/caterer/menu", "btn": "Add Menu Item"}
    elif not has_portfolio:
        next_action = {"title": "Create Portfolio Event", "desc": "Showcase your past events and credibility by creating a portfolio project.", "url": "/caterer/portfolio", "btn": "Create Portfolio"}
    elif not has_packages:
        next_action = {"title": "Create First Package", "desc": "Create at least one catering package for customers to book.", "url": "/caterer/packages", "btn": "Create Package"}
    elif profile.status == 'Draft' or profile.status == 'Identity Verified':
        next_action = {"title": "Publish Listing", "desc": "You're all set! Publish your listing to start receiving bookings.", "url": "#", "btn": "Publish Now", "onclick": "togglePublish(this)"}

    total_bookings = len([b for b in profile.bookings if b.status not in ['draft', 'pending_quotation', 'pending_review', 'inquiry', 'negotiating', 'quoted', 'cancelled'] and not b.is_archived])

    return templates.TemplateResponse("caterer/index.html", {
        "request": request,
        "user": user,
        "profile": profile,
        **stats,
        "active_page": "dashboard",
        "completion_percentage": completion_pct,
        "has_logo": has_logo,
        "has_cover": has_cover,
        "has_description": has_description,
        "has_packages": has_packages,
        "has_portfolio": has_portfolio,
        "has_starting_price": has_starting_price,
        "has_menu": has_menu,
        "has_permit": has_permit,
        "can_publish": can_publish,
        "is_identity_verified": is_identity_verified,
        "next_action": next_action,
        "total_bookings": total_bookings
    })

@router.post("/toggle-publish")
async def toggle_publish(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    if not profile:
        return JSONResponse(status_code=404, content={"success": False, "message": "Profile not found"})
        
    has_description = bool(profile.description and profile.description.strip())
    has_packages = len([p for p in profile.packages if getattr(p, 'is_archived', False) == False]) >= 1
    has_portfolio = len([p for p in profile.portfolios if getattr(p, 'visibility', 'Public') == 'Public']) >= 1
    is_identity_verified = profile.verification_status == 'Verified'
    
    can_publish = is_identity_verified and has_packages and has_portfolio and has_description
    
    if profile.status == "Published":
        profile.status = "Identity Verified"
        db.commit()
        return {"success": True, "status": "Identity Verified", "message": "Listing successfully unpublished."}
    else:
        if not can_publish:
            missing = []
            if not is_identity_verified: missing.append("Identity Verification")
            if not has_packages: missing.append("At least 1 Package")
            if not has_portfolio: missing.append("At least 1 Portfolio Event")
            if not has_description: missing.append("Business Description")
            return JSONResponse(
                status_code=400, 
                content={
                    "success": False, 
                    "message": f"Cannot publish listing. Missing requirements: {', '.join(missing)}"
                }
            )
        
        profile.status = "Published"
        db.commit()
        return {"success": True, "status": "Published", "message": "Listing successfully published to customers!"}

@router.get("/api/omni-search")
async def caterer_omni_search(
    q: str,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    import time
    query = q.lower().strip()
    if not query:
        return {"results": []}
    
    results = []
    profile = user.caterer_profile
    if not profile:
        return {"results": []}

    # 1. Search Bookings (Reference ID, Customer Name, Event Type, Status)
    bookings = db.query(models.Booking).filter(
        models.Booking.caterer_id == profile.id
    ).all()
    
    for b in bookings:
        b_ref = str(b.id)
        b_name = f"{b.user.first_name} {b.user.last_name}".lower() if b.user else ""
        b_type = b.event_type.lower() if b.event_type else ""
        b_status = b.status.lower() if b.status else ""
        
        if query in b_ref or query in b_name or query in b_type or query in b_status:
            results.append({
                "type": "Booking",
                "title": f"Booking #{b_ref} - {b_name.title()}",
                "subtitle": f"{b.event_type.capitalize() if b.event_type else 'Event'} • {b.status.upper() if b.status else 'UNKNOWN'}",
                "url": f"/caterer/bookings?focus={b.id}",
                "icon": "fas fa-calendar-check"
            })

    # 2. Search Menu Items
    menu_items = db.query(models.MenuItem).filter(
        models.MenuItem.caterer_id == profile.id,
        models.MenuItem.is_archived == False
    ).all()
    for item in menu_items:
        i_name = item.name.lower() if item.name else ""
        if query in i_name:
            results.append({
                "type": "Menu Item",
                "title": item.name,
                "subtitle": f"₱{item.price:,.2f} • {item.category}",
                "url": "/caterer/menu",
                "icon": "fas fa-utensils"
            })

    # 3. Search Packages
    packages = db.query(models.CateringPackage).filter(
        models.CateringPackage.caterer_id == profile.id,
        models.CateringPackage.status != "archived"
    ).all()
    for pkg in packages:
        p_name = pkg.name.lower() if pkg.name else ""
        if query in p_name:
            results.append({
                "type": "Package",
                "title": pkg.name,
                "subtitle": f"₱{pkg.price_per_head:,.2f}/head",
                "url": "/caterer/packages",
                "icon": "fas fa-box"
            })
            
    # 4. Search Customers
    customers = db.query(models.User).join(models.Booking, models.Booking.user_id == models.User.id).filter(
        models.Booking.caterer_id == profile.id
    ).distinct().all()
    for c in customers:
        c_name = f"{c.first_name} {c.last_name}".lower()
        c_email = c.email.lower()
        if query in c_name or query in c_email:
            results.append({
                "type": "Customer",
                "title": f"{c.first_name} {c.last_name}",
                "subtitle": c.email,
                "url": "/caterer/customers",
                "icon": "fas fa-user-tag"
            })

    # 5. Search System Modules/Pages
    pages = [
        {"name": "Dashboard & Analytics", "url": "/caterer/dashboard", "icon": "fas fa-chart-line"},
        {"name": "Calendar & Schedule", "url": "/caterer/calendar", "icon": "fas fa-calendar-alt"},
        {"name": "Booking Management", "url": "/caterer/bookings", "icon": "fas fa-book-open"},
        {"name": "Financials & Payouts", "url": "/caterer/financials", "icon": "fas fa-wallet"},
        {"name": "Payments & Invoices", "url": "/caterer/payments", "icon": "fas fa-file-invoice-dollar"},
        {"name": "Customers Database", "url": "/caterer/customers", "icon": "fas fa-users"},
        {"name": "Menu Builder", "url": "/caterer/menu", "icon": "fas fa-utensils"},
        {"name": "Package Management", "url": "/caterer/packages", "icon": "fas fa-box-open"},
        {"name": "Reviews & Feedback", "url": "/caterer/reviews", "icon": "fas fa-star"},
        {"name": "Brand Profile Settings", "url": "/caterer/profile", "icon": "fas fa-store"},
        {"name": "Message Center", "url": "/caterer/messages", "icon": "fas fa-comments"}
    ]
    
    for p in pages:
        if query in p["name"].lower():
            results.append({
                "type": "Module",
                "title": p["name"],
                "subtitle": "System Page",
                "url": p["url"],
                "icon": p["icon"]
            })

    # Limit results to 8 to avoid overwhelming the UI
    return {"results": results[:8]}

@router.get("/api/dashboard-overview")
async def dashboard_overview_api(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    try:
        from app.services.reminders import generate_caterer_reminders
        generate_caterer_reminders(user.id, db)
    except Exception as e:
        print(f'Reminder generation error: {e}')
    from fastapi.responses import JSONResponse
    profile = user.caterer_profile
    bookings = [b for b in profile.bookings if b.status not in ['draft', 'pending_quotation', 'pending_review'] and not b.is_archived]
    
    timeframe = request.query_params.get('timeframe', 'month')
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    stats = _get_caterer_stats(profile, bookings, timeframe=timeframe, start_date=start_date, end_date=end_date)
    
    # Generate intelligent calendar reminders proactively
    try:
        from app.services.reminders import generate_caterer_reminders
        generate_caterer_reminders(user.id, db)
    except Exception as e:
        print(f"Error generating reminders: {e}")
    
    # Process complex objects for JSON
    serializable_upcoming = []
    for e in stats['upcoming_events']:
        total_tasks = len(e.tasks)
        completed_tasks = sum(1 for t in e.tasks if t.is_completed)
        progress = round((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0

        serializable_upcoming.append({
            "id": e.id,
            "event_name": e.event_name,
            "event_type": e.event_type,
            "status": e.status,
            "package_name": e.package.name if e.package else e.event_type,
            "event_date": e.event_date.strftime('%Y-%m-%d') if e.event_date else None,
            "event_time": e.event_time.strftime('%I:%M %p') if e.event_time else None,
            "month_short": e.event_date.strftime('%b') if e.event_date else '???',
            "day": e.event_date.strftime('%d') if e.event_date else '??',
            "venue_address": e.venue_address,
            "guest_count": e.guest_count,
            "task_progress": progress,
            "tasks_count": total_tasks,
            "tasks_completed": completed_tasks
        })

    serializable_recent = []
    for b in stats['recent_orders']:
        c_first = b.user.first_name if b.user and b.user.first_name else ""
        c_last = b.user.last_name if b.user and b.user.last_name else ""
        c_init = (c_first[0].upper() if c_first else "") + (c_last[0].upper() if c_last else "")
        
        serializable_recent.append({
            "id": b.id,
            "customer_name": f"{c_first} {c_last}".strip() if b.user else "Walk-in Customer",
            "customer_initials": c_init if c_init else "WI",
            "event_type": b.event_type,
            "total_amount": float(b.total_amount or 0),
            "event_date": b.event_date.strftime('%b %d, %Y') if b.event_date else '',
            "status": b.status
        })

    return JSONResponse({
        "total_revenue": stats['total_revenue'],
        "projected_revenue": stats['projected_revenue'],
        "net_profit": stats['net_profit'],
        "projected_profit": stats['projected_profit'],
        "estimated_expenses": stats['estimated_expenses'],
        "actual_expenses": stats['actual_expenses'],
        "roi_percentage": stats['roi_percentage'],
        "roi_trend_data": stats['roi_trend_data'],
        "total_customers": stats['total_customers'],
        "chart_data": stats['chart_data'],
        "bookings_chart_data": stats['bookings_chart_data'],
        "upcoming_events": serializable_upcoming,
        "popular_packages": stats['popular_packages'],
        "recent_orders": serializable_recent,
        "top_spenders": stats['top_spenders'],
        "revenue_by_event": stats['revenue_by_event']
    })

@router.get("/bookings/{booking_id}")
async def redirect_booking_details(booking_id: int):
    return RedirectResponse(url=f"/caterer/bookings?focus={booking_id}", status_code=303)

@router.get("/bookings", response_class=HTMLResponse)

async def manage_bookings(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    all_bookings = [b for b in user.caterer_profile.bookings if b.status not in ['draft', 'pending_quotation'] and not b.is_archived and b.document_type != 'invoice']
    all_bookings.sort(key=lambda x: x.id, reverse=True)
    
    total_bookings = len(all_bookings)
    confirmed_count = sum(1 for b in all_bookings if b.status in ['confirmed', 'completed'])
    pending_count = sum(1 for b in all_bookings if b.status in ['pending', 'awaiting_caterer', 'awaiting_payment', 'pending_review'])
    cancelled_count = sum(1 for b in all_bookings if b.status == 'cancelled')
    
    packages = db.query(models.CateringPackage).filter(
        models.CateringPackage.caterer_id == user.caterer_profile.id,
        models.CateringPackage.status == 'active'
    ).all()
    
    from datetime import date
    today = date.today()
    
    return templates.TemplateResponse("caterer/bookings.html", {
        "request": request,
        "user": user,
        "bookings": all_bookings,
        "packages": packages,
        "total_bookings": total_bookings,
        "confirmed_count": confirmed_count,
        "pending_count": pending_count,
        "cancelled_count": cancelled_count,
        "active_page": "bookings",
        "today": today
    })

@router.get("/orders", response_class=HTMLResponse)
async def manage_orders(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    all_orders = [b for b in user.caterer_profile.bookings if b.status not in ['draft', 'pending_quotation'] and not b.is_archived and b.document_type == 'invoice']
    all_orders.sort(key=lambda x: x.id, reverse=True)
    
    total_bookings = len(all_orders)
    confirmed_count = sum(1 for b in all_orders if b.status in ['confirmed', 'completed'])
    pending_count = sum(1 for b in all_orders if b.status in ['pending', 'awaiting_caterer', 'awaiting_payment', 'pending_review'])
    cancelled_count = sum(1 for b in all_orders if b.status == 'cancelled')
    
    from datetime import date
    today = date.today()
    
    return templates.TemplateResponse("caterer/orders.html", {
        "request": request,
        "user": user,
        "bookings": all_orders,
        "total_bookings": total_bookings,
        "confirmed_count": confirmed_count,
        "pending_count": pending_count,
        "cancelled_count": cancelled_count,
        "active_page": "orders",
        "today": today
    })

@router.get("/bookings/{booking_id}/contract", response_class=HTMLResponse)
async def view_contract_caterer(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    quotation = booking.quotation
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found for this booking")

    return templates.TemplateResponse("caterer/contract_view.html", {
        "request": request,
        "user": user,
        "booking": booking,
        "quotation": quotation,
        "active_page": "bookings"
    })

@router.get("/bookings/{booking_id}/sign", response_class=HTMLResponse)
async def sign_contract_caterer(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    quotation = booking.quotation
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found for this booking")

    return templates.TemplateResponse("caterer/sign_contract.html", {
        "request": request,
        "user": user,
        "booking": booking,
        "quotation": quotation,
        "active_page": "bookings"
    })

@router.get("/archives", response_class=HTMLResponse)
async def caterer_archives(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    """Render the archives view for the caterer, showing all archived items."""
    profile = user.caterer_profile
    if not profile:
        return RedirectResponse(url="/caterer/setup")

    # Fetch archived items
    archived_menu_items = [item for item in profile.menu_items if item.is_archived]
    archived_packages = [pkg for pkg in profile.packages if pkg.status == 'archived']
    archived_gallery_items = [item for item in profile.gallery_items if item.is_archived]
    archived_bookings = [b for b in profile.bookings if b.is_archived]
    archived_services = [s for s in profile.service_items if getattr(s, 'is_archived', False)]
    archived_equipment = [e for e in profile.equipment_items if getattr(e, 'is_archived', False)]
    archived_portfolios = [p for p in profile.portfolios if getattr(p, 'is_archived', False)]

    return templates.TemplateResponse("caterer/archives.html", {
        "request": request,
        "user": user,
        "archived_menu_items": archived_menu_items,
        "archived_packages": archived_packages,
        "archived_gallery_items": archived_gallery_items,
        "archived_bookings": archived_bookings,
        "archived_services": archived_services,
        "archived_equipment": archived_equipment,
        "archived_portfolios": archived_portfolios,
        "active_page": "archives"
    })

@router.get("/payments", response_class=HTMLResponse)
async def caterer_payments(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    from datetime import datetime, timezone
    profile = user.caterer_profile
    bookings = [b for b in profile.bookings if b.status not in ['draft', 'pending_review'] and not b.is_archived]

    # ── Post-Paid Commission System Variables ──────────────────────────
    outstanding_balance = profile.outstanding_balance or 0.0
    lifetime_revenue = 0.0
    active_count = 0
    total_commission_paid = 0.0

    for b in bookings:
        if b.status in ('cancelled', 'rejected'):
            continue
        if b.status not in ('completed'):
            active_count += 1
            
        gross_amount = float(b.total_amount or b.total_price or 0)
        
        if b.payment_status == 'paid' and b.status == 'completed':
            lifetime_revenue += gross_amount

    # Fetch billing invoices
    invoices = db.query(models.BillingInvoice).filter(
        models.BillingInvoice.caterer_id == profile.id
    ).order_by(models.BillingInvoice.created_at.desc()).all()
    
    for invoice in invoices:
        if invoice.status == 'paid':
            total_commission_paid += float(invoice.amount)

    return templates.TemplateResponse("caterer/payments.html", {
        "request": request,
        "user": user,
        "bookings": bookings,
        "invoices": invoices,
        "outstanding_balance": outstanding_balance,
        "lifetime_revenue": lifetime_revenue,
        "total_commission_paid": total_commission_paid,
        "active_count": active_count,
        "active_page": "payments"
    })


@router.get("/payments/{booking_id}/confirm")
async def confirm_caterer_payment_get(booking_id: int):
    # This specifically handles cases where old cached JS or browser redirects 
    # might attempt a GET request on this state-changing endpoint.
    # We redirect back to payments with an instruction to retry.
    return RedirectResponse(
        url="/caterer/payments?error_msg=Manual+refresh+required.+Please+click+Verify+again.", 
        status_code=303
    )

async def _confirm_booking_logic(db: Session, booking: models.Booking, caterer_user: models.User, is_manual_accept: bool = False):
    """Shared logic for confirming a booking via payment verification or manual acceptance."""
    from ..services.notification import NotificationService
    import asyncio
    
    old_payment_status = booking.payment_status
    history_note = "Booking confirmed by caterer."
    
    # CASE 1: Downpayment Verification or Initial Acceptance
    if booking.payment_status in ['proof_submitted', 'reupload_requested', 'pending'] or booking.status == 'pending':
        if booking.payment_plan == 'full':
            booking.payment_status = 'paid'
        else:
            booking.payment_status = 'deposit_paid'
        booking.status = 'confirmed'
        
        # Initialize operations checklist
        create_default_booking_tasks(db, booking.id)
        
        # Calculate Initial Actual Cost (Baseline)
        total_cost = 0
        if booking.package:
            if booking.package.price_unit == "per_guest":
                total_cost += (booking.package.cost_price or 0) * (booking.guest_count or 0)
            else:
                total_cost += (booking.package.cost_price or 0)
        
        # Add selected items cost
        from sqlalchemy import text
        # Using a join or subquery might be better but let's stick to the existing approach safely
        for item in booking.selected_items:
            if hasattr(item, 'menu_item') and item.menu_item:
                total_cost += (item.menu_item.cost_price or 0)
        
        booking.actual_cost = total_cost
        
        if is_manual_accept:
            history_note = "Booking manually ACCEPTED and CONFIRMED by caterer."
        else:
            history_note = "Downpayment verified and confirmed. Booking is now officially CONFIRMED."
            
        # Notification to Customer
        await NotificationService.notify_status_update(
            db, booking.user_id, 
            "Booking Confirmed!", 
            f"Your booking for '{booking.event_name}' has been confirmed. Your reservation is now active.", 
            f"/customer/bookings/manage/{booking.id}"
        )

    # CASE 2: Final Balance Verification
    elif booking.payment_status in ['balance_proof_submitted', 'balance_reupload_requested']:
        booking.payment_status = 'paid'
        history_note = "Final balance verified. Booking is now FULLY PAID."
        
        await NotificationService.notify_status_update(
            db, booking.user_id, 
            "Payment Fully Verified!", 
            f"Your full payment for '{booking.event_name}' has been received and verified. Thank you!", 
            f"/customer/bookings/manage/{booking.id}"
        )
    
    # CASE 3: Fallback / Manual Override to Paid
    else:
        booking.payment_status = 'paid'
        history_note = "Booking/Payment marked as fully received manually."

    # Log History
    history = models.BookingHistory(
        booking_id=booking.id,
        status=booking.status,
        notes=history_note
    )
    db.add(history)
    db.commit()

    # WebSocket Updates
    # 1. To Customer
    asyncio.create_task(manager.broadcast_to_user(booking.user_id, {
        "type": "payment_update",
        "message": f"Status updated for {booking.event_name}",
        "booking_id": booking.id,
        "status": booking.status,
        "payment_status": booking.payment_status
    }))

    # 2. To Caterer
    status_class_map = {
        'deposit_paid': 'ps-badge-confirmed',
        'paid': 'ps-badge-completed',
        'proof_submitted': 'ps-badge-payment',
        'balance_proof_submitted': 'ps-badge-payment'
    }
    
    await manager.broadcast_to_user(caterer_user.id, {
        "type": "booking_update",
        "booking_id": booking.id,
        "new_status": booking.status,
        "new_payment_status": booking.payment_status,
        "payment_status_class": status_class_map.get(booking.payment_status, 'ps-badge-payment'),
        "message": history_note
    })

    await manager.broadcast_to_user(caterer_user.id, {
        "type": "dashboard_update",
        "message": "Stats updated: Booking confirmed."
    })

    return {"status": "success", "message": history_note}

@router.post("/bookings/{booking_id}/accept")
async def accept_booking_manual(
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    """Allows a caterer to manually accept a booking, bypassing digital proof verification."""
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    result = await _confirm_booking_logic(db, booking, user, is_manual_accept=True)
    return result

@router.post("/payments/{booking_id}/confirm")
async def confirm_caterer_payment(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    # [Rest of AI verification logic remains before calling logic]

    # [NEW] Automated Proof Verification Detection
    proof_path = None
    if booking.payment_proof_url:
        # Resolve path handling both root-relative and app-relative structures
        raw_url = booking.payment_proof_url.lstrip("/")
        proof_path = os.path.join(os.getcwd(), raw_url)
        if not os.path.exists(proof_path):
            # Fallback for when the file is inside the 'app/' directory but DB path is web-relative
            proof_path = os.path.join(os.getcwd(), "app", raw_url)

        if os.path.exists(proof_path):
            verify_results = payment_verification_service.check_for_fraud(db, booking, proof_path)
            booking.payment_verification_data = verify_results
            booking.proof_image_hash = payment_verification_service.get_image_hash(proof_path)
            if verify_results["confidence"] > 80:
                booking.ocr_verified = True
            
            # [NEW] Automated Fraud Flagging
            if verify_results["is_duplicate_ref"] or verify_results["confidence"] < 40 or not verify_results.get("amount_match", True):
                for flag_desc in verify_results["flags"]:
                    # Check if flag already exists to avoid duplicates
                    exists = db.query(models.FraudFlag).filter(
                        models.FraudFlag.booking_id == booking.id,
                        models.FraudFlag.description == flag_desc
                    ).first()
                    if not exists:
                        db.add(models.FraudFlag(
                            booking_id=booking.id, 
                            flag_type="high_risk_detected", 
                            description=flag_desc
                        ))
                
                # WebSocket Alert to Caterer
                await manager.broadcast_to_user(user.id, {
                    "type": "risk_alert",
                    "booking_id": booking_id,
                    "message": "⚠️ High Risk Payment Detected! Check AI Scan details."
                })

        
    # Call shared confirmation logic
    result = await _confirm_booking_logic(db, booking, user, is_manual_accept=False)
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({
            "status": "success", 
            "message": result["message"], 
            "new_status": booking.status,
            "new_payment_status": booking.payment_status
        })
        
    return RedirectResponse(url="/caterer/payments?success_msg=Payment+confirmed+successfully", status_code=303)

@router.post("/bookings/{booking_id}/request-new-proof")
async def request_new_proof(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    data = await request.json()
    reason = data.get("reason", "The submitted proof was unreadable or incorrect.")

    # 1. Reset proof fields and status based on current state
    if booking.payment_status == 'proof_submitted':
        booking.payment_status = 'reupload_requested'
        booking.payment_proof_url = None
    elif booking.payment_status == 'balance_proof_submitted':
        booking.payment_status = 'balance_reupload_requested'
        booking.balance_proof_url = None

    # 2. Add History
    history = models.BookingHistory(
        booking_id=booking.id,
        status=booking.status,
        notes=f"Payment proof rejected. Reason: {reason}"
    )
    db.add(history)
    
    # 3. Add Fraud Flag if it was rejected for suspicious reasons
    if "fake" in reason.lower() or "suspicious" in reason.lower() or "duplicate" in reason.lower():
        db.add(models.FraudFlag(
            booking_id=booking.id,
            flag_type="manual_rejection",
            description=f"Caterer rejected proof as suspicious: {reason}"
        ))

    db.commit()

    # 4. Notify Customer
    from ..services.notification import NotificationService
    await NotificationService.notify_proof_rejected(db, booking, reason)

    # 5. Broadcast real-time update to both parties
    await manager.broadcast_to_user(booking.user_id, {
        "type": "payment_rejected",
        "booking_id": booking.id,
        "reason": reason,
        "message": f"Your payment proof for '{booking.event_name}' was rejected. Please check your dashboard for details."
    })
    
    await manager.broadcast_to_user(user.id, {
        "type": "booking_update",
        "booking_id": booking.id,
        "new_payment_status": booking.payment_status,
        "message": "Proof rejected. Waiting for re-upload."
    })

    return {"status": "success", "message": "Customer notified to re-upload proof."}

class DueDateRequest(BaseModel):
    due_date: str

@router.post("/api/bookings/{booking_id}/set-due-date")
async def set_balance_due_date(
    booking_id: int,
    req: DueDateRequest,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or (user.caterer_profile and booking.caterer_id != user.caterer_profile.id):
        raise HTTPException(status_code=404, detail="Booking not found")

    try:
        from datetime import datetime, date
        # Validate format
        new_date = datetime.strptime(req.due_date, '%Y-%m-%d').date()
        today = date.today()
        
        # Validation 1: No Past Dates
        if new_date < today:
            raise HTTPException(status_code=400, detail="Deadline cannot be set to a past date.")
            
        # Validation 2: Event Date Constraint
        if booking.event_date:
            event_date = booking.event_date.date() if isinstance(booking.event_date, datetime) else booking.event_date
            if new_date > event_date:
                raise HTTPException(status_code=400, detail="Deadline cannot be set after the scheduled Event Date.")
                
        booking.balance_due_date = new_date
        
        # Add History
        history = models.BookingHistory(
            booking_id=booking.id,
            status=booking.status,
            notes=f"Balance Due Date set to {req.due_date} by Caterer."
        )
        db.add(history)
        db.commit()

        # [NEW] Notify Customer
        from ..services.notification import NotificationService
        await NotificationService.notify_status_update(
            db, 
            booking.user_id, 
            "Balance Payment Deadline Set", 
            f"The caterer has set the final payment deadline for '{booking.event_name}' to {req.due_date}. Please ensure payment is settled by this date.", 
            f"/customer/bookings/manage/{booking.id}"
        )
        
        return {"status": "success", "message": "Due date updated and customer notified"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

@router.post("/api/bookings/{booking_id}/verify-proof")
async def verify_booking_proof(
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    if not booking.payment_proof_url and not booking.balance_proof_url:
        return {"status": "error", "message": "No proof uploaded yet."}

    proof_url = (booking.balance_proof_url or booking.payment_proof_url).lstrip("/")
    proof_path = os.path.join(os.getcwd(), proof_url)
    
    if not os.path.exists(proof_path):
        # Fallback for 'app/' directory structure
        proof_path = os.path.join(os.getcwd(), "app", proof_url)

    if not os.path.exists(proof_path):
        return {"status": "error", "message": f"Proof file missing on server. Looking at: {proof_path}"}

    verify_results = payment_verification_service.check_for_fraud(db, booking, proof_path)
    booking.payment_verification_data = verify_results
    booking.proof_image_hash = payment_verification_service.get_image_hash(proof_path)
    db.commit()

    return {"status": "success", "data": verify_results}

@router.get("/api/bookings/{booking_id}/details")
async def get_booking_details_api(
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Fetch commission settings
    config = db.query(models.WebsiteConfig).first()
    comm_rate = config.commission_rate if config else 10.0
    comm_fixed = config.commission_fixed_amount if config else 20.0
    
    total = float(booking.total_amount or 0)
    commission = (total * (comm_rate / 100.0)) + comm_fixed
    net_amount = total - commission

    return {
        "id": booking.id,
        "event_name": booking.event_name,
        "event_type": booking.event_type,
        "total_amount": total,
        "commission": round(commission, 2),
        "net_amount": round(net_amount, 2),
        "commission_rate": comm_rate,
        "payment_status": booking.payment_status,
        "payment_method": booking.payment_method,
        "payment_proof_url": booking.payment_proof_url,
        "balance_proof_url": booking.balance_proof_url,
        "payment_verification_data": booking.payment_verification_data,
        "quotation_id": booking.quotation.id if booking.quotation else None,
        "contract_url": booking.quotation.contract_url if booking.quotation else None,
        "user": {
            "first_name": booking.user.first_name if booking.user else "Walk-in",
            "last_name": booking.user.last_name if booking.user else "Customer",
            "email": booking.user.email if booking.user else "N/A"
        },
        "is_package": booking.package_id is not None
    }

@router.get("/api/bookings/{booking_id}/history")
async def get_booking_history(
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    history = db.query(models.BookingHistory).filter_by(booking_id=booking_id).order_by(models.BookingHistory.created_at.desc()).all()
    
    results = []
    for h in history:
        results.append({
            "status": h.status,
            "notes": h.notes,
            "created_at_formatted": h.created_at.strftime("%b %d, %Y %I:%M %p")
        })
    return results

class BookingNotesSchema(BaseModel):
    notes: str

@router.post("/api/bookings/{booking_id}/notes")
async def update_booking_notes(
    booking_id: int,
    data: BookingNotesSchema,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking.caterer_notes = data.notes
    db.commit()
    return {"status": "success"}

@router.get("/api/bookings/{booking_id}/messages")
async def get_booking_messages(
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    messages = []
    for msg in booking.messages:
        messages.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "message": msg.message,
            "attachment_url": msg.attachment_url,
            "is_me": msg.sender_id == user.id,
            "created_at": msg.created_at.strftime('%b %d, %I:%M %p')
        })
    return {"status": "success", "messages": messages}


@router.get("/bookings/{booking_id}/quotation")
async def view_booking_quotation(
    request: Request,
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    """View the detailed quotation/invoice for a booking or create a proposal."""
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    
    quotation = booking.quotation
    if not quotation:
        # If it's a custom event or requires manual quote, show the Proposal Maker
        if booking.is_custom_event or booking.travel_fee_status == "manual_quote":
            return templates.TemplateResponse("caterer/proposal_maker.html", {
                "request": request,
                "booking": booking,
                "user": user
            })
            
        # Fallback if no quotation record exists
        quotation = {
            "total_amount": booking.total_amount,
            "package_details": {"name": booking.event_type},
            "addons": [],
            "status": "confirmed"
        }

    return templates.TemplateResponse("caterer/quotation_view.html", {
        "request": request,
        "booking": booking,
        "quotation": quotation,
        "user": user
    })

@router.post("/bookings/{booking_id}/proposal_maker")
async def submit_proposal_maker(
    booking_id: int,
    base_price: float = Form(...),
    total_amount: float = Form(...),
    downpayment_percent: int = Form(30),
    addon_names: List[str] = Form([]),
    addon_prices: List[float] = Form([]),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    """Submit a custom quotation/proposal from the caterer."""
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    if booking.quotation:
        raise HTTPException(status_code=400, detail="Quotation already exists")
        
    # Financial Constraint Enforcement
    # 1. Baseline Fees (₱150/head equipment fee)
    min_equipment_fee = booking.guest_count * 150.0
    
    # 2. Staffing Ratios (1 waiter per 20 guests, assuming ₱800 per waiter)
    waiters_needed = max(1, booking.guest_count // 20)
    min_staffing_fee = waiters_needed * 800.0
    
    absolute_minimum = min_equipment_fee + min_staffing_fee
    
    if total_amount < absolute_minimum:
        raise HTTPException(
            status_code=400, 
            detail=f"Total proposal amount (₱{total_amount}) is below the required absolute minimum (₱{absolute_minimum}) to cover baseline equipment and staffing costs."
        )
        
    # Build addons list
    addons = []
    for i in range(len(addon_names)):
        if addon_names[i].strip():
            addons.append({
                "name": addon_names[i].strip(),
                "price": addon_prices[i] if i < len(addon_prices) else 0.0
            })
            
    package_details = {
        "name": f"Custom Request: {booking.event_name or booking.event_type}",
        "unit_price": base_price / (booking.guest_count or 1),
        "base_amount": base_price,
        "guest_count": booking.guest_count,
        "description": booking.custom_requirements.get("theme_description", "") if booking.custom_requirements else ""
    }
    
    # Dynamic downpayment percent from caterer profile
    if user.caterer_profile.accepted_payment_terms:
        downpayment_percent = min(user.caterer_profile.accepted_payment_terms)
        
    quotation = models.Quotation(
        booking_id=booking.id,
        package_details=package_details,
        addons=addons,
        total_amount=total_amount,
        downpayment_percent=downpayment_percent,
        status="awaiting_customer" # The customer needs to accept it
    )
    db.add(quotation)
    
    booking.total_amount = total_amount
    booking.total_price = total_amount
    booking.reservation_fee = total_amount * (downpayment_percent / 100.0)
    booking.status = "awaiting_customer"
    
    db.commit()
    
    # Notify customer
    await NotificationService.notify_status_update(
        db, 
        booking.user_id, 
        "Proposal Received", 
        f"Caterer {user.caterer_profile.business_name} has submitted a proposal for your event.", 
        f"/bookings/step/quotation/{booking.id}"
    )
    
    return RedirectResponse(url=f"/caterer/bookings/{booking.id}/quotation", status_code=303)


@router.post("/bookings/{booking_id}/complete")
async def complete_booking(
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    """Mark a confirmed booking as completed."""
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status not in ['confirmed', 'paid']:
        raise HTTPException(status_code=400, detail="Only confirmed bookings can be marked as completed")

    # --- PHASE 3: COMPLETION GATING LOGIC ---
    has_equipment = False
    has_food = True if booking.package_id else False
    has_service = False
    
    for item in booking.selected_items:
        if getattr(item, 'equipment_id', None): has_equipment = True
        if getattr(item, 'menu_item_id', None): has_food = True
        if getattr(item, 'service_id', None): has_service = True
        
    if has_equipment and not booking.return_photo_url:
        return RedirectResponse(url=f"/caterer/bookings?error_msg=Cannot+complete+booking:+Equipment+Return+Inspection+is+required.", status_code=303)
        
    if has_food and not booking.dispatch_proof_url:
        return RedirectResponse(url=f"/caterer/bookings?error_msg=Cannot+complete+booking:+Food+Dispatch+verification+is+required.", status_code=303)

    booking.status = 'completed'
    booking.payment_status = 'paid'  # Mark as fully settled when event is completed

    history = models.BookingHistory(
        booking_id=booking.id,
        status='completed',
        notes="Event completed. Booking marked as completed by caterer."
    )
    db.add(history)

    # Automatically generate commission record
    config = db.query(models.WebsiteConfig).first()
    commission_rate = (config.commission_rate / 100.0) if config and config.commission_rate else 0.10
    commission_due = (booking.total_amount or 0.0) * commission_rate

    commission_record = models.BillingInvoice(
        caterer_id=booking.caterer_id,
        booking_id=booking.id,
        billing_period=booking.event_date.strftime('%B %Y') if booking.event_date else 'General',
        amount=commission_due,
        commission_rate=commission_rate,
        status='pending'
    )
    db.add(commission_record)
    
    db.commit()

    # Real-time alert to customer
    import asyncio
    asyncio.create_task(manager.broadcast_to_user(booking.user_id, {
        "type": "booking_update",
        "message": f"Your event '{booking.event_name}' has been marked as completed!",
        "booking_id": booking.id,
        "status": "completed"
    }))

    return RedirectResponse(url=f"/caterer/bookings?success_msg=Booking+marked+as+completed", status_code=303)


@router.post("/bookings/{booking_id}/actual-cost")
async def update_actual_cost(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.caterer_id == user.caterer_profile.id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    data = await request.json()
    actual_cost = data.get("actual_cost", 0)
    actual_cost_breakdown = data.get("actual_cost_breakdown", [])

    booking.actual_cost = actual_cost
    booking.actual_cost_breakdown = actual_cost_breakdown
    db.commit()

    return {"status": "success", "message": "Actual cost updated"}
@router.get("/reviews", response_class=HTMLResponse)
async def caterer_reviews(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    all_reviews = user.caterer_profile.reviews
    total_reviews = len(all_reviews)
    avg_rating = sum(r.rating for r in all_reviews) / total_reviews if total_reviews > 0 else 0
    
    # Rating categories (5 to 1 stars)
    rating_stats = {i: 0 for i in range(5, 0, -1)}
    for r in all_reviews:
        if r.rating in rating_stats:
            rating_stats[r.rating] += 1
            
    return templates.TemplateResponse("caterer/reviews.html", {
        "request": request,
        "user": user,
        "reviews": sorted(all_reviews, key=lambda x: x.created_at, reverse=True),
        "avg_rating": round(float(avg_rating), 1),
        "total_reviews": total_reviews,
        "rating_stats": rating_stats,
        "active_page": "reviews"
    })
@router.post("/reviews/{review_id}/reply")
async def post_review_reply(
    review_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    data = await request.json()
    reply_text = data.get("reply")
    
    review = db.query(models.Review).filter(
        models.Review.id == review_id,
        models.Review.caterer_id == user.caterer_profile.id
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    

@router.post("/reviews/{review_id}/helpful")
async def toggle_review_helpful(
    review_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    review = db.query(models.Review).filter(
        models.Review.id == review_id,
        models.Review.caterer_id == user.caterer_profile.id
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.is_helpful = not review.is_helpful
    db.commit()
    return {"status": "success", "is_helpful": review.is_helpful}

@router.get("/customers", response_class=HTMLResponse)
async def caterer_customers(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    
    # Get unique customers and their stats
    customer_ids = {b.user_id for b in user.caterer_profile.bookings if b.user and not b.user.email.startswith("walkin@")}
    customers = []
    
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    first_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    
    total_customers_count = len(customer_ids)
    vip_customers_count = 0
    new_customers_this_month_count = 0
    repeat_customers_count = 0
    
    if customer_ids:
        raw_customers = db.query(models.User).filter(
            models.User.id.in_(customer_ids)
        ).all()
        
        for c in raw_customers:
            # Stats for this customer relative to THIS caterer
            all_bookings = db.query(models.Booking).filter(
                models.Booking.user_id == c.id,
                models.Booking.caterer_id == user.caterer_profile.id
            ).order_by(models.Booking.event_date.desc()).all()
            
            bookings_count = len(all_bookings)
            total_spent = sum(b.total_price for b in all_bookings if b.status == 'completed')
            last_booking = all_bookings[0] if all_bookings else None
            first_booking = all_bookings[-1] if all_bookings else None
            
            # Status Logic
            status = "REGULAR"
            if bookings_count >= 3:
                status = "VIP"
                vip_customers_count += 1
            
            if first_booking and first_booking.created_at >= first_of_month:
                status = "NEW"
                new_customers_this_month_count += 1
            
            if bookings_count > 1:
                repeat_customers_count += 1
            
            # Attach attributes for template
            c.total_bookings = bookings_count
            c.total_spent = total_spent
            c.last_booking_date = last_booking.event_date if last_booking else None
            c.status = status
            customers.append(c)

    repeat_rate = round((repeat_customers_count / total_customers_count * 100), 1) if total_customers_count > 0 else 0

    return templates.TemplateResponse("caterer/customers.html", {
        "request": request,
        "user": user,
        "customers": customers,
        "stats": {
            "total": total_customers_count,
            "vip": vip_customers_count,
            "new": new_customers_this_month_count,
            "repeat": f"{repeat_rate}%"
        },
        "primary_color": user.caterer_profile.primary_color or "#3b82f6",
        "active_page": "customers",
        "today": now

    })

@router.get("/api/payments/summary")
async def payments_summary_api(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    """Real-time summary of payment card totals — used by JS polling."""
    from datetime import datetime, timezone
    profile = user.caterer_profile
    bookings = [b for b in profile.bookings if b.status not in ['draft', 'pending_review'] and not b.is_archived]

    # Post-paid variables
    outstanding_balance = profile.outstanding_balance or 0.0
    lifetime_revenue = 0.0
    active_count = 0
    total_commission_paid = 0.0
    
    # Calculate lifetime_revenue and active_count
    for b in bookings:
        if b.status in ('cancelled', 'rejected'):
            continue
        if b.status != 'completed':
            active_count += 1
            
        gross_amount = float(b.total_amount or b.total_price or 0)
        if b.payment_status == 'paid' and b.status == 'completed':
            lifetime_revenue += gross_amount
            
    # Calculate commission paid
    invoices = db.query(models.BillingInvoice).filter(
        models.BillingInvoice.caterer_id == profile.id,
        models.BillingInvoice.status == 'paid'
    ).all()
    
    for inv in invoices:
        total_commission_paid += float(inv.amount)
        
    return JSONResponse({
        "ready_total": round(outstanding_balance, 2), # Using ready_total key for outstanding_balance frontend
        "released_total": round(lifetime_revenue, 2), # Using released_total key for lifetime_revenue frontend
        "escrow_total": round(total_commission_paid, 2), # Using escrow_total key for commission_paid frontend
        "active_count": active_count,
        "last_updated": datetime.now(timezone.utc).isoformat()
    })

@router.get("/api/roi-analytics")

async def caterer_roi_analytics(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    from datetime import datetime
    import calendar
    from dateutil.relativedelta import relativedelta

    # Get last 6 months list
    now = datetime.now()
    months_labels = []
    projected_revenue = []
    actual_costs = []
    projected_costs = []

    for i in range(5, -1, -1):
        target_month = now - relativedelta(months=i)
        month_label = target_month.strftime("%b %Y")
        months_labels.append(month_label)
        
        # Calculate stats for this month
        month_bookings = db.query(models.Booking).filter(
            models.Booking.caterer_id == user.caterer_profile.id,
            models.Booking.status == 'completed',
            func.extract('month', models.Booking.event_date) == target_month.month,
            func.extract('year', models.Booking.event_date) == target_month.year
        ).all()
        
        config = db.query(models.WebsiteConfig).first()
        comm_rate = config.commission_rate if config else 10.0
        comm_fixed = config.commission_fixed_amount if config else 20.0

        gross_rev = sum(b.total_amount or b.total_price or 0 for b in month_bookings)
        
        total_commission = 0
        for b in month_bookings:
            b_total = b.total_amount or b.total_price or 0
            total_commission += (b_total * (comm_rate / 100.0)) + comm_fixed

        net_rev = gross_rev - total_commission

        act_cost = sum(b.actual_cost or 0 for b in month_bookings)

        month_expenses = db.query(models.BusinessExpense).filter(
            models.BusinessExpense.caterer_id == user.caterer_profile.id,
            func.extract('month', models.BusinessExpense.date_incurred) == target_month.month,
            func.extract('year', models.BusinessExpense.date_incurred) == target_month.year
        ).all()
        overhead_cost = sum(e.amount for e in month_expenses)
        
        total_act_cost = act_cost + overhead_cost
        
        proj_cost = 0
        for b in month_bookings:
            c = 0
            if b.package:
                c += (b.package.cost_price or 0) * (b.guest_count if b.package.price_unit == 'per_guest' else 1)
            for item in b.selected_items:
                c += (item.menu_item.cost_price or 0)
            proj_cost += c
            
        projected_revenue.append(float(net_rev))
        actual_costs.append(float(total_act_cost))
        projected_costs.append(float(proj_cost))

    return {
        "labels": months_labels,
        "revenue": projected_revenue,
        "actual_costs": actual_costs,
        "projected_costs": projected_costs
    }

@router.get("/calendar", response_class=HTMLResponse)
async def caterer_calendar(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    from datetime import date, timedelta
    current_date = date.today()
    lead_time_days = user.caterer_profile.booking_lead_time or 7
    min_booking_date = current_date + timedelta(days=lead_time_days)
    max_advance_days = user.caterer_profile.scheduling_rules.get("max_advance_booking_days", 730) if user.caterer_profile.scheduling_rules else 730
    max_booking_date = current_date + timedelta(days=max_advance_days)
    
    # For the list view on the side (Status Tracker) - Show active non-completed bookings first
    tracker_bookings = db.query(models.Booking).filter(
        models.Booking.caterer_id == user.caterer_profile.id,
        models.Booking.status.in_(['confirmed', 'preparing', 'ready_for_delivery', 'on_the_way', 'arrived', 'setup_ongoing']),
        models.Booking.is_archived == False
    ).order_by(models.Booking.event_date.asc()).all()
    # For the walk-in form options
    packages = db.query(models.CateringPackage).filter(
        models.CateringPackage.caterer_id == user.caterer_profile.id,
        models.CateringPackage.is_active == True,
        models.CateringPackage.status != 'archived'
    ).all()
    
    menu_items = db.query(models.MenuItem).filter(
        models.MenuItem.caterer_id == user.caterer_profile.id,
        models.MenuItem.is_archived == False
    ).all()
    
    return templates.TemplateResponse("caterer/calendar.html", {
        "request": request,
        "user": user,
        "bookings": tracker_bookings,
        "current_date": current_date,
        "packages": packages,
        "menu_items": menu_items,
        "max_bookings_per_day": user.caterer_profile.max_bookings_per_day or 1,
        "auto_block_enabled": user.caterer_profile.auto_block_enabled if user.caterer_profile.auto_block_enabled is not None else True,
        "primary_color": user.caterer_profile.primary_color or "#3b82f6",
        "booking_lead_time": lead_time_days,
        "min_booking_date": min_booking_date,
        "max_booking_date": max_booking_date,
        "business_open": user.caterer_profile.scheduling_rules.get("business_hours", {}).get("open_time", "08:00") if user.caterer_profile.scheduling_rules else "08:00",
        "business_close": user.caterer_profile.scheduling_rules.get("business_hours", {}).get("close_time", "20:00") if user.caterer_profile.scheduling_rules else "20:00",
        "min_pax": user.caterer_profile.min_pax or 20,
        "active_page": "calendar"
    })

@router.get("/packages", response_class=HTMLResponse)
async def manage_packages(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    active_packages = [p for p in profile.packages if p.status != 'archived']
    
    # Filter menu items (Dishes)
    service_cats = ['Rentals', 'Services', 'Event Styling', 'Event Rental', 'Entertainment', 'Event Coordination', 'Food Cart', 'Equipment Rental', 'Staffing Services', 'Packages']
    active_menu = [m for m in profile.menu_items if not m.is_archived and m.category not in service_cats and (getattr(m, 'usage_type', 'both') != 'order_only' or getattr(m, 'is_addon', False))]
    
    # Compile Inventory & Services
    equipment_items = [e for e in profile.equipment_items if not e.is_archived and e.status == 'available' and (getattr(e, 'usage_type', 'both') != 'order_only' or getattr(e, 'is_addon', False))]
    service_items = [s for s in profile.service_items if not s.is_archived and s.status == 'available' and (getattr(s, 'usage_type', 'both') != 'order_only' or getattr(s, 'is_addon', False))]
    legacy_items = [m for m in profile.menu_items if not m.is_archived and m.status == 'available' and m.category in service_cats and (getattr(m, 'usage_type', 'both') != 'order_only' or getattr(m, 'is_addon', False))]
    
    # Unify them into a dictionary format compatible with the template
    active_services = []
    for e in equipment_items:
        active_services.append({
            "id": f"eq_{e.id}",
            "real_id": e.id,
            "type": "Equipment",
            "name": e.name,
            "category": e.category,
            "cost_price": e.cost_value,
            "image_url": e.image_url,
            "is_addon": e.is_addon
        })
    for s in service_items:
        active_services.append({
            "id": f"svc_{s.id}",
            "real_id": s.id,
            "type": "Service",
            "name": s.name,
            "category": s.category,
            "cost_price": s.cost,
            "image_url": s.image_url,
            "is_addon": s.is_addon
        })
    for m in legacy_items:
        active_services.append({
            "id": m.id, # legacy uses int ID
            "real_id": m.id,
            "type": "Legacy",
            "name": m.name,
            "category": m.category,
            "cost_price": m.cost_price,
            "image_url": m.image_url,
            "is_addon": m.is_addon
        })
        
    return templates.TemplateResponse("caterer/packages.html", {
        "request": request,
        "user": user,
        "packages": active_packages,
        "menu_items": active_menu,
        "services": active_services,
        "active_page": "packages"
    })

@router.get("/menu", response_class=HTMLResponse)
async def manage_menu(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    service_cats = ['Rentals', 'Services', 'Event Styling', 'Event Rental', 'Entertainment', 'Event Coordination', 'Food Cart', 'Equipment Rental', 'Staffing Services', 'Packages']
    active_menu = [m for m in user.caterer_profile.menu_items if not m.is_archived and m.category not in service_cats]
    return templates.TemplateResponse("caterer/menu.html", {
        "request": request,
        "user": user,
        "menu_items": active_menu,
        "active_page": "menu"
    })

@router.get("/services", response_class=HTMLResponse)
async def manage_services(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    equipment_items = [e for e in user.caterer_profile.equipment_items if not e.is_archived]
    service_items = [s for s in user.caterer_profile.service_items if not s.is_archived]
    
    # Legacy items in menu_items table
    service_cats = ['Rentals', 'Services', 'Event Styling', 'Event Rental', 'Entertainment', 'Event Coordination', 'Food Cart', 'Equipment Rental', 'Staffing Services', 'Packages']
    legacy_items = [m for m in user.caterer_profile.menu_items if not m.is_archived and m.category in service_cats]
    
    # Unify them for the frontend
    items = []
    for e in equipment_items:
        items.append({
            "id": e.id,
            "item_type": e.equipment_type or "Equipment",
            "name": e.name,
            "category": e.category,
            "description": e.description,
            "price": e.rental_price,
            "cost_price": e.cost_value,
            "unit_type": e.unit_type,
            "available_qty": e.available_qty,
            "status": e.status,
            "is_hidden": e.is_hidden,
            "usage_type": getattr(e, "usage_type", "both"),
            "is_addon": getattr(e, "is_addon", False),
            "addon_price": getattr(e, "addon_price", 0.0),
            "image_url": e.image_url
        })
    for s in service_items:
        items.append({
            "id": s.id,
            "item_type": "Service",
            "name": s.name,
            "category": s.category,
            "description": s.description,
            "price": s.selling_price,
            "cost_price": s.cost,
            "unit_type": s.unit_type,
            "available_qty": s.max_available,
            "status": s.status,
            "is_hidden": s.is_hidden,
            "usage_type": getattr(s, "usage_type", "both"),
            "is_addon": getattr(s, "is_addon", False),
            "addon_price": getattr(s, "addon_price", 0.0),
            "image_url": s.image_url
        })
    for m in legacy_items:
        items.append({
            "id": m.id,
            "item_type": "Legacy",
            "name": m.name,
            "category": m.category,
            "description": m.description,
            "price": m.price,
            "cost_price": m.cost_price,
            "unit_type": m.pricing_unit,
            "available_qty": m.max_stock_quantity or 1,
            "status": "unavailable" if m.is_hidden else "available",
            "is_hidden": m.is_hidden,
            "usage_type": getattr(m, "usage_type", "both"),
            "is_addon": getattr(m, "is_addon", False),
            "addon_price": getattr(m, "addon_price", 0.0),
            "image_url": m.image_url
        })

    return templates.TemplateResponse("caterer/services.html", {
        "request": request,
        "user": user,
        "items": items,
        "active_page": "services"
    })

@router.post("/services/add")
async def add_service_item(
    request: Request,
    type: str = Form(...),
    name: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(0.0),
    cost_price: float = Form(0.0),
    unit_type: str = Form("Per Event"),
    available_qty: int = Form(1),
    status: str = Form("available"),
    visibility: str = Form("public"),
    usage_type: str = Form("both"),
    is_addon: bool = Form(False),
    addon_price: float = Form(0.0),
    base_duration_hours: int = Form(3),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    import base64
    image_url = None
    if image and image.filename:
        try:
            content_bytes = await image.read()
            if content_bytes:
                image_url = process_base64_image(content_bytes)
        except Exception:
            pass

    if type in ["Equipment", "Decoration"]:
        new_item = models.Equipment(
            caterer_id=user.caterer_profile.id,
            equipment_type=type,
            name=name,
            category=category,
            description=description,
            rental_price=price,
            cost_value=cost_price,
            unit_type=unit_type,
            available_qty=available_qty,
            status=status,
            is_hidden=(visibility == "hidden"),
            usage_type=usage_type,
            is_addon=is_addon,
            addon_price=addon_price,
            image_url=image_url
        )
    else:
        new_item = models.Service(
            caterer_id=user.caterer_profile.id,
            name=name,
            category=category,
            description=description,
            selling_price=price,
            cost=cost_price,
            unit_type=unit_type,
            max_available=available_qty,
            status=status,
            is_hidden=(visibility == "hidden"),
            usage_type=usage_type,
            is_addon=is_addon,
            addon_price=addon_price,
            base_duration_hours=base_duration_hours,
            image_url=image_url
        )
        
    db.add(new_item)
    db.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Item added successfully"})
    return RedirectResponse(url="/caterer/services", status_code=303)

@router.post("/services/{item_id}/update")
async def update_service_item(
    item_id: int,
    request: Request,
    type: str = Form(...),
    name: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(0.0),
    cost_price: float = Form(0.0),
    unit_type: str = Form("Per Event"),
    available_qty: int = Form(1),
    status: str = Form("available"),
    visibility: str = Form("public"),
    usage_type: str = Form("both"),
    is_addon: bool = Form(False),
    addon_price: float = Form(0.0),
    base_duration_hours: int = Form(3),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    import base64
    image_url = None
    if image and image.filename:
        try:
            content_bytes = await image.read()
            if content_bytes:
                image_url = process_base64_image(content_bytes)
        except Exception:
            pass

    if type in ["Equipment", "Decoration"]:
        item = db.query(models.Equipment).get(item_id)
        if not item or item.caterer_id != user.caterer_profile.id:
            raise HTTPException(status_code=404, detail="Item not found")
        item.name = name
        item.category = category
        item.description = description
        item.rental_price = price
        item.cost_value = cost_price
        item.unit_type = unit_type
        item.available_qty = available_qty
        item.status = status
        item.is_hidden = (visibility == "hidden")
        item.usage_type = usage_type
        item.is_addon = is_addon
        item.addon_price = addon_price
        if image_url: item.image_url = image_url
    elif type == "Legacy":
        item = db.query(models.MenuItem).get(item_id)
        if not item or item.caterer_id != user.caterer_profile.id:
            raise HTTPException(status_code=404, detail="Item not found")
        item.name = name
        item.category = category
        item.description = description
        item.price = price
        item.cost_price = cost_price
        item.pricing_unit = unit_type
        item.max_stock_quantity = available_qty
        item.is_hidden = (visibility == "hidden")
        item.status = status
        item.usage_type = usage_type
        item.is_addon = is_addon
        item.addon_price = addon_price
        if image_url: item.image_url = image_url
    else:
        item = db.query(models.Service).get(item_id)
        if not item or item.caterer_id != user.caterer_profile.id:
            raise HTTPException(status_code=404, detail="Item not found")
        item.name = name
        item.category = category
        item.description = description
        item.selling_price = price
        item.cost = cost_price
        item.unit_type = unit_type
        item.max_available = available_qty
        item.status = status
        item.is_hidden = (visibility == "hidden")
        item.usage_type = usage_type
        item.is_addon = is_addon
        item.addon_price = addon_price
        item.base_duration_hours = base_duration_hours
        if image_url: item.image_url = image_url

    db.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Item updated successfully"})
    return RedirectResponse(url="/caterer/services", status_code=303)

@router.post("/services/{item_id}/archive")
async def archive_service_item(
    item_id: int,
    type: str,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    if type in ["Equipment", "Decoration"]:
        item = db.query(models.Equipment).get(item_id)
    elif type == "Legacy":
        item = db.query(models.MenuItem).get(item_id)
    else:
        item = db.query(models.Service).get(item_id)
        
    if not item or item.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Item not found")
        
    item.is_archived = True
    db.commit()
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Item archived successfully"})
    return RedirectResponse(url="/caterer/services", status_code=303)


@router.get("/profile", response_class=HTMLResponse)
@router.get("/settings", response_class=HTMLResponse)
async def edit_profile(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    identity = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == user.id).first()
    return templates.TemplateResponse("caterer/profile_edit.html", {
        "request": request,
        "user": user,
        "profile": user.caterer_profile,
        "identity": identity,
        "active_page": "settings"
    })

@router.post("/packages/add")
async def add_package(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    service_type: str = Form("General"),
    pricing_mode: str = Form("per_pax"),
    service_duration: int = Form(8),
    price_per_head: float = Form(0.0),
    cost_price: float = Form(0.0),
    cost_breakdown: Optional[str] = Form(None),
    markup_type: str = Form("percentage"),
    markup_value: float = Form(0.0),
    min_contract_amount: float = Form(0.0),
    min_guests: int = Form(1),
    max_guests: Optional[str] = Form(None),
    inclusions: Optional[List[str]] = Form(None),
    linked_menu_ids: Optional[List[str]] = Form(None),
    additional_guest_price: float = Form(0.0),
    image: Optional[UploadFile] = File(None),
    base_pax: int = Form(50),
    labor_cost: float = Form(0.0),
    utility_cost: float = Form(0.0),
    equipment_cost: float = Form(0.0),
    transportation_cost: float = Form(0.0),
    miscellaneous_cost: float = Form(0.0),
    internal_cost_per_pax: float = Form(0.0),
    reservation_fee_type: str = Form("fixed"),
    reservation_fee_value: float = Form(0.0),
    booking_lead_time: int = Form(7),
    selection_rules: Optional[str] = Form(None),
    status: str = Form("active"),
    policies_cancellation: Optional[str] = Form(None),
    policies_internal: Optional[str] = Form(None),
    menu_addons: Optional[str] = Form(None),
    service_addons: Optional[str] = Form(None),
    equipment_addons: Optional[str] = Form(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    errors = []
    
    # Inject Global Settings for Operational Costs and Reservation
    labor_cost = user.caterer_profile.default_labor_cost or 0.0
    utility_cost = user.caterer_profile.default_utility_cost or 0.0
    transportation_cost = user.caterer_profile.default_transport_cost or 0.0
    reservation_fee_type = user.caterer_profile.default_reservation_type or "fixed"
    reservation_fee_value = user.caterer_profile.default_reservation_value or 0.0
    
    if not name.strip():
        errors.append("Package name is required.")
    # Removed mandatory menu item selection to allow optional packages
    if price_per_head <= 0:
        errors.append("Price per head must be greater than 0.")
    global_min_pax = user.caterer_profile.min_pax or 20
    if min_guests < global_min_pax:
        errors.append(f"Minimum guests cannot be lower than your global setting of {global_min_pax}.")
        
    global_lead_time = user.caterer_profile.booking_lead_time or 7
    if booking_lead_time < global_lead_time:
        errors.append(f"Booking lead time cannot be lower than your global setting of {global_lead_time} days.")
    if reservation_fee_value <= 0 and price_per_head > 0:
        pass # Optional warning: errors.append("Reservation fee must be greater than 0.")
    elif reservation_fee_type == 'fixed' and price_per_head > 0 and min_guests > 0 and pricing_mode == 'per_pax':
        max_allowed_fee = (price_per_head * min_guests) * 0.5
        if reservation_fee_value > max_allowed_fee:
            errors.append(f"Reservation fee cannot exceed 50% of the total base package cost.")


    # Smart Validation: Detect existing package with the same name
    existing_pkg = db.query(models.CateringPackage).filter(
        models.CateringPackage.caterer_id == user.caterer_profile.id,
        models.CateringPackage.name.ilike(name.strip())
    ).first()
    
    if existing_pkg:
        errors.append(f"A package named '{name}' already exists in your library.")
        
    if errors:
        error_msg = " | ".join(errors)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse({"status": "error", "message": error_msg}, status_code=400)
        return RedirectResponse(url=f"/caterer/packages?error_msg={error_msg}", status_code=303)

    import base64
    image_url = None
    if image and image.filename:
        try:
            content_bytes = await image.read()
            if content_bytes:
                image_url = process_base64_image(content_bytes)
        except Exception:
            pass

    new_pkg = models.CateringPackage(
        caterer_id=user.caterer_profile.id,
        name=name,
        description=description,
        service_type=service_type,
        pricing_mode=pricing_mode,
        service_duration=service_duration,
        price_per_head=price_per_head,
        price=price_per_head, # Sync for compatibility
        cost_price=cost_price,
        cost_breakdown=json.loads(cost_breakdown) if cost_breakdown else [],
        markup_type=markup_type,
        markup_value=markup_value,
        min_contract_amount=min_contract_amount,
        min_guests=min_guests,
        max_guests=int(max_guests) if max_guests and str(max_guests).strip() else None,
        image_url=image_url,
        inclusions={inc: True for inc in inclusions} if inclusions else {},
        base_pax=base_pax,
        additional_guest_price=additional_guest_price,
        labor_cost=user.caterer_profile.default_labor_cost or 0.0,
        utility_cost=user.caterer_profile.default_utility_cost or 0.0,
        equipment_cost=equipment_cost,
        transportation_cost=user.caterer_profile.default_transport_cost or 0.0,
        miscellaneous_cost=miscellaneous_cost,
        internal_cost_per_pax=internal_cost_per_pax,
        reservation_fee_type=reservation_fee_type,
        reservation_fee_value=reservation_fee_value,
        booking_lead_time=booking_lead_time,
        selection_rules=json.loads(selection_rules) if selection_rules else None,
        policies={"cancellation": policies_cancellation, "internal": policies_internal},
        is_active=status == 'active',
        status=status
    )
    
    # Handle linked items
    if linked_menu_ids:
        db.add(new_pkg)
        db.flush()
        
        menu_ids = []
        eq_data = []
        svc_data = []
        for i in set(linked_menu_ids):
            qty = 1
            if '_q' in i:
                parts = i.split('_q')
                i = parts[0]
                try: qty = int(parts[1])
                except: pass
                
            if i.startswith('eq_'): eq_data.append((int(i.replace('eq_', '')), qty))
            elif i.startswith('svc_'): svc_data.append((int(i.replace('svc_', '')), qty))
            elif i.startswith('leg_'): menu_ids.append(int(i.replace('leg_', '')))
            else:
                try: menu_ids.append(int(i))
                except: pass
                
        if menu_ids:
            items = db.query(models.MenuItem).filter(models.MenuItem.id.in_(menu_ids)).all()
            new_pkg.menu_items = items
            
        if eq_data:
            for eid, qty in eq_data:
                db.add(models.PackageEquipment(package_id=new_pkg.id, equipment_id=eid, quantity=qty))
                
        if svc_data:
            for sid, qty in svc_data:
                db.add(models.PackageService(package_id=new_pkg.id, service_id=sid, quantity=qty))
    else:
        db.add(new_pkg)
        db.flush()
        
    # Save addons
    try:
        import json
        if menu_addons:
            for ma in json.loads(menu_addons):
                db.add(models.PackageMenuAddon(package_id=new_pkg.id, menu_item_id=int(str(ma['id']).replace('leg_', '')), price=float(ma['price']), selection_type=ma.get('selection_type', 'single'), min_quantity=ma.get('min_quantity', 1), max_quantity=ma.get('max_quantity')))
        if service_addons:
            for sa in json.loads(service_addons):
                db.add(models.PackageServiceAddon(package_id=new_pkg.id, service_id=int(str(sa['id']).replace('svc_', '')), price=float(sa['price']), selection_type=ma.get('selection_type', 'single'), min_quantity=sa.get('min_quantity', 1), max_quantity=sa.get('max_quantity')))
        if equipment_addons:
            for ea in json.loads(equipment_addons):
                db.add(models.PackageEquipmentAddon(package_id=new_pkg.id, equipment_id=int(str(ea['id']).replace('eq_', '')), price=float(ea['price']), min_quantity=ea.get('min_quantity', 1), max_quantity=ea.get('max_quantity')))
    except Exception as e:
        pass

    db.commit()
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({
            "status": "success", 
            "message": "Package added successfully", 
            "package_id": new_pkg.id,
            "package_name": new_pkg.name
        })

    return RedirectResponse(url="/caterer/packages?success_msg=Package+added+successfully", status_code=303)

@router.post("/packages/{package_id}/toggle")
async def toggle_package_status(
    package_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    package.is_active = not package.is_active
    db.commit()
    return {"status": "success", "is_active": package.is_active}

@router.post("/menu/add")
async def add_menu_item(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    form_data = await request.form()
    
    name = form_data.get("name")
    category = form_data.get("category")
    if category == "Other":
        category = form_data.get("custom_category") or "Other"
    
    description = form_data.get("description")
    status = form_data.get("status", "available")
    
    # New V2.0 Fields
    usage_type = form_data.get("usage_type", "both")
    available_for_package = usage_type in ["package_only", "both"]
    available_for_order = usage_type in ["order_only", "both"]
    
    pricing_mode = form_data.get("pricing_mode", "single")
    pricing_type = pricing_mode # Save as pricing_type for backwards compatibility

    price = 0.0
    serving_size = None
    if not (usage_type == "package_only") and pricing_mode == "single":
        try:
            price = float(form_data.get("price", "0").replace(",", ""))
        except ValueError:
            price = 0.0
        serving_size = form_data.get("serving_size")

    if not (usage_type == "package_only"):
        min_order_qty = int(form_data.get("min_order_qty", "1") or "1")
    else:
        min_order_qty = 1
    
    is_hidden = form_data.get("visibility") == "hidden"
    
    is_addon = False
    addon_price = 0.0
    cost_price = 0.0
    item_type = form_data.get("item_type", "single")
    is_combo = (item_type == "preset_combo")
    included_dishes = form_data.getlist("included_dishes[]")
    combo_options = {"included_menu_ids": [int(x) for x in included_dishes if x.isdigit()]} if is_combo else {}
    max_choices = 0
    
    dietary_tags = form_data.getlist("dietary_tags")
    allergen_info = form_data.getlist("allergen_info")
    serving_style = form_data.get("serving_style")
    
    image = form_data.get("image")
    import base64
    image_url = None
    if image and hasattr(image, "filename") and image.filename:
        try:
            content_bytes = await image.read()
            if content_bytes:
                image_url = process_base64_image(content_bytes)
        except Exception:
            pass

    pricing_unit = pricing_type

    new_item = models.MenuItem(
        caterer_id=user.caterer_profile.id,
        name=name,
        category=category,
        description=description,
        cost_price=cost_price,
        price=price,
        pricing_unit=pricing_unit,
        serving_size=serving_size,
        min_order_qty=min_order_qty,
        status=status,
        usage_type=usage_type,
        available_for_package=available_for_package,
        available_for_order=available_for_order,
        pricing_type=pricing_type,
        is_hidden=is_hidden,
        is_addon=is_addon,
        addon_price=addon_price,
        dietary_tags=dietary_tags,
        allergen_info=allergen_info,
        image_url=image_url,
        is_combo=is_combo,
        max_choices=max_choices,
        combo_options=combo_options,
        serving_style=serving_style,
        is_archived=False
    )
    db.add(new_item)
    db.flush() # To get new_item.id

    if not (usage_type == "package_only") and pricing_mode == "variants":
        v_names = form_data.getlist("variant_names[]")
        v_prices = form_data.getlist("variant_prices[]")
        v_servings = form_data.getlist("variant_servings[]")
        v_statuses = form_data.getlist("variant_statuses[]")

        for i, name in enumerate(v_names):
            if name.strip():
                try:
                    v_price = float(v_prices[i].replace(",", ""))
                except:
                    v_price = 0.0
                serving = v_servings[i].strip() if i < len(v_servings) else None
                v_status = v_statuses[i] if i < len(v_statuses) else 'available'
                
                variant = models.MenuVariant(
                    menu_item_id=new_item.id,
                    variant_name=name.strip(),
                    measurement=None,
                    price=v_price,
                    serving_capacity=serving,
                    status=v_status,
                    display_order=i
                )
                db.add(variant)

    db.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({
            "status": "success", 
            "message": "Dish added successfully", 
            "item_id": new_item.id,
            "item_name": new_item.name
        })

    return RedirectResponse(url="/caterer/menu?success_msg=Dish+added+successfully", status_code=303)

@router.post("/api/validate-dish-name")
async def validate_dish_name(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    try:
        data = await request.json()
        name = data.get("value", "").strip()
        exclude_id = data.get("exclude_id")

        if not name:
            return JSONResponse({"valid": True})

        query = db.query(models.MenuItem).filter(
            models.MenuItem.caterer_id == user.caterer_profile.id,
            models.MenuItem.name.ilike(name),
            models.MenuItem.is_archived == False
        )
        
        if exclude_id and str(exclude_id).isdigit():
            query = query.filter(models.MenuItem.id != int(exclude_id))

        exists = query.first() is not None
        
        return JSONResponse({
            "valid": not exists,
            "message": "This dish name is already in your library." if exists else ""
        })
    except Exception as e:
        return JSONResponse({"valid": True}) # Default to true on error so we don't block


@router.post("/profile")
async def update_profile(
    request: Request,
    business_name: str = Form(...),
    description: str = Form(...),
    city: Optional[str] = Form(None),
    contact_phone: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    middle_name: Optional[str] = Form(None),
    personal_address: Optional[str] = Form(None),
    logo: Optional[UploadFile] = File(None),
    logo_brand: Optional[UploadFile] = File(None),
    cover_image: Optional[UploadFile] = File(None),
    gcash_number: Optional[str] = Form(None),
    gcash_qr: Optional[UploadFile] = File(None),
    maya_number: Optional[str] = Form(None),
    maya_qr: Optional[UploadFile] = File(None),
    bank_name: Optional[str] = Form(None),
    bank_account_name: Optional[str] = Form(None),
    bank_account_number: Optional[str] = Form(None),
    bank_qr: Optional[UploadFile] = File(None),
    card_bank: Optional[str] = Form(None),
    card_holder_name: Optional[str] = Form(None),
    card_number: Optional[str] = Form(None),
    cash_instructions: Optional[str] = Form(None),
    booking_lead_time: Optional[str] = Form("7"),
    equipment_turnover_hours: Optional[str] = Form("24"),
    min_pax: Optional[str] = Form("20"),
    starting_price: Optional[str] = Form("0.0"),
    terms_and_conditions: Optional[str] = Form(None),
    general_terms: Optional[str] = Form(None),
    payment_terms: List[str] = Form(default=["100"]),
    default_labor_cost: Optional[str] = Form("0.0"),
    default_utility_cost: Optional[str] = Form("0.0"),
    default_transport_cost: Optional[str] = Form("0.0"),
    default_reservation_type: str = Form("fixed"),
    default_reservation_value: Optional[str] = Form("0.0"),
    primary_color: Optional[str] = Form(None),
    secondary_color: Optional[str] = Form(None),
    accent_color: Optional[str] = Form(None),
    highlight_color: Optional[str] = Form(None),
    font_family: Optional[str] = Form(None),
    border_radius: str = Form("12"),
    sidebar_mode: str = Form("full"),
    show_platform_logo: bool = Form(True),
    dashboard_texture: str = Form("none"),
    latitude: Optional[str] = Form(None),
    longitude: Optional[str] = Form(None),
    years_of_operation: Optional[int] = Form(None),
    contact_address: Optional[str] = Form(None),
    payout_method: Optional[str] = Form(None),
    province: Optional[str] = Form(None),
    municipality: Optional[str] = Form(None),
    barangay: Optional[str] = Form(None),
    province_code: Optional[str] = Form(None),
    city_code: Optional[str] = Form(None),
    brgy_code: Optional[str] = Form(None),
    base_delivery_fee: Optional[float] = Form(150.0),
    out_of_coverage_action: Optional[str] = Form("reject"),
    gallery: List[UploadFile] = File(default=[]),
    permit_file: Optional[UploadFile] = File(None),
    business_hours_open_time: Optional[str] = Form("08:00"),
    business_hours_close_time: Optional[str] = Form("20:00"),
    operating_days: List[str] = Form(default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]),
    food_delivery_start: Optional[str] = Form("09:00"),
    food_delivery_end: Optional[str] = Form("19:00"),
    food_lead_time_hours: Optional[int] = Form(24),
    food_allow_same_day: Optional[bool] = Form(False),
    equipment_pickup_start: Optional[str] = Form("08:00"),
    equipment_pickup_end: Optional[str] = Form("18:00"),
    equipment_min_rental: Optional[int] = Form(24),
    equipment_max_rental: Optional[int] = Form(72),
    service_earliest_start: Optional[str] = Form("08:00"),
    service_latest_end: Optional[str] = Form("22:00"),
    service_min_duration: Optional[int] = Form(3),
    service_max_duration: Optional[int] = Form(8),
    package_min_duration: Optional[int] = Form(4),
    package_max_duration: Optional[int] = Form(6),
    package_setup_time: Optional[int] = Form(2),
    package_cleanup_time: Optional[int] = Form(1),
    refund_policy: Optional[str] = Form(None),
    reschedule_policy: Optional[str] = Form(None),
    late_payment_policy: Optional[str] = Form(None),
    no_show_policy: Optional[str] = Form(None),
    social_facebook: Optional[str] = Form(None),
    social_instagram: Optional[str] = Form(None),
    social_website: Optional[str] = Form(None),
    holiday_schedule: Optional[str] = Form(None),
    max_advance_booking_days: Optional[int] = Form(365),
    business_tags: Optional[str] = Form(None),
    specialties: Optional[str] = Form(None),
    languages: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile

    # Update Universal Scheduling Rules
    profile.scheduling_rules = {
        "business_hours": {"open_time": business_hours_open_time, "close_time": business_hours_close_time, "operating_days": operating_days},
        "food_rules": {
            "delivery_available": True, "pickup_available": True, 
            "delivery_start": food_delivery_start, "delivery_end": food_delivery_end, 
            "lead_time_hours": food_lead_time_hours, "allow_same_day": bool(food_allow_same_day)
        },
        "equipment_rules": {
            "pickup_start": equipment_pickup_start, "pickup_end": equipment_pickup_end, 
            "return_start": equipment_pickup_start, "return_end": equipment_pickup_end, 
            "min_rental_hours": equipment_min_rental, "max_rental_hours": equipment_max_rental
        },
        "service_rules": {
            "min_duration_hours": service_min_duration, "max_duration_hours": service_max_duration, 
            "earliest_start": service_earliest_start, "latest_end": service_latest_end
        },
        "package_rules": {
            "min_event_duration": package_min_duration, "max_event_duration": package_max_duration, 
            "setup_time_hours": package_setup_time, "cleanup_time_hours": package_cleanup_time
        },
        "booking_rules": {
            "max_advance_booking_days": max_advance_booking_days,
            "holiday_schedule": holiday_schedule
        },
        "policies": {
            "refund_policy": refund_policy,
            "reschedule_policy": reschedule_policy,
            "late_payment_policy": late_payment_policy,
            "no_show_policy": no_show_policy
        },
        "social_links": {
            "facebook": social_facebook,
            "instagram": social_instagram,
            "website": social_website
        },
        "public_profile": {
            "tags": business_tags,
            "specialties": specialties,
            "languages": languages
        }
    }

    # Update User Info
    user.first_name = first_name
    user.last_name = last_name
    user.middle_name = middle_name
    user.address = personal_address

    # Update Profile Info
    profile.business_name = business_name
    profile.description = description
    if years_of_operation is not None:
        profile.years_of_operation = years_of_operation
    if city:
        profile.city = city
    if contact_address:
        profile.contact_address = contact_address
    profile.contact_phone = contact_phone
    profile.payout_method = payout_method
    profile.accepted_payment_terms = payment_terms

    # Update address components
    if province_code:
        profile.province_code = province_code
    if city_code:
        profile.city_code = city_code
    if brgy_code:
        profile.brgy_code = brgy_code

    # Save human-readable name parts
    if municipality and municipality != city_code:
        profile.city = municipality
    
    # Build a clean composite address_details from all parts
    # This becomes the single source of truth for display across all views
    addr_parts = []
    contact = contact_address.strip() if contact_address else ""
    if contact:
        addr_parts.append(contact)
    
    if barangay and barangay != brgy_code and barangay.lower() not in contact.lower():
        addr_parts.append(f"Brgy. {barangay}")
    if municipality and municipality != city_code and municipality.lower() not in contact.lower():
        addr_parts.append(municipality)
    if province and province != province_code and province.lower() not in contact.lower():
        addr_parts.append(province)
        
    if addr_parts:
        profile.address_details = ", ".join(addr_parts)
    # Update payment methods
    profile.gcash_number = gcash_number
    profile.maya_number = maya_number
    profile.bank_name = bank_name
    profile.bank_account_name = bank_account_name
    profile.bank_account_number = bank_account_number
    profile.card_bank = card_bank
    profile.card_holder_name = card_holder_name
    profile.card_number = card_number
    profile.cash_instructions = cash_instructions
    try:
        profile.booking_lead_time = int(booking_lead_time) if booking_lead_time else 7
        profile.equipment_turnover_hours = int(equipment_turnover_hours) if equipment_turnover_hours else 24
        profile.min_pax = int(min_pax) if min_pax else 20
        profile.starting_price = float(starting_price) if starting_price else 0.0
    except ValueError:
        pass
    profile.terms_and_conditions = terms_and_conditions
    profile.general_terms = general_terms
    try:
        profile.default_labor_cost = float(default_labor_cost) if default_labor_cost else 0.0
        profile.default_utility_cost = float(default_utility_cost) if default_utility_cost else 0.0
        profile.default_transport_cost = float(default_transport_cost) if default_transport_cost else 0.0
        profile.default_reservation_value = float(default_reservation_value) if default_reservation_value else 0.0
    except ValueError:
        pass
    profile.default_reservation_type = default_reservation_type
    
    if base_delivery_fee is not None:
        profile.base_delivery_fee = base_delivery_fee
    if out_of_coverage_action:
        profile.out_of_coverage_action = out_of_coverage_action

    # Update branding
    profile.primary_color = primary_color
    profile.secondary_color = secondary_color
    profile.accent_color = accent_color
    profile.highlight_color = highlight_color
    profile.font_family = font_family
    try:
        profile.border_radius = int(border_radius) if border_radius else 12
    except ValueError:
        pass
    profile.sidebar_mode = sidebar_mode
    profile.show_platform_logo = show_platform_logo
    profile.dashboard_texture = dashboard_texture

    if latitude and latitude.strip() != "":
        try:
            val = float(latitude)
            if val != 0.0:
                profile.latitude = val
        except ValueError:
            pass
    if longitude and longitude.strip() != "":
        try:
            val = float(longitude)
            if val != 0.0:
                profile.longitude = val
        except ValueError:
            pass

    import base64
    # Handle Single File Uploads
    logo_file = logo if (logo and logo.filename) else logo_brand
    # Size limits: logo/cover 400px, QR codes 300px, permit stored raw (PDF support)
    size_map = {"logo": (400, 400), "cover_image": (1200, 600), "gcash_qr": (300, 300), "maya_qr": (300, 300), "bank_qr": (300, 300)}
    for field_name, file_obj in [("logo", logo_file), ("cover_image", cover_image), ("gcash_qr", gcash_qr), ("maya_qr", maya_qr), ("bank_qr", bank_qr), ("permit", permit_file)]:
        if file_obj and file_obj.filename:
            try:
                content_bytes = await file_obj.read()
                if not content_bytes:
                    if field_name == 'permit':
                        return RedirectResponse(url="/caterer/profile?error_msg=The+uploaded+business+permit+file+is+empty.+Please+upload+a+valid+document.", status_code=303)
                    continue

                if field_name == 'permit':
                    import base64
                    # Permit may be PDF — store raw base64
                    mime = file_obj.content_type or "image/jpeg"
                    if mime.lower() not in ["image/png", "image/jpeg", "image/jpg", "application/pdf"]:
                        return RedirectResponse(url="/caterer/profile?error_msg=Invalid+business+permit+file+type.+Only+PNG,+JPEG,+and+PDF+are+allowed.", status_code=303)
                    
                    # Convert document directly to base64
                    b64 = base64.b64encode(content_bytes).decode('utf-8')
                    # Standardize mime if necessary
                    actual_mime = "application/pdf" if "pdf" in mime.lower() else "image/jpeg"
                    data_url = f"data:{actual_mime};base64,{b64}"
                    profile.permit_url = data_url
                    profile.permit_status = 'Pending Review'
                    profile.verification_status = 'Pending Review'
                    profile.is_verified = False
                    if profile.user:
                        profile.user.is_verified = False
                else:
                    max_size = size_map.get(field_name, (600, 600))
                    data_url = process_base64_image(content_bytes, max_size=max_size)
                    attr_name = 'logo_url' if field_name == 'logo' else f"{field_name}_url"
                    setattr(profile, attr_name, data_url)
                    if field_name == 'logo':
                        db_user = db.query(models.User).filter(models.User.id == user.id).first()
                        if db_user:
                            db_user.profile_image_url = data_url
            except Exception as e:
                import traceback
                print(f"[IMAGE UPLOAD ERROR] Failed on {field_name}: {str(e)}")
                traceback.print_exc()

    # Handle Gallery Uploads (Multiple)
    if gallery:
        for file_obj in gallery:
            if file_obj.filename:
                try:
                    content_bytes = await file_obj.read()
                    if content_bytes:
                        # Compress gallery images to 800x600 WebP
                        data_url = process_base64_image(content_bytes, max_size=(800, 600), quality=80)
                        new_gallery_item = models.CatererGallery(
                            caterer_id=profile.id,
                            media_url=data_url,
                            media_type="image"
                        )
                        db.add(new_gallery_item)
                except Exception as e:
                    import traceback
                    print(f"[GALLERY UPLOAD ERROR] Failed: {str(e)}")
                    traceback.print_exc()

    db.commit()
    from ..core import utils
    if background_tasks:
        background_tasks.add_task(utils.background_geocode, profile.id)
    return RedirectResponse(url="/caterer/profile?success_msg=Business+profile+updated+successfully", status_code=303)

@router.get("/packages/{package_id}/details")
async def get_package_details_api(
    package_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    return {
        "id": package.id,
        "name": package.name,
        "description": package.description,
        "service_type": package.service_type,
        "price_per_head": package.price_per_head,
        "cost_price": package.cost_price,
        "cost_breakdown": package.cost_breakdown or [],
        "markup_type": package.markup_type or 'percentage',
        "markup_value": package.markup_value or 0,
        "min_contract_amount": package.min_contract_amount,
        "min_guests": package.min_guests,
        "max_guests": package.max_guests,
        "service_duration": package.service_duration,
        "image_url": package.image_url,
        "inclusions": package.inclusions or {},
        "is_active": package.is_active,
        "pricing_mode": package.pricing_mode,
        "base_pax": package.base_pax,
        "labor_cost": package.labor_cost,
        "utility_cost": package.utility_cost,
        "equipment_cost": package.equipment_cost,
        "transportation_cost": package.transportation_cost,
        "miscellaneous_cost": package.miscellaneous_cost,
        "ingredient_total_cost": package.ingredient_total_cost,
        "internal_cost_per_pax": package.internal_cost_per_pax,
        "reservation_fee_type": package.reservation_fee_type,
        "reservation_fee_value": package.reservation_fee_value,
        "booking_lead_time": package.booking_lead_time,
        "additional_guest_price": package.additional_guest_price
    }

@router.post("/packages/{package_id}/update")
async def update_package(
    request: Request,
    package_id: int,
    name: str = Form(...),
    description: str = Form(...),
    service_type: str = Form("General"),
    pricing_mode: str = Form("per_pax"),
    service_duration: int = Form(8),
    price_per_head: float = Form(0.0),
    cost_price: float = Form(0.0),
    cost_breakdown: Optional[str] = Form(None),
    markup_type: str = Form("percentage"),
    markup_value: float = Form(0.0),
    min_contract_amount: float = Form(0.0),
    min_guests: int = Form(1),
    max_guests: Optional[str] = Form(None),
    inclusions: Optional[List[str]] = Form(None),
    linked_menu_ids: Optional[List[str]] = Form(None),
    additional_guest_price: float = Form(0.0),
    image: Optional[UploadFile] = File(None),
    base_pax: int = Form(50),
    labor_cost: float = Form(0.0),
    utility_cost: float = Form(0.0),
    equipment_cost: float = Form(0.0),
    transportation_cost: float = Form(0.0),
    miscellaneous_cost: float = Form(0.0),
    internal_cost_per_pax: float = Form(0.0),
    reservation_fee_type: str = Form("fixed"),
    reservation_fee_value: float = Form(0.0),
    booking_lead_time: int = Form(7),
    selection_rules: Optional[str] = Form(None),
    status: str = Form("active"),
    policies_cancellation: Optional[str] = Form(None),
    policies_internal: Optional[str] = Form(None),
    menu_addons: Optional[str] = Form(None),
    service_addons: Optional[str] = Form(None),
    equipment_addons: Optional[str] = Form(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
        
    errors = []
    
    # Inject Global Settings for Operational Costs and Reservation
    labor_cost = user.caterer_profile.default_labor_cost or 0.0
    utility_cost = user.caterer_profile.default_utility_cost or 0.0
    transportation_cost = user.caterer_profile.default_transport_cost or 0.0
    reservation_fee_type = user.caterer_profile.default_reservation_type or "fixed"
    reservation_fee_value = user.caterer_profile.default_reservation_value or 0.0
    
    if not name.strip():
        errors.append("Package name is required.")
    # Removed mandatory menu item selection to allow optional packages
    if price_per_head <= 0:
        errors.append("Price per head must be greater than 0.")
    global_min_pax = user.caterer_profile.min_pax or 20
    if min_guests < global_min_pax:
        errors.append(f"Minimum guests cannot be lower than your global setting of {global_min_pax}.")
        
    global_lead_time = user.caterer_profile.booking_lead_time or 7
    if booking_lead_time < global_lead_time:
        errors.append(f"Booking lead time cannot be lower than your global setting of {global_lead_time} days.")
    if reservation_fee_value <= 0 and price_per_head > 0:
        pass # Optional warning: errors.append("Reservation fee must be greater than 0.")
    elif reservation_fee_type == 'fixed' and price_per_head > 0 and min_guests > 0 and pricing_mode == 'per_pax':
        max_allowed_fee = (price_per_head * min_guests) * 0.5
        if reservation_fee_value > max_allowed_fee:
            errors.append(f"Reservation fee cannot exceed 50% of the total base package cost.")


    # Smart Validation: Detect existing package with the same name, excluding this package
    existing_pkg = db.query(models.CateringPackage).filter(
        models.CateringPackage.caterer_id == user.caterer_profile.id,
        models.CateringPackage.name.ilike(name.strip()),
        models.CateringPackage.id != package_id
    ).first()
    
    if existing_pkg:
        errors.append(f"A package named '{name}' already exists in your library.")
        
    if errors:
        error_msg = " | ".join(errors)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse({"status": "error", "message": error_msg}, status_code=400)
        return RedirectResponse(url=f"/caterer/packages?error_msg={error_msg}", status_code=303)

    package.name = name
    package.description = description
    package.service_type = service_type
    package.pricing_mode = pricing_mode
    package.service_duration = service_duration
    package.price_per_head = price_per_head
    package.price = price_per_head # Sync for compatibility
    package.cost_price = cost_price
    if cost_breakdown is not None:
        package.cost_breakdown = json.loads(cost_breakdown) if cost_breakdown else None
    package.min_contract_amount = min_contract_amount
    package.min_guests = min_guests
    package.max_guests = int(max_guests) if max_guests and str(max_guests).strip() else None
    package.base_pax = base_pax
    package.additional_guest_price = additional_guest_price
    package.labor_cost = labor_cost
    package.utility_cost = utility_cost
    package.equipment_cost = equipment_cost
    package.transportation_cost = transportation_cost
    package.miscellaneous_cost = miscellaneous_cost
    package.internal_cost_per_pax = internal_cost_per_pax
    package.markup_type = markup_type
    package.markup_value = markup_value
    package.reservation_fee_type = reservation_fee_type
    package.reservation_fee_value = reservation_fee_value
    package.booking_lead_time = booking_lead_time
    package.selection_rules = json.loads(selection_rules) if selection_rules else None
    
    
    # Process inclusions into a dict for storage
    if inclusions:
        package.inclusions = {inc: True for inc in inclusions}
    else:
        package.inclusions = {}

    # Handle linked items
    if linked_menu_ids is not None:
        menu_ids = []
        eq_data = []
        svc_data = []
        for i in set(linked_menu_ids):
            qty = 1
            if '_q' in i:
                parts = i.split('_q')
                i = parts[0]
                try: qty = int(parts[1])
                except: pass
                
            if i.startswith('eq_'): eq_data.append((int(i.replace('eq_', '')), qty))
            elif i.startswith('svc_'): svc_data.append((int(i.replace('svc_', '')), qty))
            elif i.startswith('leg_'): menu_ids.append(int(i.replace('leg_', '')))
            else:
                try: menu_ids.append(int(i))
                except: pass

        # Clear existing specific table links
        package.menu_items = []
        db.query(models.PackageEquipment).filter(models.PackageEquipment.package_id == package.id).delete()
        db.query(models.PackageService).filter(models.PackageService.package_id == package.id).delete()
        
        # Add new
        if menu_ids:
            items = db.query(models.MenuItem).filter(models.MenuItem.id.in_(menu_ids)).all()
            package.menu_items = items
            
        for eid, qty in eq_data:
            db.add(models.PackageEquipment(package_id=package.id, equipment_id=eid, quantity=qty))
        for sid, qty in svc_data:
            db.add(models.PackageService(package_id=package.id, service_id=sid, quantity=qty))


    import base64
    if image and image.filename:
        try:
            content_bytes = await image.read()
            if content_bytes:
                package.image_url = process_base64_image(content_bytes, max_size=(600, 400))
        except Exception:
            pass

    db.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({
            "status": "success", 
            "message": "Package updated successfully", 
            "package_id": package.id,
            "package_name": package.name
        })

    return RedirectResponse(url="/caterer/packages", status_code=303)

@router.post("/packages/{package_id}/archive")
async def archive_package_caterer(
    package_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    package.status = 'archived'
    package.is_active = False
    db.commit()

    # Broadcast update
    await manager.broadcast_to_user(user.id, {
        "type": "package_archived",
        "package_id": package_id,
        "message": f"Package '{package.name}' archived."
    })
    
    return JSONResponse({"status": "success", "message": "Package archived successfully", "package_id": package_id})

@router.post("/packages/{package_id}/toggle-status")
async def toggle_package_status(
    package_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    package.is_active = not package.is_active
    db.commit()
    
    return JSONResponse({
        "status": "success", 
        "is_active": package.is_active,
        "message": f"Package '{package.name}' is now {'active' if package.is_active else 'hidden'}."
    })

@router.get("/packages/{package_id}/addons")
async def get_package_addons(
    package_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    res = {"menu": [], "service": [], "equipment": []}
    
    for a in package.menu_addons:
        m = db.query(models.MenuItem).filter(models.MenuItem.id == a.menu_item_id).first()
        if m:
            res["menu"].append({
                "id": m.id,
                "name": m.name,
                "price": a.price,
                "selection_type": a.selection_type,
                "min_quantity": a.min_quantity,
                "max_quantity": a.max_quantity,
                "is_enabled": a.is_enabled
            })
            
    for a in package.service_addons:
        s = db.query(models.Service).filter(models.Service.id == a.service_id).first()
        if s:
            res["service"].append({
                "id": f"svc_{s.id}",
                "name": s.name,
                "price": a.price,
                "selection_type": a.selection_type,
                "min_quantity": a.min_quantity,
                "max_quantity": a.max_quantity,
                "is_enabled": a.is_enabled
            })
            
    for a in package.equipment_addons:
        e = db.query(models.Equipment).filter(models.Equipment.id == a.equipment_id).first()
        if e:
            res["equipment"].append({
                "id": f"eq_{e.id}",
                "name": e.name,
                "price": a.price,
                "min_quantity": a.min_quantity,
                "max_quantity": a.max_quantity,
                "is_enabled": a.is_enabled
            })
            
    return res

@router.get("/packages/{package_id}/menu")
async def get_package_menu(
    package_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    res = [
        {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "image_url": item.image_url,
            "is_addon": item.is_addon
        }
        for item in package.menu_items
    ]
    
    eqs = db.query(models.PackageEquipment).filter(models.PackageEquipment.package_id == package.id).all()
    for e in eqs:
        res.append({"id": f"eq_{e.equipment_id}", "quantity": e.quantity})
        
    svcs = db.query(models.PackageService).filter(models.PackageService.package_id == package.id).all()
    for s in svcs:
        res.append({"id": f"svc_{s.service_id}", "quantity": s.quantity})
        
    return res

@router.post("/packages/{package_id}/menu/add")
async def add_menu_to_package(
    package_id: int,
    name: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    cost_price: float = Form(0.0),
    cost_breakdown: Optional[str] = Form(None),
    is_addon: bool = Form(False),
    addon_price: float = Form(0.0),
    is_combo: bool = Form(False),
    max_choices: int = Form(0),
    combo_options: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    # First check package
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    import base64
    image_url = None
    if image and image.filename:
        try:
            content_bytes = await image.read()
            if content_bytes:
                image_url = process_base64_image(content_bytes)
        except Exception:
            pass

    new_item = models.MenuItem(
        caterer_id=user.caterer_profile.id,
        name=name,
        category=category,
        description=description,
        cost_price=cost_price,
        cost_breakdown=json.loads(cost_breakdown) if cost_breakdown else None,
        is_addon=is_addon,
        addon_price=addon_price,
        is_combo=is_combo,
        max_choices=max_choices,
        combo_options=json.loads(combo_options) if combo_options else None,
        image_url=image_url,
        is_archived=False
    )
    db.add(new_item)
    db.flush() # Get ID
    
    # Link to package
    package.menu_items.append(new_item)
    db.commit()
    return {"status": "success", "item_id": new_item.id}

@router.post("/packages/{package_id}/menu/{item_id}/unlink")
async def unlink_menu_from_package(
    package_id: int,
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    item = next((i for i in package.menu_items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not linked to this package")
    
    package.menu_items.remove(item)
    db.commit()
    return {"status": "success"}

@router.get("/api/menu")
async def get_all_menu_items_api(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    items = db.query(models.MenuItem).filter(
        models.MenuItem.caterer_id == user.caterer_profile.id,
        models.MenuItem.is_archived == False
    ).all()
    
    result = []
    for i in items:
        # Get variants if pricing_type is variants
        variants_data = []
        base_price = getattr(i, 'price', 0.0)
        
        if getattr(i, 'pricing_type', '') == 'variants':
            variants = db.query(models.MenuVariant).filter(models.MenuVariant.menu_item_id == i.id).all()
            for v in variants:
                variants_data.append({
                    "id": v.id,
                    "name": v.variant_name,
                    "price": v.price
                })
            
            # Update base_price to the lowest variant price if it exists
            if variants_data:
                base_price = min([v['price'] for v in variants_data])

        result.append({
            "id": i.id,
            "name": i.name,
            "category": i.category,
            "image_url": i.image_url,
            "cost_price": i.cost_price,
            "price": base_price,
            "is_addon": i.is_addon,
            "usage_type": i.usage_type,
            "pricing_type": getattr(i, 'pricing_type', 'fixed'),
            "variants": variants_data
        })
    
    eqs = db.query(models.Equipment).filter(
        models.Equipment.caterer_id == user.caterer_profile.id,
        models.Equipment.is_archived == False
    ).all()
    for e in eqs:
        result.append({
            "id": f"eq_{e.id}",
            "name": e.name,
            "category": e.category or 'Equipment',
            "image_url": e.image_url,
            "cost_price": e.cost_value,
            "price": e.rental_price,
            "is_addon": getattr(e, 'is_addon', False),
            "usage_type": getattr(e, 'usage_type', 'both')
        })
        
    svcs = db.query(models.Service).filter(
        models.Service.caterer_id == user.caterer_profile.id,
        models.Service.is_archived == False
    ).all()
    for s in svcs:
        result.append({
            "id": f"svc_{s.id}",
            "name": s.name,
            "category": s.category or 'Service',
            "image_url": s.image_url,
            "cost_price": s.cost,
            "price": s.selling_price,
            "is_addon": getattr(s, 'is_addon', False),
            "usage_type": getattr(s, 'usage_type', 'both')
        })
        
    return result

@router.post("/packages/{package_id}/menu/link")
async def link_menu_to_package(
    package_id: int,
    item_id: int = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    item = db.query(models.MenuItem).filter(
        models.MenuItem.id == item_id,
        models.MenuItem.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item not in package.menu_items:
        package.menu_items.append(item)
        db.commit()
    
    return {"status": "success"}

@router.get("/api/menu-items/{item_id}/ingredients")
async def get_menu_item_ingredients(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.MenuItem).filter(
        models.MenuItem.id == item_id,
        models.MenuItem.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    ingredients = []
    # Removed ingredient fetching due to Phase 1 cleanup
    return {
        "menu_item_id": item_id,
        "name": item.name,
        "ingredients": ingredients,
        "total_cost": item.cost_price
    }

@router.post("/menu/{item_id}/update")
async def update_menu_item(
    item_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    import base64
    item = db.query(models.MenuItem).get(item_id)
    if not item or item.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Item not found")

    form_data = await request.form()
    
    name = form_data.get("name")
    category = form_data.get("category")
    if category == "Other":
        category = form_data.get("custom_category") or "Other"
    
    description = form_data.get("description")
    status = form_data.get("status", "available")
    
    # New V2.0 Fields
    usage_type = form_data.get("usage_type", "both")
    available_for_package = usage_type in ["package_only", "both"]
    available_for_order = usage_type in ["order_only", "both"]
    
    pricing_mode = form_data.get("pricing_mode", "single")
    pricing_type = pricing_mode

    price = 0.0
    serving_size = None
    if not (usage_type == "package_only") and pricing_mode == "single":
        try:
            price = float(form_data.get("price", "0").replace(",", ""))
        except ValueError:
            price = 0.0
        serving_size = form_data.get("serving_size")

    if not (usage_type == "package_only"):
        min_order_qty = int(form_data.get("min_order_qty", "1") or "1")
    else:
        min_order_qty = 1
    
    is_hidden = form_data.get("visibility") == "hidden"
    
    is_addon = False
    addon_price = 0.0
    cost_price = 0.0
    item_type = form_data.get("item_type", "single")
    is_combo = (item_type == "preset_combo")
    included_dishes = form_data.getlist("included_dishes[]")
    combo_options = {"included_menu_ids": [int(x) for x in included_dishes if x.isdigit()]} if is_combo else {}
    max_choices = 0
    
    dietary_tags = form_data.getlist("dietary_tags")
    allergen_info = form_data.getlist("allergen_info")
    serving_style = form_data.get("serving_style")
    
    image = form_data.get("image")

    item.name = name
    item.category = category
    item.description = description
    item.serving_style = serving_style
    item.cost_price = cost_price
    item.price = price
    item.serving_size = serving_size
    item.min_order_qty = min_order_qty
    item.status = status
    item.usage_type = usage_type
    item.available_for_package = available_for_package
    item.available_for_order = available_for_order
    item.pricing_type = pricing_type
    item.pricing_unit = pricing_type
        
    item.is_hidden = is_hidden
    item.is_addon = is_addon
    item.addon_price = addon_price
    item.dietary_tags = dietary_tags
    item.allergen_info = allergen_info
    item.is_combo = is_combo
    item.max_choices = max_choices
    item.combo_options = combo_options

    if image and hasattr(image, "filename") and image.filename:
        try:
            content_bytes = await image.read()
            if content_bytes:
                item.image_url = process_base64_image(content_bytes, max_size=(600, 400))
        except Exception:
            pass

    # Clear existing pricing
    db.query(models.MenuVariant).filter(models.MenuVariant.menu_item_id == item.id).delete()

    if not (usage_type == "package_only") and pricing_mode == "variants":
        v_names = form_data.getlist("variant_names[]")
        v_prices = form_data.getlist("variant_prices[]")
        v_servings = form_data.getlist("variant_servings[]")
        v_statuses = form_data.getlist("variant_statuses[]")

        for i, name in enumerate(v_names):
            if name.strip():
                try:
                    v_price = float(v_prices[i].replace(",", ""))
                except:
                    v_price = 0.0
                serving = v_servings[i].strip() if i < len(v_servings) else None
                v_status = v_statuses[i] if i < len(v_statuses) else 'available'
                
                variant = models.MenuVariant(
                    menu_item_id=item.id,
                    variant_name=name.strip(),
                    measurement=None,
                    price=v_price,
                    serving_capacity=serving,
                    status=v_status,
                    display_order=i
                )
                db.add(variant)

    db.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Dish updated successfully"})

    return RedirectResponse(url="/caterer/menu?success_msg=Dish+updated+successfully", status_code=303)

@router.post("/menu/{item_id}/archive")
async def archive_menu_item_caterer(
    request: Request,
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.MenuItem).filter(
        models.MenuItem.id == item_id,
        models.MenuItem.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    item.is_archived = True
    db.commit()

    # Broadcast update
    await manager.broadcast_to_user(user.id, {
        "type": "menu_archived",
        "item_id": item_id,
        "message": f"Dish '{item.name}' archived."
    })
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Menu item archived successfully", "item_id": item_id})

    return RedirectResponse(url="/caterer/menu?success_msg=Menu+item+archived+successfully", status_code=303)

@router.post("/profile/change-password")
async def change_password_caterer(
    current_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    if not auth.verify_password(current_password, user.password_hash):
        return {"success": False, "message": "Incorrect current password"}
    
    user.password_hash = auth.get_password_hash(new_password)
    db.commit()
    return {"success": True}

@router.post("/api/availability/toggle")
async def toggle_availability(
    data: dict,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(auth.get_current_user) # Using current user instead of caterer_only to be safer with dict parsing
):
    if user.role != "caterer":
        raise HTTPException(status_code=403, detail="Caterer only")
        
    date_str = data.get("date")
    is_available = data.get("is_available", False)
    reason = data.get("reason", "")
    
    from datetime import datetime
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    # Check if entry already exists
    existing = db.query(models.Availability).filter(
        models.Availability.caterer_id == user.caterer_profile.id,
        models.Availability.date == target_date
    ).first()
    
    if existing:
        existing.is_available = is_available
        existing.reason = reason
    else:
        new_avail = models.Availability(
            caterer_id=user.caterer_profile.id,
            date=target_date,
            is_available=is_available,
            reason=reason
        )
        db.add(new_avail)
    
    db.commit()
    return {"status": "success"}

@router.post("/api/calendar/capacity-settings")
async def update_capacity_settings(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    """Update caterer's calendar capacity settings."""
    data = await request.json()
    profile = user.caterer_profile
    
    max_per_day = data.get("max_bookings_per_day")
    auto_block = data.get("auto_block_enabled")
    
    if max_per_day is not None:
        max_per_day = max(1, min(10, int(max_per_day)))  # Clamp 1-10
        profile.max_bookings_per_day = max_per_day
    
    if auto_block is not None:
        profile.auto_block_enabled = bool(auto_block)
    
    db.commit()
    return {
        "status": "success", 
        "max_bookings_per_day": profile.max_bookings_per_day,
        "auto_block_enabled": profile.auto_block_enabled
    }

@router.post("/api/sidebar-mode")
async def toggle_sidebar_mode(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    try:
        data = await request.json()
    except:
        data = {}
        
    mode = data.get("mode", "full")
    if mode not in ["full", "icons"]:
        mode = "full"
    
    user.caterer_profile.sidebar_mode = mode
    db.commit()
    return {"status": "success", "mode": mode}

@router.get("/api/events")
async def get_calendar_events(
    caterer_id: Optional[int] = None,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(auth.get_current_user_optional)
):
    # Use provided caterer_id (for customers) or user's caterer profile (for caterers themselves)
    target_caterer_id = caterer_id
    if not target_caterer_id and user and user.role == 'caterer':
        target_caterer_id = user.caterer_profile.id
    
    if not target_caterer_id:
        return []

    bookings = db.query(models.Booking).filter(
        models.Booking.caterer_id == target_caterer_id,
        models.Booking.status.in_(['confirmed', 'preparing', 'ready_for_delivery', 'on_the_way', 'arrived', 'setup_ongoing', 'completed']),
        models.Booking.is_archived == False
    ).all()
    
    events = []
    colors = {
        "Wedding": "#6366f1", # Indigo
        "Birthday": "#0ea5e9", # Cerulean
        "Corporate": "#0f172a", # Charcoal
        "Private Party": "#10b981", # Emerald
        "Ala Carte": "#f59e0b", # Amber/Orange
        "Equipment Rental": "#14b8a6" # Teal
    }
    
    # Check if we should show full details (only for the caterer owner)
    is_owner = user and user.role == 'caterer' and user.caterer_profile.id == target_caterer_id
    
    # Get capacity settings
    caterer_profile = None
    if is_owner:
        caterer_profile = user.caterer_profile
    else:
        caterer_profile = db.query(models.CatererProfile).get(target_caterer_id)
    
    max_capacity = (caterer_profile.max_bookings_per_day or 1) if caterer_profile else 1
    auto_block = (caterer_profile.auto_block_enabled if caterer_profile and caterer_profile.auto_block_enabled is not None else True)

    # Track booking counts per date for capacity visualization
    date_booking_counts = {}
    
    for b in bookings:
        start_dt = str(b.event_date)
        if b.event_time:
            start_dt += f"T{b.event_time}"
        
        # Track counts
        date_key = str(b.event_date)
        date_booking_counts[date_key] = date_booking_counts.get(date_key, 0) + 1
            
        # Normalize event type for color mapping
        raw_type = (b.event_type or "Wedding").strip()
        ev_type = raw_type.title()
        if ev_type.lower() in ['ala carte', 'alacarte', 'a la carte', 'ala carte order']:
            ev_type = "Ala Carte"
        elif ev_type.lower() in ['equipment rental']:
            ev_type = "Equipment Rental"
            
        event_data = {
            "id": str(b.id),
            "start": start_dt,
            "backgroundColor": colors.get(ev_type, "#6366f1"),
            "borderColor": colors.get(ev_type, "#6366f1"),
        }

        if is_owner:
            customer_name = f"{b.user.first_name} {b.user.last_name}" if b.user else "Unknown Customer"
            customer_first_name = b.user.first_name if b.user else "Customer"
            event_data["title"] = f"{b.event_type or 'Event'} - {b.event_name or customer_first_name}"
            event_data["extendedProps"] = {
                "customer": customer_name,
                "type": b.event_type or "N/A",
                "guests": b.guest_count,
                "venue": b.venue_address or "TBD",
                "package": b.package.name if b.package else "Custom",
                "time": str(b.event_time) if b.event_time else "TBD",
                "status": b.status,
                "payment_status": b.payment_status or "pending",
                "booking_id": b.id,
                "special_requests": b.special_requests or ""
            }
        else:
            event_data["title"] = "BOOKED"
            event_data["display"] = "background"
            event_data["overlap"] = False

        events.append(event_data)
        
    # Add blocked dates from availability
    availabilities = db.query(models.Availability).filter(
        models.Availability.caterer_id == target_caterer_id,
        models.Availability.is_available == False
    ).all()
    
    for a in availabilities:
        events.append({
            "title": "BLOCKED",
            "start": str(a.date),
            "allDay": True,
            "backgroundColor": "#f43f5e",
            "borderColor": "#e11d48",
            "textColor": "#ffffff",
            "extendedProps": {
                "type": "BLOCKED",
                "reason": a.reason or "No reason provided",
                "customer": "N/A",
                "is_manual_block": True
            }
        })
    
    # Add FULL indicators for dates at capacity (auto-block)
    if is_owner and auto_block:
        blocked_dates = {str(a.date) for a in availabilities}
        for date_key, count in date_booking_counts.items():
            if count >= max_capacity and date_key not in blocked_dates:
                events.append({
                    "title": f"FULL ({count}/{max_capacity})",
                    "start": date_key,
                    "allDay": True,
                    "backgroundColor": "#f59e0b",
                    "borderColor": "#d97706",
                    "textColor": "#ffffff",
                    "extendedProps": {
                        "type": "CAPACITY_FULL",
                        "reason": f"Auto-blocked: {count}/{max_capacity} slots filled",
                        "customer": "N/A",
                        "is_manual_block": False,
                        "booking_count": count,
                        "max_capacity": max_capacity
                    }
                })
        
    return events

@router.post("/api/bookings/{booking_id}/reminders")
async def set_booking_reminder(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Simple logic: create a notification for the caterer
    new_notif = models.Notification(
        user_id=user.id,
        title=f"Reminder: {booking.event_name or 'Event'}",
        message=f"Preparation reminder for {booking.event_name} on {booking.event_date}.",
        type="reminder"
    )
    db.add(new_notif)
    db.commit()

    # Real-time WebSocket Alert to Caterer
    import asyncio
    asyncio.create_task(manager.broadcast_to_user(user.id, {
        "type": "new_notification",
        "message": f"Reminder set: {booking.event_name}",
        "count": db.query(models.Notification).filter(models.Notification.user_id == user.id, models.Notification.is_read == False).count()
    }))

    return {"status": "success", "message": "Reminder set successfully"}


@router.get("/api/bookings/{booking_id}/tasks")
async def get_booking_tasks(
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.caterer_id == user.caterer_profile.id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    tasks = db.query(models.BookingTask).filter(models.BookingTask.booking_id == booking_id).order_by(models.BookingTask.created_at.asc()).all()
    return tasks

@router.post("/api/bookings/{booking_id}/tasks")
async def add_booking_task(
    booking_id: int,
    data: dict = Body(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.caterer_id == user.caterer_profile.id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    task = models.BookingTask(
        booking_id=booking_id,
        title=data.get("title", "New Task")
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@router.post("/api/tasks/{task_id}/toggle")
async def toggle_booking_task(
    task_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    task = db.query(models.BookingTask).join(models.Booking).filter(
        models.BookingTask.id == task_id,
        models.Booking.caterer_id == user.caterer_profile.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task.is_completed = not task.is_completed
    db.commit()
    return {"is_completed": task.is_completed}

@router.delete("/api/tasks/{task_id}")
async def delete_booking_task(
    task_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    task = db.query(models.BookingTask).join(models.Booking).filter(
        models.BookingTask.id == task_id,
        models.Booking.caterer_id == user.caterer_profile.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    db.delete(task)
    db.commit()
    return {"status": "success"}

@router.get("/notifications", response_class=HTMLResponse)

async def caterer_notifications(
    request: Request, 
    page: int = 1,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    per_page = 10
    page = max(1, page)
    
    base_query = db.query(models.Notification).filter(
        models.Notification.user_id == user.id
    )
    
    total_notifications = base_query.count()
    total_pages = (total_notifications + per_page - 1) // per_page if total_notifications > 0 else 1
    
    notifications = base_query.order_by(
        models.Notification.created_at.desc()
    ).offset((page - 1) * per_page).limit(per_page).all()
    
    return templates.TemplateResponse("caterer/notifications.html", {
        "request": request,
        "user": user,
        "notifications": notifications,
        "active_page": "notifications",
        "current_page": page,
        "total_pages": total_pages,
        "total_notifications": total_notifications
    })

@router.post("/bookings/{booking_id}/cancel")
async def cancel_booking(
    request: Request,
    booking_id: int,
    reason: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking.status = "cancelled"
    
    history = models.BookingHistory(
        booking_id=booking.id,
        status="cancelled",
        notes=f"Booking cancelled by caterer. Reason: {reason}"
    )
    db.add(history)
    db.commit()
    
    # Broadcast update to sync other caterer tabs
    await manager.broadcast_to_user(user.id, {
        "type": "dashboard_update",
        "message": "Stats updated: Booking cancelled."
    })
    await manager.broadcast_to_user(user.id, {
        "type": "booking_update",
        "booking_id": booking_id,
        "new_status": "cancelled",
        "message": f"Booking #{booking_id} has been cancelled."
    })
    
    # Notify Customer
    from ..services.notification import NotificationService
    import asyncio
    is_food_order = (booking.document_type == 'invoice')
    ref_id = f"ORD-{booking.id:03d}" if is_food_order else f"BK-{booking.id:03d}"
    notif_link = f"/customer/orders" if is_food_order else f"/customer/bookings"
    asyncio.create_task(NotificationService.notify_status_update(
        db, 
        booking.user_id, 
        "Booking Cancelled" if not is_food_order else "Order Cancelled", 
        f"Your {'order' if is_food_order else 'booking'} '{booking.event_name}' ({ref_id}) with {user.caterer_profile.business_name} has been cancelled. Reason: {reason}", 
        notif_link
    ))
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Booking cancelled successfully", "new_status": "cancelled"})

    return RedirectResponse(url="/caterer/bookings?success_msg=Booking+cancelled+successfully", status_code=303)

@router.post("/bookings/{booking_id}/accept")
async def accept_booking(
    request: Request,
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking.status = 'confirmed'
    history = models.BookingHistory(booking_id=booking.id, status='confirmed', notes="Booking accepted by caterer manually.")
    db.add(history)
    db.commit()

    
    return JSONResponse({"status": "success", "message": "Booking accepted", "new_status": "confirmed"})

@router.post("/bookings/{booking_id}/reject")
async def reject_booking(
    request: Request,
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    try:
        data = await request.json()
        reason = data.get("reason", "No reason provided.")
    except:
        reason = "Booking rejected by caterer."

    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking.status = 'cancelled'
    history = models.BookingHistory(booking_id=booking.id, status='cancelled', notes=f"Rejected: {reason}")
    db.add(history)
    db.commit()

    await manager.broadcast_to_user(user.id, {
        "type": "booking_update",
        "booking_id": booking_id,
        "new_status": "cancelled",
        "message": f"Booking rejected: {reason}"
    })
    
    # Notify Customer
    from ..services.notification import NotificationService
    import asyncio
    is_food_order = (booking.document_type == 'invoice')
    ref_id = f"ORD-{booking.id:03d}" if is_food_order else f"BK-{booking.id:03d}"
    notif_link = f"/customer/orders" if is_food_order else f"/customer/bookings"
    asyncio.create_task(NotificationService.notify_status_update(
        db, 
        booking.user_id, 
        "Booking Rejected" if not is_food_order else "Order Rejected", 
        f"We regret to inform you that your {'order' if is_food_order else 'booking'} '{booking.event_name}' ({ref_id}) with {user.caterer_profile.business_name} was not accepted. Reason: {reason}", 
        notif_link
    ))
    
    return JSONResponse({"status": "success", "message": "Booking rejected", "new_status": "cancelled"})

@router.post("/bookings/{booking_id}/complete")
async def complete_booking(
    request: Request,
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # --- PHASE 3: COMPLETION GATING LOGIC ---
    has_equipment = False
    has_food = True if booking.package_id else False
    has_service = False
    
    for item in booking.selected_items:
        if getattr(item, 'equipment_id', None): has_equipment = True
        if getattr(item, 'menu_item_id', None): has_food = True
        if getattr(item, 'service_id', None): has_service = True
        
    if has_equipment and not booking.return_photo_url:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Cannot complete booking: Equipment Return Inspection (Photo) is required."})
        
    if has_food and not booking.dispatch_proof_url:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Cannot complete booking: Food Dispatch/Setup verification (Photo) is required."})
    
    # Optional: If services have specific completion proof in the future, add it here.
    
    booking.status = 'completed'
    history = models.BookingHistory(booking_id=booking.id, status='completed', notes="Event marked as completed by caterer.")
    db.add(history)

    # Automatically generate commission record
    config = db.query(models.WebsiteConfig).first()
    commission_rate = (config.commission_rate / 100.0) if config and config.commission_rate else 0.10
    commission_due = (booking.total_amount or 0.0) * commission_rate

    commission_record = models.BillingInvoice(
        caterer_id=booking.caterer_id,
        booking_id=booking.id,
        billing_period=booking.event_date.strftime('%B %Y') if booking.event_date else 'General',
        amount=commission_due,
        commission_rate=commission_rate,
        status='pending'
    )
    db.add(commission_record)

    db.commit()

    await manager.broadcast_to_user(user.id, {
        "type": "booking_update",
        "booking_id": booking_id,
        "new_status": "completed",
        "message": "Booking completed."
    })
    
    # Notify Customer
    from ..services.notification import NotificationService
    import asyncio
    is_food_order = (booking.document_type == 'invoice')
    ref_id = f"ORD-{booking.id:03d}" if is_food_order else f"BK-{booking.id:03d}"
    caterer_name = user.caterer_profile.business_name
    notif_link = f"/customer/orders/manage/{booking.id}" if is_food_order else f"/customer/bookings/manage/{booking.id}"
    asyncio.create_task(NotificationService.notify_status_update(
        db, 
        booking.user_id, 
        "Event Service Completed" if not is_food_order else "Order Completed!", 
        f"Your {'booking' if not is_food_order else 'order'} '{booking.event_name}' ({ref_id}) with {caterer_name} has been marked as COMPLETED. Thank you for choosing OccaServe! Don't forget to leave a review.", 
        notif_link
    ))
    
    return JSONResponse({"status": "success", "message": "Booking completed", "new_status": "completed"})

@router.post("/bookings/{booking_id}/archive")
async def archive_booking(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.caterer_id == user.caterer_profile.id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking.is_archived = True
    db.commit()
    
    # WebSocket Broadcast for real-time removal from dashboard & stats refresh
    await manager.broadcast_to_user(user.id, {
        "type": "dashboard_update",
        "message": "Stats updated: Booking archived."
    })
    await manager.broadcast_to_user(user.id, {
        "type": "booking_archived",
        "booking_id": booking_id,
        "message": "Booking has been archived successfully."
    })
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Booking archived successfully", "booking_id": booking_id})

    # Allow redirecting back to where the request came from (e.g., payments page)
    next_url = request.query_params.get("next", "/caterer/bookings")
    if "?" in next_url:
        next_url += "&success_msg=Booking+archived+successfully"
    else:
        next_url += "?success_msg=Booking+archived+successfully"
    return RedirectResponse(url=next_url, status_code=303)

@router.post("/bookings/{booking_id}/restore")
async def restore_booking(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.caterer_id == user.caterer_profile.id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking.is_archived = False
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Booking+restored+successfully", status_code=303)

@router.post("/gallery/{item_id}/restore")
async def restore_gallery_item(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.CatererGallery).filter(
        models.CatererGallery.id == item_id,
        models.CatererGallery.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Gallery item not found")
    
    item.is_archived = False
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Gallery+item+restored+successfully", status_code=303)

@router.post("/packages/{package_id}/restore")
async def restore_package(
    package_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    package.status = 'active'
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Package+restored+successfully", status_code=303)

@router.post("/menu/{item_id}/restore")
async def restore_menu_item(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.MenuItem).filter(
        models.MenuItem.id == item_id,
        models.MenuItem.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    item.is_archived = False
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Menu+item+restored+successfully", status_code=303)

@router.post("/bookings/{booking_id}/delete")
async def delete_booking_permanent(
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.caterer_id == user.caterer_profile.id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(booking)
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Booking+permanently+deleted", status_code=303)

@router.post("/packages/{package_id}/delete")
async def delete_package_permanent(
    package_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    db.delete(package)
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Package+permanently+deleted", status_code=303)

@router.post("/menu/{item_id}/delete")
async def delete_menu_item_permanent(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.MenuItem).filter(
        models.MenuItem.id == item_id,
        models.MenuItem.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    db.delete(item)
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Menu+item+permanently+deleted", status_code=303)

@router.post("/gallery/{item_id}/delete")
async def delete_gallery_item_permanent(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.CatererGallery).filter(
        models.CatererGallery.id == item_id,
        models.CatererGallery.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Gallery item not found")
    db.delete(item)
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Gallery+photo+permanently+deleted", status_code=303)

@router.post("/services/{item_id}/restore")
async def restore_service(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.Service).filter(
        models.Service.id == item_id,
        models.Service.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Service not found")
    item.is_archived = False
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Service+restored+successfully", status_code=303)

@router.post("/services/{item_id}/delete")
async def delete_service_permanent(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.Service).filter(
        models.Service.id == item_id,
        models.Service.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Service not found")
    db.delete(item)
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Service+permanently+deleted", status_code=303)

@router.post("/equipment/{item_id}/restore")
async def restore_equipment(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.Equipment).filter(
        models.Equipment.id == item_id,
        models.Equipment.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Equipment not found")
    item.is_archived = False
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Equipment+restored+successfully", status_code=303)

@router.post("/equipment/{item_id}/delete")
async def delete_equipment_permanent(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.Equipment).filter(
        models.Equipment.id == item_id,
        models.Equipment.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Equipment not found")
    db.delete(item)
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Equipment+permanently+deleted", status_code=303)

@router.post("/portfolio/{item_id}/restore")
async def restore_portfolio(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.Portfolio).filter(
        models.Portfolio.id == item_id,
        models.Portfolio.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    item.is_archived = False
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Portfolio+restored+successfully", status_code=303)

@router.post("/portfolio/{item_id}/delete")
async def delete_portfolio_permanent(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.Portfolio).filter(
        models.Portfolio.id == item_id,
        models.Portfolio.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    db.delete(item)
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Portfolio+permanently+deleted", status_code=303)

@router.get("/messages", response_class=HTMLResponse)
async def caterer_messages(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    """Render the chat messaging interface for the caterer."""
    return templates.TemplateResponse("caterer/messages.html", {
        "request": request,
        "user": user,
        "active_page": "messages"
    })

@router.post("/api/check-customer")
async def check_customer(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    data = await request.json()
    email = data.get("email", "").strip()
    name = data.get("name", "").strip()

    query = db.query(models.User).filter(models.User.role == 'customer')
    
    target = None
    if email and "@" in email:
        target = query.filter(models.User.email.ilike(email)).first()

    # Then by name using ilike if email is missing or not found
    if not target and name and len(name) > 2:
        parts = name.split()
        if len(parts) >= 2:
            target = query.filter(
                models.User.first_name.ilike(f"%{parts[0]}%"),
                models.User.last_name.ilike(f"%{parts[-1]}%")
            ).first()
        else:
            target = query.filter(
                models.User.first_name.ilike(f"%{name}%") |
                models.User.last_name.ilike(f"%{name}%")
            ).first()

    if target:
        full_name = f"{target.first_name or ''} {target.last_name or ''}".strip()
        email_taken = False
        if email and target.email and email.lower() == target.email.lower():
            email_taken = True
            
        return {
            "exists": True, 
            "is_taken": email_taken,
            "match_type": "email" if email_taken else "name",
            "name": full_name or target.email, 
            "email": target.email, 
            "contact": target.phone_number,
            "message": "Existing customer found." if email_taken else "Similar name found."
        }
        
    return {"exists": False}

@router.get("/reviews", response_class=HTMLResponse)
async def manage_reviews_page(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    reviews = db.query(models.Review).filter(models.Review.caterer_id == profile.id).order_by(models.Review.created_at.desc()).all()
    
    return templates.TemplateResponse("caterer/manage_reviews.html", {
        "request": request,
        "user": user,
        "profile": profile,
        "reviews": reviews,
        "active_page": "reviews"
    })

@router.post("/reviews/{review_id}/highlight")
async def toggle_review_highlight(
    review_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    review = db.query(models.Review).filter(models.Review.id == review_id, models.Review.caterer_id == profile.id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.is_highlighted = not review.is_highlighted
    db.commit()
    
    return {"success": True, "is_highlighted": review.is_highlighted}

@router.post("/reviews/{review_id}/reply")
async def reply_to_review(
    review_id: int,
    reply_text: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    review = db.query(models.Review).filter(models.Review.id == review_id, models.Review.caterer_id == profile.id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.caterer_reply = reply_text.strip()
    db.commit()
    
    return RedirectResponse(url="/caterer/reviews?success_msg=Reply+submitted!", status_code=303)

@router.get("/compliance", response_class=HTMLResponse)
async def view_compliance_queue(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    # Fetch all customers who have booked with this caterer and have a pending KYC
    customers = db.query(models.User).join(models.Booking).join(models.IdentityVerification).filter(
        models.Booking.caterer_id == profile.id,
        models.Booking.status.not_in(['inquiry', 'negotiating', 'quoted']),
        models.User.role == "customer",
        models.User.is_archived == False,
        models.IdentityVerification.verification_status.in_([
            "pending", "pending_confirmation", "pending_liveliness", 
            "processing", "pending_manual_review", "manual_review", 
            "liveliness_failed", "verified", "approved", "rejected", "failed"
        ]),
        models.IdentityVerification.is_archived == False
    ).distinct().all()

    # KYC records & Bookings mapping
    user_ids = [c.id for c in customers]
    kyc_requests = db.query(models.IdentityVerification).filter(
        models.IdentityVerification.user_id.in_(user_ids) if user_ids else False,
        models.IdentityVerification.is_archived == False
    ).all()
    kyc_map = {k.user_id: k for k in kyc_requests}

    # Categorization and Labels
    package_customers = []
    package_map = {}

    for customer in customers:
        # Get all relevant package bookings for this customer with this caterer
        user_bookings = db.query(models.Booking).filter(
            models.Booking.user_id == customer.id, 
            models.Booking.caterer_id == profile.id,
            models.Booking.status.not_in(['inquiry', 'negotiating', 'quoted']),
            ~models.Booking.event_type.in_(["Ala Carte Order", "Equipment Rental"])
        ).order_by(models.Booking.created_at.desc()).all()
        
        if not user_bookings:
            continue

        package_customers.append(customer)
        latest = user_bookings[0]
        package_map[customer.id] = latest.event_type if len(user_bookings) == 1 else f"{latest.event_type} (+{len(user_bookings)-1} more)"
            
        # Flag for the Multi-Order badge UI
        customer.has_multiple_orders = (len(user_bookings) > 1)

    return templates.TemplateResponse("caterer/compliance.html", {
        "request": request,
        "user": user,
        "package_customers": package_customers,
        "kyc_map": kyc_map,
        "package_map": package_map,
        "active_page": "compliance"
    })



@router.get("/compliance/view/{user_id}", response_class=HTMLResponse)
async def view_customer_verification(
    user_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    # Verify this customer has a booking with this caterer
    booking = db.query(models.Booking).filter(
        models.Booking.caterer_id == profile.id,
        models.Booking.user_id == user_id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=403, detail="You do not have access to this user's verification data.")

    target_user = db.query(models.User).get(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    verification = target_user.identity_verification
    if not verification:
        return RedirectResponse(url="/caterer/compliance?error_msg=No+verification+data+found+for+this+user.")

    # Fetch relevant bookings for historical context
    bookings = db.query(models.Booking).filter(
        models.Booking.caterer_id == profile.id,
        models.Booking.user_id == user_id
    ).order_by(models.Booking.created_at.desc()).all()

    return templates.TemplateResponse("caterer/compliance_verify.html", {
        "request": request,
        "user": user,
        "target_user": target_user,
        "verification": verification,
        "bookings": bookings,
        "active_page": "compliance"
    })

@router.post("/compliance/{user_id}/verify")
async def verify_customer_compliance(
    user_id: int,
    action: str = Form(...),
    reason: Optional[str] = Form(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    # Verify this customer has a booking with this caterer
    booking = db.query(models.Booking).filter(
        models.Booking.caterer_id == profile.id,
        models.Booking.user_id == user_id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=403, detail="Unauthorized")

    target_user = db.query(models.User).get(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    kyc_record = target_user.identity_verification
    
    if action == "approve":
        target_user.is_verified = True
        target_user.is_kyc_complete = True
        if kyc_record:
            kyc_record.verification_status = "verified"
            kyc_record.verified_at = func.now()
        
        # Update latest verification session
        from ..db.models import VerificationSession
        session = db.query(VerificationSession).filter(VerificationSession.user_id == user_id).order_by(VerificationSession.created_at.desc()).first()
        if session:
            session.status = "verified"
        
        # Also update all bookings for this user with this caterer
        db.query(models.Booking).filter(
            models.Booking.user_id == user_id,
            models.Booking.caterer_id == profile.id
        ).update({"ocr_verified": True, "liveness_verified": True})

        # NOTIFY: Real-time update for customer
        await NotificationService.notify_status_update(
            db, user_id, 
            "Identity Approved!", 
            f"Your identity has been verified by {profile.business_name}. You may now proceed with your booking.",
            f"/bookings/step/quotation/{booking.id}",
            "kyc_update"
        )
            
    elif action == "reject":
        if kyc_record:
            kyc_record.verification_status = "rejected"
            kyc_record.failure_reason = reason
        target_user.is_verified = False
        
        # Update latest verification session
        from ..db.models import VerificationSession
        session = db.query(VerificationSession).filter(VerificationSession.user_id == user_id).order_by(VerificationSession.created_at.desc()).first()
        if session:
            session.status = "rejected"

        # NOTIFY: Failure alert for customer
        await NotificationService.notify_status_update(
            db, user_id, 
            "Identity Action Required", 
            f"Your identity verification was rejected by {profile.business_name}. Reason: {reason}",
            f"/bookings/step/kyc/{booking.id}",
            "kyc_update"
        )
        
    db.commit()

    # --- Real-time WebSocket Notification ---
    # Notify the customer that their verification state has changed
    try:
        await manager.broadcast_to_user(target_user.id, {
            "type": "kyc_update",
            "status": "verified" if action == "approve" else "rejected",
            "reason": reason if action == "reject" else None
        })
    except Exception as e:
        print(f"[KYC WS] Failed to notify user {user_id}: {e}")

    return RedirectResponse(url=f"/caterer/compliance/view/{user_id}?success_msg=Identity+{action}d+successfully", status_code=303)


# --- SMART PRICING & QUICK BOOK SYSTEM ---
from ..services.pricing_service import PricingService

@router.get("/ingredients", response_class=HTMLResponse)
async def manage_ingredients(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    ingredients = db.query(None).filter(
        None.caterer_id == user.caterer_profile.id,
        None.is_archived == False
    ).order_by(None.name).all()
    
    return templates.TemplateResponse("caterer/ingredients.html", {
        "request": request,
        "user": user,
        "ingredients": ingredients,
        "active_page": "ingredients" # Corrected active page to highlight the sidebar link
    })

@router.get("/api/ingredients/list")
async def list_ingredients_api(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    ingredients = db.query(None).filter(
        None.caterer_id == user.caterer_profile.id,
        None.is_archived == False
    ).order_by(None.name).all()
    
    return [{"id": i.id, "name": i.name, "unit": i.unit, "unit_price": i.unit_price} for i in ingredients]

@router.post("/api/ingredients")
async def save_ingredient(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    return {"status": "error", "message": "Not implemented"}

@router.delete("/api/ingredients/{ingredient_id}")
async def delete_ingredient(
    ingredient_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    return {"status": "error", "message": "Not implemented"}

@router.get("/api/menu-items/{menu_item_id}/ingredients")
async def get_menu_item_ingredients(
    menu_item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    menu_item = db.query(models.MenuItem).get(menu_item_id)
    if not menu_item or menu_item.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    ingredients = []
    return {
        "menu_item_id": menu_item_id,
        "name": menu_item.name,
        "ingredients": ingredients,
        "total_cost": menu_item.cost_price
    }

@router.post("/api/menu-items/{menu_item_id}/ingredients")
async def save_menu_item_ingredients(
    menu_item_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    return {"status": "error", "message": "Not implemented"}

@router.post("/api/packages/{package_id}/roi")
async def save_package_roi(
    package_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    data = await request.json()
    markup_type = data.get("markup_type", "percentage")
    markup_value = float(data.get("markup_value") or 0)

    package = db.query(models.CateringPackage).get(package_id)
    if not package or package.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Package not found")
    
    package.markup_type = markup_type
    package.markup_value = markup_value
    
    db.commit()
    
    # Recalculate package selling price
    PricingService.calculate_package_cost(db, package_id)
    
    return {"status": "success", "new_price": package.price}

@router.get("/api/quick-quotation/{package_id}")
async def get_quick_quotation(
    package_id: int,
    pax: int = 10,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).get(package_id)
    if not package or package.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Package not found")
    
    PricingService.calculate_package_cost(db, package_id)
    
    cost_per_pax = package.cost_price
    total_cost = cost_per_pax * pax
    total_price = package.price * pax
    roi = total_price - total_cost
    
    breakdown = []
    for item in package.menu_items:
        breakdown.append({
            "name": item.name,
            "cost_per_pax": item.cost_price,
            "ingredients": []
        })

    return {
        "package_name": package.name,
        "pax": pax,
        "cost_per_pax": cost_per_pax,
        "total_cost": total_cost,
        "total_price": total_price,
        "roi": roi,
        "markup_label": f"{package.markup_value}%" if package.markup_type == 'percentage' else f"₱{package.markup_value}",
        "breakdown": breakdown
    }

@router.get("/api/validate-customer-email")
async def validate_customer_email(
    email: str, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    """Detects if a customer email is already registered in the system."""
    target_user = db.query(models.User).filter(models.User.email == email).first()
    if target_user:
        return {
            "exists": True, 
            "name": f"{target_user.first_name} {target_user.last_name}",
            "role": target_user.role
        }
    return {"exists": False}

# --- ELITE CRM API ENDPOINTS ---

@router.post("/api/customers/register")
async def register_manual_customer(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    try:
        form_data = await request.form()
        first_name = form_data.get("first_name", "").strip()
        middle_name = form_data.get("middle_name", "").strip()
        last_name = form_data.get("last_name", "").strip()
        email = form_data.get("email", "").strip()
        phone = form_data.get("phone", "").strip()
        notes = form_data.get("notes", "").strip()
        
        # Address parts
        province = form_data.get("province", "").strip()
        city = form_data.get("city", "").strip()
        barangay = form_data.get("barangay", "").strip()
        landmark = form_data.get("landmark", "").strip()
        
        if not first_name or not last_name or not email:
            return {"status": "error", "message": "First Name, Last Name, and Email are required."}
            
        # Check if user exists by email
        existing_user = db.query(models.User).filter(models.User.email == email).first()
        if existing_user:
            return {"status": "error", "message": "A client with this email already exists in the master database."}

        # Check if phone already exists
        if phone:
            existing_phone = db.query(models.User).filter(models.User.phone_number == phone).first()
            if existing_phone:
                return {"status": "error", "message": "This phone number is already registered."}
                
        # Check exact identity duplicate among customers only
        q_identity = db.query(models.User).filter(
            models.User.first_name == first_name,
            models.User.last_name == last_name,
            models.User.role == "customer"
        )
        if middle_name:
            q_identity = q_identity.filter(models.User.middle_name == middle_name)
        else:
            q_identity = q_identity.filter((models.User.middle_name == None) | (models.User.middle_name == ""))
            
        if q_identity.first():
            return {"status": "error", "message": "A customer with this exact First, Middle, and Last name already exists."}
            
        # Construct Address
        address_parts = [p for p in [landmark, barangay, city, province] if p]
        full_address = ", ".join(address_parts)
        
        # Create a new "Manual/Walk-in" style user
        new_user = models.User(
            email=email,
            first_name=first_name,
            middle_name=middle_name if middle_name else None,
            last_name=last_name,
            phone_number=phone,
            address=full_address if full_address else None,
            role="customer",
            status="active",
            is_verified=True,
            auth_provider="manual_entry",
            investigation_notes=notes if notes else None
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {"status": "success", "message": "Client registered successfully.", "customer_id": new_user.id}
    except Exception as e:
        print(f"[CRM] Error: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/api/customers/validate")
async def validate_customer_api(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    try:
        data = await request.json()
        email = data.get("email", "").strip()
        phone = data.get("phone", "").strip()
        exclude_id = data.get("exclude_id")
        
        if email:
            q = db.query(models.User).filter(models.User.email == email)
            if exclude_id:
                q = q.filter(models.User.id != int(exclude_id))
            if q.first():
                return {"status": "error", "field": "email", "message": "This email is already registered."}
                
        if phone:
            q = db.query(models.User).filter(models.User.phone_number == phone)
            if exclude_id:
                q = q.filter(models.User.id != int(exclude_id))
            if q.first():
                return {"status": "error", "field": "phone", "message": "Phone number is already registered."}
                
        # Validate Identity
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        middle_name = data.get("middle_name", "").strip()
        
        if first_name and last_name:
            q = db.query(models.User).filter(
                models.User.first_name == first_name,
                models.User.last_name == last_name,
                models.User.role == "customer"
            )
            # Match middle name (or absence thereof) if passed
            if middle_name:
                q = q.filter(models.User.middle_name == middle_name)
            else:
                q = q.filter((models.User.middle_name == None) | (models.User.middle_name == ""))
                
            if exclude_id:
                q = q.filter(models.User.id != int(exclude_id))
            
            existing = q.first()
            if existing:
                return {"status": "error", "field": "identity", "message": "A client with this exact First, Middle, and Last name already exists."}
                
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/api/customers/{customer_id}/details")
async def get_customer_crm_details(
    customer_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    target_user = db.query(models.User).filter(models.User.id == customer_id).first()
    if not target_user:
        return {"status": "error", "message": "Customer not found."}
        
    # Get bookings for THIS caterer
    bookings = db.query(models.Booking).filter(
        models.Booking.user_id == customer_id,
        models.Booking.caterer_id == user.caterer_profile.id
    ).order_by(models.Booking.event_date.desc()).all()
    
    total_spent = sum((b.total_price or b.total_amount or 0) for b in bookings if b.status == "completed")
    
    # Calculate status dynamically
    status = "REGULAR"
    if len(bookings) >= 3: status = "VIP"
    if target_user.status == "blacklisted": status = "BLACKLISTED"
    
    history = []
    for b in bookings:
        history.append({
            "id": b.id,
            "ref_no": f"{b.id:05d}",
            "date": b.event_date.isoformat() if b.event_date else None,
            "amount": float(b.total_price or b.total_amount or 0),
            "status": b.status,
            "type": b.status.upper(),
            "package_name": b.package.name if b.package else (b.event_type or "Custom Event")
        })

    return {
        "id": target_user.id,
        "first_name": target_user.first_name,
        "middle_name": target_user.middle_name,
        "last_name": target_user.last_name,
        "email": target_user.email,
        "phone": target_user.phone_number,
        "address": target_user.address,
        "status": status,
        "total_spent": float(total_spent),
        "total_bookings": len(bookings),
        "created_at": target_user.created_at.isoformat(),
        "notes": target_user.investigation_notes or "No notes added yet.",
        "history": history
    }

@router.post("/api/customers/{customer_id}/edit")
async def update_customer_crm_profile(
    customer_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    try:
        target_user = db.query(models.User).filter(models.User.id == customer_id).first()
        if not target_user:
            return {"status": "error", "message": "Customer not found."}
            
        form_data = await request.form()
        f_name = form_data.get("first_name", "").strip()
        l_name = form_data.get("last_name", "").strip()
        email = form_data.get("email", "").strip()
        phone = form_data.get("phone", "").strip()
        notes = form_data.get("notes", "").strip()
        
        if not f_name or not email:
            return {"status": "error", "message": "First Name and Email are required."}

        # Check if email is used by someone else
        existing_email = db.query(models.User).filter(models.User.email == email, models.User.id != customer_id).first()
        if existing_email:
            return {"status": "error", "message": "This email is already in use by another user."}

        # Check if phone is used by someone else
        if phone:
            existing_phone = db.query(models.User).filter(models.User.phone_number == phone, models.User.id != customer_id).first()
            if existing_phone:
                return {"status": "error", "message": "This phone number is already registered to another customer."}
            
        target_user.first_name = f_name
        target_user.last_name = l_name
        target_user.email = email
        target_user.phone_number = phone
        target_user.investigation_notes = notes
        
        db.commit()
        return {"status": "success", "message": "Customer profile updated successfully."}
        
    except Exception as e:
        print(f"[CRM Update] Error: {e}")
        return {"status": "error", "message": "Failed to update profile due to a system error."}


@router.post("/api/customers/{customer_id}/blacklist")
async def blacklist_customer_api(
    customer_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    target_user = db.query(models.User).filter(models.User.id == customer_id).first()
    if not target_user:
        return {"status": "error", "message": "Customer not found."}
        
    try:
        data = await request.json()
        reason = data.get("reason", "").strip()
    except:
        reason = ""
        
    if target_user.status == "blacklisted":
        target_user.status = "active"
        msg = "Customer access restored."
        if reason:
            target_user.investigation_notes = (target_user.investigation_notes or "") + f"\n[RESTORED] {datetime.now().strftime('%Y-%m-%d')}: {reason}"
    else:
        target_user.status = "blacklisted"
        msg = "Customer blacklisted and blocked from further bookings."
        if reason:
            target_user.investigation_notes = (target_user.investigation_notes or "") + f"\n[BLACKLISTED] {datetime.now().strftime('%Y-%m-%d')}: {reason}"
            
    db.commit()
    return {"status": "success", "message": msg}

@router.post("/api/customers/{customer_id}/toggle-vip")
async def toggle_vip_status_api(
    customer_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    # For now, VIP is dynamic (>=3 bookings), so we return a helpful message
    return {"status": "success", "message": "VIP status is calculated automatically based on booking volume (3+ bookings)."}

# ──────────────────────────────────────────────────────
# SETTINGS: Gallery Archive
# ──────────────────────────────────────────────────────
@router.post("/gallery/{item_id}/archive")
async def archive_gallery_item(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.CatererGallery).filter(
        models.CatererGallery.id == item_id,
        models.CatererGallery.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Gallery item not found")
    
    item.is_archived = True
    db.commit()
    return {"status": "success", "message": "Gallery item archived."}

# ──────────────────────────────────────────────────────
# SETTINGS: Notification Preferences
# ──────────────────────────────────────────────────────
@router.post("/settings/notifications")
async def update_notification_preferences(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    data = await request.json()
    profile = user.caterer_profile
    
    # Build preferences object from submitted data
    prefs = {
        "email_new_booking": data.get("email_new_booking", True),
        "email_payment_confirmed": data.get("email_payment_confirmed", True),
        "email_weekly_summary": data.get("email_weekly_summary", False),
        "push_messages": data.get("push_messages", True),
        "email_review_received": data.get("email_review_received", True)
    }
    
    profile.notification_preferences = prefs
    db.commit()
    return {"status": "success", "message": "Notification preferences updated."}

# ──────────────────────────────────────────────────────
# SETTINGS: Account Deactivation
# ──────────────────────────────────────────────────────
@router.post("/settings/deactivate")
async def deactivate_account(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    try:
        data = await request.json()
    except Exception:
        data = {}
    reason = data.get("reason", "No reason provided")
    profile = user.caterer_profile
    
    profile.account_status = "Deactivated"
    profile.deactivation_reason = reason
    profile.deactivated_at = datetime.now()
    
    db.commit()
    return {"status": "success", "message": "Account deactivated. You will be logged out."}

@router.post("/settings/reactivate")
async def reactivate_account(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    profile.account_status = "Active"
    profile.deactivation_reason = None
    profile.deactivated_at = None
    db.commit()
    return {"status": "success", "message": "Account reactivated successfully!"}

# ──────────────────────────────────────────────────────
# SETTINGS: Reset Brand to Defaults
# ──────────────────────────────────────────────────────
@router.post("/settings/reset-brand")
async def reset_brand_defaults(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    profile.primary_color = None
    profile.secondary_color = None
    profile.accent_color = None
    profile.highlight_color = None
    profile.font_family = None
    profile.border_radius = None
    profile.dashboard_texture = "none"
    profile.sidebar_decoration = "none"
    profile.header_decoration = "none"
    profile.sidebar_mode = "full"
    profile.show_platform_logo = True
    db.commit()
    return {"status": "success", "message": "Brand settings reset to OccaServe defaults."}

# ──────────────────────────────────────────────────────
# FINANCIALS & OVERHEAD EXPENSES
# ──────────────────────────────────────────────────────
@router.get("/financials", response_class=HTMLResponse)
async def financials_page(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    
    # Get all business expenses for this caterer
    expenses = db.query(models.BusinessExpense).filter(
        models.BusinessExpense.caterer_id == profile.id
    ).order_by(models.BusinessExpense.date_incurred.desc()).all()
    
    # Calculate some basic stats
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    monthly_expenses = sum(e.amount for e in expenses if e.date_incurred and e.date_incurred.month == current_month and e.date_incurred.year == current_year)
    total_expenses = sum(e.amount for e in expenses)
    
    config = db.query(models.WebsiteConfig).first()
    comm_rate = config.commission_rate if config else 10.0
    comm_fixed = config.commission_fixed_amount if config else 20.0

    all_completed_bookings = db.query(models.Booking).filter(
        models.Booking.caterer_id == profile.id,
        models.Booking.status == 'completed'
    ).all()
    
    total_rev = 0
    total_comm = 0
    for b in all_completed_bookings:
        amt = float(b.total_amount or b.total_price or 0)
        total_rev += amt
        total_comm += (amt * (comm_rate / 100.0)) + comm_fixed
        
    net_earnings = total_rev - total_comm
    
    return templates.TemplateResponse("caterer/financials.html", {
        "request": request,
        "user": user,
        "active_page": "financials",
        "expenses": expenses,
        "monthly_overhead": monthly_expenses,
        "total_overhead": total_expenses,
        "total_rev": total_rev,
        "total_comm": total_comm,
        "net_earnings": net_earnings
    })

@router.post("/api/financials/expense")
async def add_business_expense(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    data = await request.json()
    profile = user.caterer_profile
    
    try:
        new_expense = models.BusinessExpense(
            caterer_id=profile.id,
            category=data.get('category'),
            description=data.get('description'),
            amount=float(data.get('amount')),
            date_incurred=datetime.strptime(data.get('date_incurred'), '%Y-%m-%d') if data.get('date_incurred') else datetime.now().date()
        )
        db.add(new_expense)
        db.commit()
        db.refresh(new_expense)
        return {"status": "success", "message": "Expense logged successfully"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.delete("/api/financials/expense/{expense_id}")
async def delete_business_expense(
    expense_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    expense = db.query(models.BusinessExpense).filter(
        models.BusinessExpense.id == expense_id,
        models.BusinessExpense.caterer_id == user.caterer_profile.id
    ).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
        
    db.delete(expense)
    db.commit()
    return {"status": "success", "message": "Expense deleted"}


@router.post("/api/payments/settle-dues")
async def settle_dues_api(
    billing_period: str = Form(...),
    proof_file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    "Caterer uploads proof of payment to settle platform commission dues."
    import shutil
    import os
    import time
    
    profile = user.caterer_profile
    if profile.outstanding_balance <= 0:
        raise HTTPException(status_code=400, detail="You do not have any outstanding balance to settle.")
        
    import base64
    content_bytes = await proof_file.read()
    b64 = base64.b64encode(content_bytes).decode('utf-8')
    mime = proof_file.content_type or 'image/jpeg'
    proof_url = f"data:{mime};base64,{b64}"
    
    invoice = models.BillingInvoice(
        caterer_id=profile.id,
        billing_period=billing_period,
        amount=profile.outstanding_balance,
        status='pending',
        payment_proof_url=proof_url
    )
    db.add(invoice)
    
    profile.outstanding_balance = 0.0
    
    audit = models.AuditLog(
        user_id=user.id,
        action="DUES_SETTLED_PENDING",
        notes=f"Submitted proof for {billing_period} commission settlement. Awaiting admin verification."
    )
    db.add(audit)
    db.flush()
    
    # Notify admins
    admins = db.query(models.User).filter(models.User.role == 'admin').all()
    for admin in admins:
        new_notif = models.Notification(
            user_id=admin.id,
            title="Commission Settlement Pending",
            message=f"{profile.business_name} has submitted a proof of payment for {billing_period}.",
            link="/admin/payouts",
            type="info"
        )
        db.add(new_notif)
    
    db.commit()
    
    return {"status": "success", "message": "Settlement proof submitted successfully"}


@router.post("/api/bookings/{booking_id}/report")
async def caterer_report_booking(
    booking_id: int,
    request: Request,
    reason: str = Form(...),
    details: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    import uuid
    from fastapi.responses import JSONResponse
    
    # Verify caterer owns this booking
    booking = db.query(models.Booking).join(models.CatererProfile).filter(
        models.Booking.id == booking_id,
        models.CatererProfile.user_id == user.id
    ).first()

    if not booking:
        return JSONResponse(status_code=404, content={"success": False, "message": "Booking not found"})

    # Check if a report already exists from this caterer for this booking
    existing = db.query(models.DisputeReport).filter(
        models.DisputeReport.booking_id == booking_id,
        models.DisputeReport.reporter_id == user.id
    ).first()

    if existing:
        return JSONResponse(status_code=400, content={"success": False, "message": f"You already have an active report for this booking: {existing.reference_id}"})

    reference_id = f"REP-{uuid.uuid4().hex[:8].upper()}"
    
    report = models.DisputeReport(
        reference_id=reference_id,
        booking_id=booking_id,
        reporter_id=user.id,
        reported_id=booking.user_id, # Report the customer
        reason=reason,
        details=details,
        status="pending"
    )
    db.add(report)
    db.commit()

    return JSONResponse(content={"success": True, "message": f"Report submitted successfully. Reference ID: {reference_id}"})


@router.post("/verification/submit")
async def submit_verification(
    background_tasks: BackgroundTasks,
    id_type: str = Form(...),
    permit_expiry: Optional[str] = Form(None),
    id_front: Optional[UploadFile] = File(None),
    id_back: Optional[UploadFile] = File(None),
    permit: Optional[UploadFile] = File(None),
    dti: Optional[UploadFile] = File(None),
    bir: Optional[UploadFile] = File(None),
    mayors: Optional[UploadFile] = File(None),
    selfie: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = db.query(models.CatererProfile).filter(models.CatererProfile.user_id == user.id).first()
    if not profile:
        return JSONResponse(status_code=400, content={"success": False, "message": "Profile not found."})

    from ..core.utils import validate_file_type_and_size
    import shutil
    import os
    import time
    
    upload_dir = "app/static/uploads/verification"
    os.makedirs(upload_dir, exist_ok=True)
    
    from ..core.encryption import encrypt_data
    
    def save_file(file_obj, prefix):
        if not file_obj or not file_obj.filename: return None
        
        content = file_obj.file.read()
        from ..core.utils import validate_file_type_and_size
        error = validate_file_type_and_size(content, file_obj.filename)
        if error:
            raise ValueError(error)
            
        # Instead of saving locally, convert directly to Base64
        import base64
        b64 = base64.b64encode(content).decode('utf-8')
        mime = file_obj.content_type or "image/jpeg"
        actual_mime = "application/pdf" if "pdf" in mime.lower() else "image/jpeg"
        if "png" in mime.lower(): actual_mime = "image/png"
        return f"data:{actual_mime};base64,{b64}"
    
    try:
        if permit:
            url = save_file(permit, "permit")
            if url: profile.permit_url = url
            
        if permit_expiry:
            from datetime import datetime
            try:
                profile.permit_expiry_date = datetime.strptime(permit_expiry, "%Y-%m-%d").date()
            except:
                pass
                
        if dti:
            url = save_file(dti, "dti")
            if url: profile.dti_url = url
            
        if bir:
            url = save_file(bir, "bir")
            if url: profile.bir_url = url
            
        if mayors:
            url = save_file(mayors, "mayors")
            if url: profile.mayors_permit_url = url
            
        # Update Verification Status
        profile.verification_status = "Pending Review"
        profile.is_verified = False
        if profile.user:
            profile.user.is_verified = False
        
        # Identity Verification
        identity = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == user.id).first()
        if not identity:
            identity = models.IdentityVerification(user_id=user.id, verification_type=id_type, verification_status="Pending Review")
            db.add(identity)
        else:
            identity.verification_type = id_type
            identity.verification_status = "Pending Review"
            
        if id_front:
            url = save_file(id_front, "id_front")
            if url: identity.document_url = url
        if id_back:
            url = save_file(id_back, "id_back")
            if url: identity.document_back_url = url
            
        if selfie:
            url = save_file(selfie, "selfie")
            if url: identity.selfie_url = url
            
        db.commit()
        
        # Phase 3: Trigger OCR AI on Manual Uploads
        if identity.document_url:
            full_name = f"{user.first_name} {user.last_name}"
            
            async def run_caterer_kyc_bg(id_url, selfie_url, user_name, user_id, type_of_id):
                try:
                    from ..db.database import SessionLocal
                    from ..services.verification import verification_service
                    db_session = SessionLocal()
                    
                    selfie_paths = [selfie_url] if selfie_url else []
                    result = await verification_service.verify_identity_v2(
                        id_path=id_url, 
                        selfie_paths=selfie_paths, 
                        full_name=user_name, 
                        id_number="", 
                        id_type=type_of_id, 
                        db=db_session, 
                        user_id=user_id
                    )
                    
                    ident = db_session.query(models.IdentityVerification).filter_by(user_id=user_id).first()
                    if ident:
                        new_ocr = result.get("ocr_data")
                        if new_ocr and isinstance(new_ocr, dict) and new_ocr.get("fields"):
                            ident.ocr_data = new_ocr
                        elif ident.ocr_data is None:
                            ident.ocr_data = {}
                            
                        ident.fraud_score = result.get("fraud_score", 0)
                        ident.match_score = result.get("face_match_confidence", 0.0)
                        ident.face_detected = result.get("liveness_score", 0.0) > 0 or result.get("face_match_confidence", 0.0) > 0
                        ident.id_detected = result.get("ocr_match", False) or (isinstance(ident.ocr_data, dict) and ident.ocr_data.get("full_name") is not None)
                        ident.liveness_status = "passed" if result.get("liveness_score", 0.0) > 0.4 else "failed"
                        db_session.commit()
                        
                    db_session.close()
                except Exception as e:
                    print(f"[CATERER OCR BACKGROUND ERROR] {e}")

            background_tasks.add_task(run_caterer_kyc_bg, identity.document_url, identity.selfie_url, full_name, user.id, id_type)

        # Phase 1: Notify Admins of Caterer Document Submission
        from ..services.realtime import manager
        from ..core.email_service import send_notification_email
        from ..core.config import settings
        import asyncio
        
        admins = db.query(models.User).filter(models.User.role == "admin").all()
        for admin in admins:
            new_notif = models.Notification(
                user_id=admin.id,
                title="KYC Submission",
                message=f"Caterer {profile.business_name} has submitted verification documents.",
                link=f"/admin/caterers?caterer_id={user.id}&action=verify",
                type="info"
            )
            db.add(new_notif)
            db.commit()
            
            # Send Email Alert to Admin
            if admin.email:
                send_notification_email(
                    to_email=admin.email,
                    subject=f"New KYC Submission: {profile.business_name}",
                    message=f"Hello Admin,\n\nA caterer ({profile.business_name}) has just submitted their identity and business documents for KYC verification.\n\nPlease log in to the OccaServe Admin Panel to review their application and verify their account.",
                    link=f"{settings.SITE_URL.rstrip('/')}/admin/caterers?caterer_id={user.id}&action=verify"
                )
            
            count = db.query(models.Notification).filter(models.Notification.user_id == admin.id, models.Notification.is_read == False).count()
            asyncio.create_task(manager.broadcast_to_user(admin.id, {
                "type": "new_notification",
                "message": f"KYC update from {profile.business_name}",
                "count": count
            }))
            
        return JSONResponse(content={"success": True, "message": "Verification submitted successfully."})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


@router.post("/rentals/{booking_id}/release")
async def release_rental_equipment(
    booking_id: int,
    request: Request,
    release_photo: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):
    user = get_current_user_from_session(request, db)
    if not user or user.role != "caterer":
        return JSONResponse(status_code=403, content={"success": False, "message": "Unauthorized"})

    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking or booking.caterer.user_id != user.id:
        return JSONResponse(status_code=404, content={"success": False, "message": "Rental not found."})

    # Validate Payment
    if booking.security_deposit_status == "unpaid":
        return JSONResponse(status_code=400, content={"success": False, "message": "Cannot release equipment. Security deposit is unpaid."})

    try:
        # Save Release Photo
        import base64
        content_bytes = await release_photo.read()
        b64 = base64.b64encode(content_bytes).decode('utf-8')
        mime = release_photo.content_type or 'image/jpeg'
        booking.release_photo_url = f"data:{mime};base64,{b64}"
        booking.status = "released"
        
        # Log History
        db.add(models.BookingHistory(booking_id=booking.id, status="released", notes="Equipment released to customer with proof of condition."))
        db.commit()
        return JSONResponse(content={"success": True, "message": "Equipment marked as Released."})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


@router.post("/rentals/{booking_id}/inspect")
async def inspect_rental_equipment(
    booking_id: int,
    request: Request,
    missing_items: int = Form(0),
    deduction_amount: float = Form(0.0),
    damage_photo: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db)
):
    user = get_current_user_from_session(request, db)
    if not user or user.role != "caterer":
        return JSONResponse(status_code=403, content={"success": False, "message": "Unauthorized"})

    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking or booking.caterer.user_id != user.id:
        return JSONResponse(status_code=404, content={"success": False, "message": "Rental not found."})

    # Strict Validation: If deduction > 0, photo is MANDATORY
    if deduction_amount > 0 and (not damage_photo or not damage_photo.filename):
        return JSONResponse(status_code=400, content={"success": False, "message": "Damage Proof Photo is required when deducting from the security deposit."})

    # Strict Validation: Cannot deduct more than deposit
    if deduction_amount > booking.security_deposit_amount:
        return JSONResponse(status_code=400, content={"success": False, "message": f"Deduction cannot exceed the total security deposit of ₱{booking.security_deposit_amount}."})

    try:
        if damage_photo and damage_photo.filename:
            import base64
            content_bytes = await damage_photo.read()
            b64 = base64.b64encode(content_bytes).decode('utf-8')
            mime = damage_photo.content_type or 'image/jpeg'
            booking.damage_proof_url = f"data:{mime};base64,{b64}"

        booking.missing_items_count = missing_items
        booking.damage_deduction_amount = deduction_amount
        booking.status = "completed"
        
        # Determine Deposit Status
        if deduction_amount > 0:
            if deduction_amount >= booking.security_deposit_amount:
                booking.security_deposit_status = "forfeited"
            else:
                booking.security_deposit_status = "partially_refunded"
        else:
            booking.security_deposit_status = "fully_refunded"

        db.add(models.BookingHistory(booking_id=booking.id, status="completed", notes=f"Inspection completed. Deduction: ₱{deduction_amount}."))
        db.commit()
        return JSONResponse(content={"success": True, "message": "Inspection recorded and Rental completed."})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

