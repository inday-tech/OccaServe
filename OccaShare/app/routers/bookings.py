from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from ..core.templates import templates
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, time, datetime
from ..db import database, models
from ..core import security as auth
from ..services.verification import verification_service
from ..services.email import EmailService
import shutil
import os
import uuid
import base64
import json
import httpx
from ..services.realtime import manager
from ..services.notification import NotificationService
from PIL import Image
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False


router = APIRouter(prefix="/bookings", tags=["bookings"])

UPLOAD_DIR = "app/static/uploads/verification"
os.makedirs(UPLOAD_DIR, exist_ok=True)

PROOF_UPLOAD_DIR = "app/static/uploads/payment_proofs"
os.makedirs(PROOF_UPLOAD_DIR, exist_ok=True)

# --- Helper Functions ---

def get_current_user_from_session(request: Request, db: Session):
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    if token.startswith("Bearer "):
        token = token.split(" ", 1)[1]
    
    try:
        user = auth.verify_token(token, db)
        return user
    except:
        return None

def save_upload_file(upload_file: UploadFile) -> str:
    file_extension = os.path.splitext(upload_file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
        
    return f"/static/uploads/verification/{unique_filename}"

def save_base64_file(base64_str: str) -> str:
    if not base64_str or "," not in base64_str:
        return ""
    
    header, encoded = base64_str.split(",", 1)
    file_extension = ".jpg" # Default to jpg
    if "png" in header: file_extension = ".png"
    
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(base64.b64decode(encoded))
        
    return f"/static/uploads/verification/{unique_filename}"

@router.get("/my")
async def my_bookings_redirect():
    return RedirectResponse(url="/customer/bookings", status_code=303)

# --- Wizard Steps ---

# --- Dedicated A La Carte Checkout ---
@router.get("/alacarte/checkout/{caterer_id}")
async def alacarte_checkout_page(request: Request, caterer_id: int, menu_id: str, db: Session = Depends(database.get_db)):
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/bookings/alacarte/checkout/{caterer_id}?menu_id={menu_id}")
    
    caterer = db.query(models.CatererProfile).get(caterer_id)
    
    # Parse multiple IDs
    try:
        id_list = [int(id_str.strip()) for id_str in menu_id.split(",") if id_str.strip()]
    except ValueError:
        return RedirectResponse(url="/marketplace", status_code=303)

    menu_items = db.query(models.MenuItem).filter(models.MenuItem.id.in_(id_list)).all()
    
    if not caterer or not menu_items:
        return RedirectResponse(url="/marketplace", status_code=303)
        
    return templates.TemplateResponse("customer/booking_wizard/alacarte_checkout.html", {
        "request": request,
        "user": user,
        "caterer": caterer,
        "menu_items": menu_items,
        "menu_id_raw": menu_id,
        "current_step": 1
    })

@router.post("/alacarte/checkout/draft")
async def alacarte_checkout_draft(
    request: Request,
    caterer_id: int = Form(...),
    menu_id: str = Form(""),
    cart_data: Optional[str] = Form(None),
    full_name: str = Form(...),
    contact_number: str = Form(...),
    delivery_date: str = Form(...),
    delivery_time: str = Form(...),
    address: Optional[str] = Form(""),
    quantity: int = Form(1),
    total_amount: float = Form(...),
    db: Session = Depends(database.get_db)
):
    user = get_current_user_from_session(request, db)
    if not user: return {"success": False, "message": "Unauthorized"}
    
    try:
        event_date_obj = date.fromisoformat(delivery_date)
        event_time_obj = datetime.strptime(delivery_time, "%H:%M").time()
        
        # Create Draft Booking
        new_booking = models.Booking(
            user_id=user.id,
            caterer_id=caterer_id,
            event_name=f"Food Order (Draft): {full_name}",
            event_type="Ala Carte Order",
            event_date=event_date_obj,
            event_time=event_time_obj,
            venue_address=address,
            guest_count=quantity,
            total_amount=total_amount,
            total_price=total_amount,
            reservation_fee=total_amount,
            status="draft" 
        )
        db.add(new_booking)
        db.flush()

        # Add Menu Items to Draft
        if cart_data:
            cart_items = json.loads(cart_data)
            for item in cart_items:
                m_item = db.query(models.MenuItem).get(int(item['id']))
                if m_item:
                    booking_item = models.BookingMenuItem(
                        booking_id=new_booking.id,
                        menu_item_id=m_item.id,
                        price=m_item.price,
                        quantity=int(item.get('quantity', 1)),
                        choices=item.get('choices')
                    )
                    db.add(booking_item)
        elif menu_id:
            id_list = [int(id_str.strip()) for id_str in menu_id.split(",") if id_str.strip()]
            menu_items = db.query(models.MenuItem).filter(models.MenuItem.id.in_(id_list)).all()
            
            for m_item in menu_items:
                booking_item = models.BookingMenuItem(
                    booking_id=new_booking.id,
                    menu_item_id=m_item.id,
                    price=m_item.price
                )
                db.add(booking_item)
            
        db.commit()

        return {"success": True, "booking_id": new_booking.id}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": str(e)}

@router.post("/alacarte/checkout/submit")
async def alacarte_checkout_submit(
    request: Request,
    caterer_id: int = Form(...),
    menu_id: str = Form(""), # Legacy
    cart_data: Optional[str] = Form(None), # New JSON cart payload: [{"id": 1, "quantity": 2, "choices": [...]}]
    full_name: str = Form(...),
    contact_number: str = Form(...),
    delivery_date: str = Form(...),
    delivery_time: str = Form(...),
    address: Optional[str] = Form(""),
    quantity: int = Form(1), # Legacy global guest count
    fulfillment: str = Form(...),
    payment_method: str = Form(...),
    total_amount: float = Form(...),
    landmark: Optional[str] = Form(None),
    booking_id: Optional[int] = Form(None),
    db: Session = Depends(database.get_db)
):
    user = get_current_user_from_session(request, db)
    if not user:
        return {"success": False, "message": "Unauthorized"}
    
    try:
        # Spam Limit Validation (Flow B Rule 1)
        unpaid_spam_count = db.query(models.Booking).filter(
            models.Booking.user_id == user.id,
            models.Booking.status.in_(['draft', 'pending', 'pending_quotation', 'awaiting_caterer', 'awaiting_payment', 'pending_payment']),
            models.Booking.id != (booking_id or 0)
        ).count()
        if unpaid_spam_count >= 2:
            return {"success": False, "message": "Spam Protection: You have 2 or more unpaid/pending bookings. Please complete them first."}

        # 1. Update or Create Booking
        event_date_obj = date.fromisoformat(delivery_date)
        event_time_obj = datetime.strptime(delivery_time, "%H:%M").time()
        
        # New Payment Logic for Ala Carte:
        if payment_method in ["CASH", "COD"]:
            reservation_fee = 0
            status = "confirmed"
        else:
            reservation_fee = total_amount
            status = "pending_payment"
        
        booking = None
        if booking_id:
            booking = db.query(models.Booking).get(booking_id)
            if booking and booking.user_id == user.id:
                booking.status = status
                booking.payment_method = payment_method
                booking.venue_address = address if fulfillment == "delivery" else "PICKUP"
                booking.special_requests = landmark
                booking.total_amount = total_amount
                booking.reservation_fee = reservation_fee
                # Clear old items to re-save
                db.query(models.BookingMenuItem).filter(models.BookingMenuItem.booking_id == booking.id).delete()
        
        # Check if items are rentals
        is_rental = False
        if cart_data:
            cart_items = json.loads(cart_data)
            for item in cart_items:
                m_item = db.query(models.MenuItem).get(int(item['id']))
                if m_item and m_item.category and m_item.category.lower() == 'rentals':
                    is_rental = True
                    break

        event_name = f"Equipment Rental: {full_name}" if is_rental else f"Food Order: {full_name}"
        event_type = "Equipment Rental" if is_rental else "Ala Carte Order"
        
        if booking:
            booking.event_name = event_name
            booking.event_type = event_type
            
        if not booking:
            booking = models.Booking(
                user_id=user.id,
                caterer_id=caterer_id,
                event_name=event_name,
                event_type=event_type,
                event_date=event_date_obj,
                event_time=event_time_obj,
                venue_address=address if fulfillment == "delivery" else "PICKUP",
                guest_count=quantity,
                total_amount=total_amount,
                total_price=total_amount,
                reservation_fee=reservation_fee,
                status=status,
                payment_method=payment_method,
                special_requests=landmark
            )
            db.add(booking)
            db.flush()

        # Add Menu Items
        if cart_data:
            cart_items = json.loads(cart_data)
            for item in cart_items:
                m_item = db.query(models.MenuItem).get(int(item['id']))
                if m_item:
                    booking_item = models.BookingMenuItem(
                        booking_id=booking.id,
                        menu_item_id=m_item.id,
                        price=m_item.price,
                        quantity=int(item.get('quantity', 1)),
                        choices=item.get('choices')
                    )
                    db.add(booking_item)
        elif menu_id:
            # Legacy Fallback
            id_list = [int(id_str.strip()) for id_str in menu_id.split(",") if id_str.strip()]
            menu_items = db.query(models.MenuItem).filter(models.MenuItem.id.in_(id_list)).all()
            for m_item in menu_items:
                booking_item = models.BookingMenuItem(
                    booking_id=booking.id,
                    menu_item_id=m_item.id,
                    price=m_item.price,
                    quantity=1
                )
                db.add(booking_item)

        db.commit()
        return {"success": True, "booking_id": booking.id}
    except Exception as e:
        db.rollback()
        print(f"Error in alacarte submit: {e}")
        return {"success": False, "message": str(e)}


# Step 1: Initialize/Select Caterer (from Profile Page)
@router.get("/start/{caterer_id}")
async def start_booking(request: Request, caterer_id: int, package_id: Optional[int] = None, db: Session = Depends(database.get_db)):
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/bookings/start/{caterer_id}")
    
    # Initialize/Reset booking session data
    request.session["booking_data"] = {
        "caterer_id": caterer_id,
        "package_id": package_id,
        "user_id": user.id
    }
    
    # If no package selected, go to Menu Selection first
    if not package_id:
        return RedirectResponse(url=f"/bookings/step/menu/{caterer_id}", status_code=303)
    
    # Always go to Phase 1 (Details) if package is already selected
    return RedirectResponse(url="/bookings/step/details", status_code=303)

@router.get("/continue/{booking_id}")
async def continue_draft_booking(booking_id: int, request: Request, db: Session = Depends(database.get_db)):
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/bookings/continue/{booking_id}")
        
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.user_id != user.id:
        return RedirectResponse(url="/customer/dashboard?error_msg=Booking+not+found", status_code=303)
        
    if booking.status not in ['draft', 'pending_quotation', 'awaiting_caterer', 'awaiting_payment']:
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}", status_code=303)
        
    # Re-populate session so back-navigation works
    request.session["booking_data"] = {
        "booking_id": booking.id,
        "caterer_id": booking.caterer_id,
        "package_id": booking.package_id,
        "user_id": user.id
    }
    
    # Step logic routing
    # 1. Does user need KYC?
    # NEW: Skip KYC if user has booking history
    has_history = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        models.Booking.id != booking.id,
        models.Booking.status.notin_(['draft', 'cancelled', 'pending_quotation'])
    ).first() is not None

    if not user.is_verified and not user.is_kyc_complete and not has_history:
        return RedirectResponse(url=f"/bookings/step/kyc/{booking.id}", status_code=303)
        
    # 2. Is there a Quotation yet?
    if not booking.quotation:
        # User hasn't finished quotation step
        return RedirectResponse(url=f"/bookings/step/quotation/{booking.id}", status_code=303)
        
    # 3. Has the Quotation been signed?
    if booking.quotation.status == 'signed':
        return RedirectResponse(url=f"/bookings/step/payment/{booking.id}", status_code=303)
        
    # Default fallback to Quotation
    return RedirectResponse(url=f"/bookings/step/quotation/{booking.id}", status_code=303)

@router.get("/step/menu/{caterer_id}", response_class=HTMLResponse)
async def step_menu_page(caterer_id: int, request: Request, db: Session = Depends(database.get_db)):
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/bookings/step/menu/{caterer_id}")
    
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer: raise HTTPException(status_code=404)
    
    packages = db.query(models.CateringPackage).filter(
        models.CateringPackage.caterer_id == caterer_id,
        models.CateringPackage.is_active == True
    ).all()
    
    return templates.TemplateResponse("customer/booking_wizard/step_menu.html", {
        "request": request,
        "caterer": caterer,
        "packages": packages,
        "user": user,
        "current_step": 0, # Step 0 for menu selection if needed
        "active_page": "bookings"
    })

@router.post("/step/menu")
async def step_menu_submit(request: Request, package_id: int = Form(...)):
    data = request.session.get("booking_data", {})
    data["package_id"] = package_id
    request.session["booking_data"] = data
    return RedirectResponse(url="/bookings/step/details", status_code=303)

# Phase 1: Booking Details (Event Info, Date/Time, Guests)
@router.get("/step/details/{booking_id}", response_class=HTMLResponse)
@router.get("/step/details", response_class=HTMLResponse)
async def step_details_page(request: Request, booking_id: Optional[int] = None, db: Session = Depends(database.get_db)):
    user = get_current_user_from_session(request, db)
    if not user:
        next_url = f"/bookings/step/details/{booking_id}" if booking_id else "/bookings/step/details"
        return RedirectResponse(url=f"/auth/login?next={next_url}")
        
    data = request.session.get("booking_data", {})
    
    # Priority: 1. URL path, 2. Session data
    actual_id = booking_id or data.get("booking_id")
    
    booking = None
    if actual_id:
        booking = db.query(models.Booking).get(actual_id)
        if booking and user and booking.user_id == user.id:
            # Sync session if we found a valid booking from URL
            data["booking_id"] = booking.id
            data["caterer_id"] = booking.caterer_id
            data["package_id"] = booking.package_id
            request.session["booking_data"] = data
        else:
            booking = None # Reset if not authorized or not found

    if not data or "caterer_id" not in data:
        return RedirectResponse(url="/customer/marketplace", status_code=303)
    
    package = None
    package_id = data.get("package_id")
    if package_id:
        package = db.query(models.CateringPackage).get(package_id)
    
    caterer = db.query(models.CatererProfile).get(data["caterer_id"])
    
    # All active items for this caterer (to allow swapping)
    all_menu_items = db.query(models.MenuItem).filter(
        models.MenuItem.caterer_id == caterer.id,
        models.MenuItem.is_archived == False
    ).all()
    
    addon_items = [i for i in all_menu_items if i.is_addon]

    # Get selected addons if existing booking
    selected_addon_ids = []
    if booking:
        selected_addon_ids = [item.menu_item_id for item in booking.items if item.is_add_on]

    return templates.TemplateResponse("customer/booking_wizard/step_details.html", {
        "request": request,
        "booking_data": data,
        "booking": booking,
        "package": package,
        "caterer": caterer,
        "all_menu_items": all_menu_items,
        "addon_items": addon_items,
        "selected_addon_ids": selected_addon_ids,
        "user": user,
        "current_step": 1,
        "active_page": "bookings"
    })

@router.post("/step/details")
async def step_details_submit(
    request: Request,
    caterer_id: int = Form(...),
    package_id_str: Optional[str] = Form(None, alias="package_id"),
    booking_id_str: Optional[str] = Form(None, alias="booking_id"),
    event_name: str = Form(...),
    event_type: str = Form(...),
    event_date: date = Form(...),
    event_time: time = Form(...),
    event_end_time_str: Optional[str] = Form(None, alias="event_end_time"),
    guest_count: int = Form(...),
    venue_address: str = Form(...),
    total_price: float = Form(0.0),
    reservation_fee: float = Form(0.0),
    selected_items: list[int] = Form([]),
    selected_addons: list[int] = Form([]),
    special_requests: Optional[str] = Form(""),
    db: Session = Depends(database.get_db)
):
    # Safely parse times and IDs
    event_end_time = None
    if event_end_time_str and event_end_time_str.strip():
        try:
            event_end_time = time.fromisoformat(event_end_time_str)
        except:
            pass
    # Safely parse IDs from strings to handle empty form values
    package_id = int(package_id_str) if package_id_str and package_id_str.strip() else None
    booking_id = int(booking_id_str) if booking_id_str and booking_id_str.strip() else None

    user = get_current_user_from_session(request, db)
    redirect_base = f"/bookings/step/details/{booking_id}" if booking_id else "/bookings/step/details"
    if not user: return RedirectResponse(url=f"/auth/login?next={redirect_base}")

    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer: return RedirectResponse(url=f"/customer/marketplace", status_code=303)

    from datetime import date as dt_date, timedelta, datetime
    today = dt_date.today()
    
    # 🚨 VALIDATION 1: Strict Lead Time Validation
    # Must be at least `caterer.booking_lead_time` days in the future
    lead_time = caterer.booking_lead_time or 3
    min_lead_date = today + timedelta(days=lead_time)
    if event_date < min_lead_date:
        return RedirectResponse(url=f"{redirect_base}?booking_error=Event+date+must+be+at+least+{lead_time}+days+in+advance+for+proper+preparation.", status_code=303)

    # 🚨 VALIDATION 1.5: Sensible Operating Hours Check
    # Restrict events to standard operating hours (6:00 AM to 9:00 PM)
    if event_time.hour < 6 or event_time.hour > 21:
        return RedirectResponse(url=f"{redirect_base}?booking_error=Please+select+a+time+between+6:00+AM+and+9:00+PM.", status_code=303)

    # 🚨 VALIDATION 1.8: Unpaid Booking Spam Limit (Flow B Rule 1)
    unpaid_spam_count = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        models.Booking.status.in_(['draft', 'pending', 'pending_quotation', 'awaiting_caterer', 'awaiting_payment', 'pending_payment']),
        models.Booking.id != (booking_id or 0)
    ).count()

    if unpaid_spam_count >= 2:
        return RedirectResponse(url=f"{redirect_base}?booking_error=Spam+Protection:+You+have+2+or+more+unpaid+or+pending+bookings.+Please+pay+the+downpayment+or+cancel+them+before+making+a+new+one.", status_code=303)

    # 🚨 VALIDATION 2: Anti-Spam / Duplicate Booking Check
    existing_duplicate = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        models.Booking.caterer_id == caterer_id,
        models.Booking.event_date == event_date,
        models.Booking.event_time == event_time,
        models.Booking.id != (booking_id or 0),
        models.Booking.status.notin_(['cancelled'])
    ).first()
    
    if existing_duplicate:
        return RedirectResponse(url=f"{redirect_base}?booking_error=You+already+have+a+booking+request+for+this+exact+schedule+and+caterer.", status_code=303)

    # 🚨 VALIDATION 3: Caterer Overlap / Time-Gap Check
    same_day_bookings = db.query(models.Booking).filter(
        models.Booking.caterer_id == caterer_id,
        models.Booking.event_date == event_date,
        models.Booking.id != (booking_id or 0),
        models.Booking.status.in_(['confirmed', 'preparing', 'in_progress', 'on_the_way'])
    ).all()
    
    turnover = caterer.turnover_hours or 4.0
    for sdb in same_day_bookings:
        if sdb.event_time:
            dt1 = datetime.combine(today, event_time)
            dt2 = datetime.combine(today, sdb.event_time)
            diff_hours = abs((dt1 - dt2).total_seconds()) / 3600.0
            if diff_hours < turnover:
                return RedirectResponse(url=f"{redirect_base}?booking_error=The+caterer+has+another+confirmed+event+around+this+time.+Please+adjust+your+time+by+at+least+{turnover}+hours.", status_code=303)

    # 🚨 VALIDATION 4: Guest Count Bounds
    package = None
    min_guests_required = caterer.min_pax or 1
    if package_id:
        package = db.query(models.CateringPackage).get(package_id)
        if package:
            min_guests_required = package.min_guests or caterer.min_pax or 1
            if package.max_guests and guest_count > package.max_guests:
                return RedirectResponse(url=f"{redirect_base}?booking_error=Guest+count+exceeds+the+package+maximum+capacity+of+{package.max_guests}.", status_code=303)

    if guest_count < min_guests_required:
        return RedirectResponse(url=f"{redirect_base}?booking_error=Guest+count+cannot+be+less+than+the+minimum+requirement+of+{min_guests_required}.", status_code=303)

    # 1. Check Availability (Only if date changed or new booking)
    # [Availability check logic remains same for now]
    availability = db.query(models.Availability).filter(
        models.Availability.caterer_id == caterer_id,
        models.Availability.date == event_date,
        models.Availability.is_available == False
    ).first()
    
    if availability:
        return RedirectResponse(url=f"{redirect_base}?booking_error=Date+unavailable", status_code=303)

    # 2. Create or Update Booking
    booking = None
    if booking_id:
        booking = db.query(models.Booking).get(booking_id)
    
    if booking and booking.user_id == user.id:
        # Update existing
        booking.event_name = event_name
        booking.event_type = event_type
        booking.event_date = event_date
        booking.event_time = event_time
        booking.event_end_time = event_end_time
        booking.venue_address = venue_address
        booking.event_address = venue_address
        booking.guest_count = guest_count
        booking.total_price = total_price
        booking.total_amount = total_price
        booking.reservation_fee = reservation_fee
        booking.special_requests = special_requests
        # Clear old items to re-save
        db.query(models.BookingMenuItem).filter(models.BookingMenuItem.booking_id == booking.id).delete()
    else:
        # Create New Draft
        booking = models.Booking(
            user_id=user.id,
            caterer_id=caterer_id,
            package_id=package_id,
            event_name=event_name,
            event_type=event_type,
            event_date=event_date,
            event_time=event_time,
            event_end_time=event_end_time,
            venue_address=venue_address,
            event_address=venue_address,
            guest_count=guest_count,
            total_price=total_price,
            total_amount=total_price,
            reservation_fee=reservation_fee,
            special_requests=special_requests,
            status="draft"
        )
        db.add(booking)
    
    db.commit()
    db.refresh(booking)

    # 3. Save Selected Items and Validate Rules
    package = db.query(models.CateringPackage).get(package_id) if package_id else None
    
    # Selection Rule Validation
    if package and package.selection_rules:
        category_counts = {}
        for item_id in selected_items:
            mi = db.query(models.MenuItem).get(item_id)
            if mi and not mi.is_addon:
                cat = mi.category or "Others"
                category_counts[cat] = category_counts.get(cat, 0) + 1
                
        for cat, count in category_counts.items():
            allowed = package.selection_rules.get(cat)
            if allowed is not None and count > int(allowed):
                # Rollback draft if validation fails
                db.delete(booking)
                db.commit()
                return RedirectResponse(url=f"{redirect_base}?booking_error=You+selected+too+many+items+in+{cat}", status_code=303)

    all_items = selected_items + selected_addons
    for item_id in all_items:
        menu_item = db.query(models.MenuItem).get(item_id)
        if menu_item:
            booking_item = models.BookingMenuItem(
                booking_id=booking.id,
                menu_item_id=item_id,
                is_add_on=menu_item.is_addon,
                price=menu_item.addon_price if menu_item.is_addon else 0.0
            )
            db.add(booking_item)
    
    db.commit()

    # Update session
    request.session["booking_data"] = {
        "booking_id": booking.id,
        "caterer_id": caterer_id,
        "package_id": package_id
    }

    # Check if we should skip KYC for verified users OR those with booking history
    has_history = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        models.Booking.id != booking.id,
        models.Booking.status.notin_(['draft', 'cancelled', 'pending_quotation'])
    ).first() is not None

    if user.is_verified or user.is_kyc_complete or has_history:
        # Mark as verified immediately if they have history or are already verified
        booking.ocr_verified = True
        booking.liveness_verified = True
        db.commit()
        return RedirectResponse(url=f"/bookings/step/quotation/{booking.id}", status_code=303)
        
    return RedirectResponse(url=f"/bookings/step/kyc/{booking.id}", status_code=303)

# Phase 2: Identity Verification
@router.get("/step/kyc/{booking_id}", response_class=HTMLResponse)
async def step_kyc_page(booking_id: int, request: Request, db: Session = Depends(database.get_db)):
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/bookings/step/kyc/{booking_id}")
        
    booking = db.query(models.Booking).get(booking_id)
    if not booking: raise HTTPException(status_code=404)
    return templates.TemplateResponse("customer/booking_wizard/step_kyc.html", {
        "request": request,
        "booking_id": booking_id,
        "user": user,
        "current_step": 2,
        "active_page": "bookings"
    })

# Phase 3: Quotation Review & Contract
@router.get("/step/quotation/{booking_id}", response_class=HTMLResponse)
async def step_quotation_page(booking_id: int, request: Request, db: Session = Depends(database.get_db)):
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/bookings/step/quotation/{booking_id}")
        
    booking = db.query(models.Booking).get(booking_id)
    if not booking: raise HTTPException(status_code=404)
    
    # STRICT GATE: Ensure user is verified before seeing quotation/contract
    # NEW: Also allow if user has booking history
    has_history = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        models.Booking.id != booking.id,
        models.Booking.status.notin_(['draft', 'cancelled', 'pending_quotation'])
    ).first() is not None

    if not user.is_verified and not has_history:
        return RedirectResponse(url=f"/bookings/step/kyc/{booking.id}?auth_needed=1", status_code=303)

    # NEW: Transition status from draft to pending_quotation so it's visible to caterer
    if booking.status == 'draft':
        booking.status = 'pending_quotation'
        db.commit()
    
    # Ensure quotation exists or create one (default 30% downpayment)
    from ..services.quotation import quotation_service
    quotation = quotation_service.get_quotation_by_booking(db, booking_id)
    if not quotation:
        quotation = quotation_service.create_quotation(db, booking, 30)
    
    return templates.TemplateResponse("customer/booking_wizard/step_quotation.html", {
        "request": request,
        "quotation": quotation,
        "booking": booking,
        "package": booking.package,
        "user": user,
        "current_step": 3,
        "active_page": "bookings"
    })

# Phase 4: Downpayment
async def _validate_receipt_with_gemini(filepath: str, payment_method: str, expected_amount: float = 0.0) -> bool:
    is_valid = False
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        import httpx, base64, json, re
        try:
            with open(filepath, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={gemini_key}"
            prompt = (
                f"Analyze this image. Is it a legitimate payment receipt or screenshot for {payment_method}? "
                "Look for evidence of a successful transaction, reference numbers, amounts, and dates. "
                f"CRITICAL: Check if the amount paid is at least {expected_amount:,.2f} PHP. If the amount is significantly lower or missing, mark as invalid. "
                "Respond ONLY with a valid JSON object in this exact format: "
                '{"is_valid": true_or_false, "reason": "short explanation"}'
            )
            
            payload = {
                "contents": [{"parts": [{"text": prompt}, {"inlineData": {"mimeType": "image/jpeg", "data": encoded_string}}]}],
                "generationConfig": {"response_mime_type": "application/json"}
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=20.0)
                if response.status_code == 200:
                    text = response.json()['candidates'][0]['content']['parts'][0]['text']
                    match = re.search(r'\{.*\}', text.strip(), re.DOTALL)
                    if match:
                        parsed = json.loads(match.group(0))
                        is_valid = parsed.get("is_valid", False)
                        print(f"[GEMINI VALIDATION] Result: {is_valid}, Reason: {parsed.get('reason')}")
                else:
                    print(f"[GEMINI API ERROR] Status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[GEMINI OCR ERROR] {e}")
            pass # fallback to False if API fails
    else:
        # Fallback to Tesseract if no Gemini key is set
        if PYTESSERACT_AVAILABLE:
            try:
                if os.name == "nt":
                    tess_paths = [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]
                    for p in tess_paths:
                        if os.path.exists(p):
                            pytesseract.pytesseract.tesseract_cmd = p
                            break
                img = Image.open(filepath)
                img.thumbnail((800, 800))
                text = pytesseract.image_to_string(img).lower()
                keywords = ['ref', 'reference', 'no.', 'php', 'amount', 'transfer', 'gcash', 'maya', 'sent', 'success', 'date', 'pesos', 'payout']
                match_count = sum(1 for kw in keywords if kw in text)
                if match_count >= 2:
                    is_valid = True
            except Exception as e:
                pass
    return is_valid

@router.get("/step/payment/{booking_id}", response_class=HTMLResponse)
async def step_payment_v2_page(booking_id: int, request: Request, db: Session = Depends(database.get_db)):
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/bookings/step/payment/{booking_id}")
        
    # STRICT GATE: Ensure user is verified before payment
    # NEW: Also allow if user has booking history
    has_history = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        models.Booking.id != booking_id,
        models.Booking.status.notin_(['draft', 'cancelled', 'pending_quotation'])
    ).first() is not None

    if not user.is_verified and not has_history:
        return RedirectResponse(url=f"/bookings/step/kyc/{booking_id}?auth_needed=1", status_code=303)

    booking = db.query(models.Booking).get(booking_id)
    if not booking: raise HTTPException(status_code=404)

    # Get signed quotation to enforce contractual amounts
    from ..services.quotation import quotation_service
    quotation = quotation_service.get_quotation_by_booking(db, booking_id)

    # STRICT GATE: Ensure both parties have signed before allowing payment
    if not quotation or quotation.status != 'signed':
        return RedirectResponse(url=f"/bookings/step/quotation/{booking_id}?error_msg=Both+parties+must+sign+the+contract+before+proceeding+to+payment", status_code=303)

    return templates.TemplateResponse("customer/booking_wizard/step_payment.html", {
        "request": request,
        "booking_id": booking_id,
        "booking": booking,
        "quotation": quotation,
        "profile": booking.caterer,
        "user": user,
        "current_step": 4,
        "active_page": "bookings",
        "is_balance": request.query_params.get("balance") == "true"
    })

@router.post("/step/payment/{path_booking_id}")
@router.post("/step/payment")
async def step_payment_submit(
    request: Request,
    path_booking_id: Optional[int] = None,
    booking_id: Optional[int] = Form(None),
    payment_method: str = Form("GCash"),
    payment_plan: str = Form("downpayment"),
    payment_proof: Optional[UploadFile] = File(None),
    reference_no: Optional[str] = Form(None),
    db: Session = Depends(database.get_db)
):
    import re
    
    actual_booking_id = path_booking_id or booking_id
    
    if not actual_booking_id:
        session_data = request.session.get("booking_data", {})
        actual_booking_id = session_data.get("id")
        
    if not actual_booking_id:
        raise HTTPException(status_code=400, detail="Booking ID is missing from request")

    booking = db.query(models.Booking).get(actual_booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # STRICT GATE: Ensure both parties have signed before processing payment
    if not booking.quotation or booking.quotation.status != 'signed':
        return RedirectResponse(url=f"/bookings/step/quotation/{actual_booking_id}?error_msg=Both+parties+must+sign+the+contract+before+proceeding+to+payment", status_code=303)

    # Save payment plan
    booking.payment_plan = payment_plan

    user = get_current_user_from_session(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Validation: Reference Number
    if reference_no:
        reference_no = reference_no.strip()
        if not re.match(r"^[a-zA-Z0-9]+$", reference_no):
            raise HTTPException(status_code=400, detail="Reference number must be alphanumeric.")
        if len(reference_no) < 6 or len(reference_no) > 30:
            raise HTTPException(status_code=400, detail="Reference number must be between 6 and 30 characters.")
        if re.search(r"(.)\1{5,}", reference_no):
            raise HTTPException(status_code=400, detail="Reference number looks invalid (excessive repeating characters).")
            
        # Check if reference number was already used
        existing_ref = db.query(models.Booking).filter(
            models.Booking.special_requests.like(f"%[Payment Ref: {reference_no}]%"),
            models.Booking.id != booking_id
        ).first()
        if existing_ref:
            request.session["flash_error"] = "This Reference Number has already been used in another transaction."
            return RedirectResponse(url=f"/bookings/step/payment/{booking.id}?error=duplicate_ref", status_code=303)

    # Handle Payment Proof Upload
    proof_url = None
    if payment_proof and payment_proof.filename:
        # Validate MIME type
        allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp", "application/pdf"]
        if payment_proof.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type. Only JPG, PNG, WEBP, and PDF are allowed.")
            
        # File size check
        payment_proof.file.seek(0, os.SEEK_END)
        file_size = payment_proof.file.tell()
        payment_proof.file.seek(0)
        
        if file_size > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB.")
            
        ext = os.path.splitext(payment_proof.filename)[1]
        filename = f"{booking.id}_{payment_plan}_{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(PROOF_UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(payment_proof.file, buffer)
            
        # --- AI RECEIPT VALIDATION (GEMINI / OCR) ---
        expected_fee = float(booking.total_amount or 0) - float(booking.reservation_fee or 0) if payment_plan == 'balance' else float(booking.reservation_fee or 0)
        is_valid_receipt = await _validate_receipt_with_gemini(filepath, payment_method, expected_amount=expected_fee)

        if not is_valid_receipt:
            if os.path.exists(filepath):
                os.remove(filepath)
            # Encode URL manually for redirect since we can't use complex URL building easily
            request.session["flash_error"] = "Invalid Receipt Detected: Our AI could not verify the Reference Number or Amount. Please ensure the screenshot is clear."
            return RedirectResponse(url=f"/bookings/step/payment/{booking.id}?error=invalid_receipt&method={payment_method}", status_code=303)
            
        proof_url = f"/static/uploads/payment_proofs/{filename}"
        
        if payment_plan == 'balance':
            booking.balance_proof_url = proof_url
        else:
            booking.payment_proof_url = proof_url
        
        if reference_no:
            booking.special_requests = (booking.special_requests or "") + f"\n[Payment Ref: {reference_no}]"

    if not proof_url:
        request.session["flash_error"] = "Payment proof is required for online booking."
        return RedirectResponse(url=f"/bookings/step/payment/{booking.id}?error=missing_proof", status_code=303)

    booking.payment_method = payment_method
    
    if payment_plan == 'balance':
        booking.payment_status = "balance_proof_submitted"
        history = models.BookingHistory(
            booking_id=booking.id,
            status=booking.status,
            notes=f"Balance proof submitted via {payment_method}. Awaiting caterer verification."
        )
        db.add(history)
        db.commit()
        if proof_url:
            await NotificationService.notify_payment_received(db, booking, expected_fee, "Balance Proof")
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}", status_code=303)
    else:
        booking.payment_status = "proof_submitted"
        booking.status = "pending"
        history = models.BookingHistory(
            booking_id=booking.id,
            status="pending",
            notes=f"Downpayment proof submitted via {payment_method}. Awaiting caterer verification."
        )
        db.add(history)
        db.commit()
        await NotificationService.notify_new_booking(db, booking)
        if proof_url:
            await NotificationService.notify_payment_received(db, booking, expected_fee, "Downpayment Proof")
        return RedirectResponse(url=f"/bookings/success/{booking.id}", status_code=303)


@router.post("/reupload-proof/{booking_id}")
async def reupload_proof_submit(
    booking_id: int,
    request: Request,
    payment_method: str = Form("Paymongo"),
    payment_proof: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):
    user = get_current_user_from_session(request, db)
    if not user: raise HTTPException(status_code=401)
    
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.user_id != user.id:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    if booking.payment_status not in ['reupload_requested']:
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?error_msg=No+re-upload+requested", status_code=303)

    if not payment_proof or not payment_proof.filename:
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?validation_error=Please+provide+an+image&open_reupload=1", status_code=303)

    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if payment_proof.content_type not in allowed_types:
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?validation_error=Invalid+file+type&open_reupload=1", status_code=303)

    ext = os.path.splitext(payment_proof.filename)[1]
    filename = f"{booking.id}_reupload_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(PROOF_UPLOAD_DIR, filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(payment_proof.file, buffer)
        
    # --- AI RECEIPT VALIDATION (GEMINI / OCR) ---
    expected_fee = float(booking.reservation_fee or 0)
    is_valid_receipt = await _validate_receipt_with_gemini(filepath, payment_method, expected_amount=expected_fee)

    if not is_valid_receipt:
        # Delete the invalid file
        if os.path.exists(filepath):
            os.remove(filepath)
            
        import urllib.parse
        encoded_method = urllib.parse.quote(payment_method)
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?validation_error=Invalid+Receipt+Detected:+Our+AI+could+not+verify+the+Reference+Number+or+Amount.+Please+ensure+the+screenshot+is+clear.&method={encoded_method}&open_reupload=1", status_code=303)

    booking.payment_proof_url = f"/static/uploads/payment_proofs/{filename}"
    booking.payment_method = payment_method
    booking.payment_status = "proof_submitted"

    history = models.BookingHistory(
        booking_id=booking.id,
        status="pending",
        notes=f"New downpayment proof submitted via {payment_method}."
    )
    db.add(history)
    
    await NotificationService.notify_payment_received(db, booking, float(booking.reservation_fee or 0), "New Downpayment Proof")

    db.commit()
    return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?success_msg=New+proof+submitted!+Please+wait+for+verification.", status_code=303)


@router.post("/pay-balance/{booking_id}")
async def pay_balance_submit(
    booking_id: int,
    request: Request,
    payment_method: str = Form("Paymongo"),
    payment_proof: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db)
):
    user = get_current_user_from_session(request, db)
    if not user: raise HTTPException(status_code=401)
    
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.user_id != user.id:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    if booking.status in ['completed', 'cancelled', 'draft']:
        raise HTTPException(status_code=400, detail=f"Booking status '{booking.status}' does not allow balance payments.")

    outstanding_balance = float(booking.total_amount or 0) - float(booking.reservation_fee or 0)
    
    if outstanding_balance <= 0:
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?info=balance_zero", status_code=303)

    # Handle Payment Proof Upload (Prioritized for Direct Payout Flow)
    proof_url = None
    if payment_proof and payment_proof.filename:
        allowed_types = ["image/jpeg", "image/png", "image/webp", "application/pdf"]
        if payment_proof.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type.")
            
        ext = os.path.splitext(payment_proof.filename)[1]
        filename = f"{booking.id}_balance_{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(PROOF_UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(payment_proof.file, buffer)
            
        # --- AI RECEIPT VALIDATION ---
        is_valid_receipt = await _validate_receipt_with_gemini(filepath, payment_method, expected_amount=outstanding_balance)
        if not is_valid_receipt:
            if os.path.exists(filepath):
                os.remove(filepath)
            return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?error_msg=Invalid+Receipt+Detected.+Amount+did+not+match+or+receipt+is+illegible.", status_code=303)
            
        proof_url = f"/static/uploads/payment_proofs/{filename}"
        booking.balance_proof_url = proof_url
        booking.payment_method = payment_method
        booking.payment_status = "balance_proof_submitted"

        history = models.BookingHistory(
            booking_id=booking.id,
            status="confirmed",
            notes=f"Outstanding balance proof submitted via {payment_method}. Amount: ₱{outstanding_balance:,.2f}"
        )
        db.add(history)
        
        # --- Trigger Notification (In-App, Email, SMS) ---
        await NotificationService.notify_payment_received(db, booking, outstanding_balance, "Balance Payment Proof")

        db.commit()
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?success_msg=Balance+payment+proof+submitted!+Please+wait+for+verification.", status_code=303)


    return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?error_msg=No+file+uploaded", status_code=303)

@router.get("/success/{booking_id}", response_class=HTMLResponse)
async def booking_success_page(request: Request, booking_id: int, db: Session = Depends(database.get_db)):
    booking = db.query(models.Booking).get(booking_id)
    user = get_current_user_from_session(request, db)
    return templates.TemplateResponse("customer/booking_success.html", {
        "request": request,
        "booking": booking,
        "user": user,
        "active_page": "bookings"
    })

@router.post("/review")
async def submit_review(
    request: Request,
    booking_id: int = Form(...),
    rating: int = Form(...),
    comment: str = Form(...),
    recommend: Optional[str] = Form(None),
    ontime: Optional[str] = Form(None),
    db: Session = Depends(database.get_db)
):
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(url="/auth/login")

    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.user_id != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    if booking.status != 'completed':
        return RedirectResponse(url="/customer/dashboard?error_msg=Only+completed+bookings+can+be+reviewed.", status_code=303)

    if booking.review:
        return RedirectResponse(url="/customer/dashboard?error_msg=You+have+already+reviewed+this+booking.", status_code=303)

    new_review = models.Review(
        booking_id=booking_id,
        user_id=user.id,
        caterer_id=booking.caterer_id,
        rating=rating,
        comment=comment,
        recommend=True if recommend else False,
        was_punctual=True if ontime else False
    )
    db.add(new_review)
    
    # Update Caterer Rating
    caterer = booking.caterer
    total_reviews = caterer.review_count + 1
    new_rating = ((caterer.rating * caterer.review_count) + rating) / total_reviews
    caterer.rating = new_rating
    caterer.review_count = total_reviews
    
    # NEW: Mark booking as completed if it wasn't already (optional, usually status should be completed before review)
    # Actually, let's just commit.
    
    db.commit()
    return RedirectResponse(url="/customer/dashboard?success_msg=Your+review+has+been+submitted!+Thank+you!.", status_code=303)

@router.delete("/{booking_id}")
async def delete_or_archive_booking(
    booking_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or (booking.user_id != current_user.id and current_user.role != 'admin'):
        raise HTTPException(status_code=404, detail="Booking not found")

    # Business Logic:
    # 1. Hard Delete if Draft or Cancelled AND No Payment made
    if booking.status in ['draft', 'cancelled'] and booking.payment_status == 'pending':
        db.delete(booking)
        db.commit()
        return {"success": True, "message": "Booking deleted permanently.", "action": "deleted"}
    
    # 2. Otherwise, Archive (Soft Delete)
    booking.is_archived = True
    db.commit()
    return {"success": True, "message": "Booking moved to archive.", "action": "archived"}
