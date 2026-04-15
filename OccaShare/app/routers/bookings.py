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
from ..services.realtime import manager
from ..services.notification import NotificationService


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

@router.get("/my")
async def my_bookings_redirect():
    return RedirectResponse(url="/customer/bookings", status_code=303)

# --- Wizard Steps ---

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
        return RedirectResponse(url="/customer/dashboard?error=booking_not_found", status_code=303)
        
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
    if not user.is_verified and not user.is_kyc_complete:
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

# New: Package Selection Step (If not selected from Marketplace)
@router.get("/step/menu/{caterer_id}", response_class=HTMLResponse)
async def step_menu_page(caterer_id: int, request: Request, db: Session = Depends(database.get_db)):
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer: raise HTTPException(status_code=404)
    
    packages = db.query(models.CateringPackage).filter(models.CateringPackage.caterer_id == caterer_id).all()
    user = get_current_user_from_session(request, db)
    
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
    
    addon_items = db.query(models.MenuItem).filter(
        models.MenuItem.caterer_id == caterer.id,
        models.MenuItem.is_addon == True
    ).all()

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
    guest_count: int = Form(...),
    venue_address: str = Form(...),
    total_price: float = Form(...),
    reservation_fee: float = Form(...),
    selected_items: list[int] = Form([]),
    selected_addons: list[int] = Form([]),
    special_requests: Optional[str] = Form(""),
    db: Session = Depends(database.get_db)
):
    # Safely parse IDs from strings to handle empty form values
    package_id = int(package_id_str) if package_id_str and package_id_str.strip() else None
    booking_id = int(booking_id_str) if booking_id_str and booking_id_str.strip() else None
    user = get_current_user_from_session(request, db)
    if not user: return RedirectResponse(url=f"/auth/login?next=/packages/{package_id}")

    # 1. Check Availability (Only if date changed or new booking)
    # [Availability check logic remains same for now]
    availability = db.query(models.Availability).filter(
        models.Availability.caterer_id == caterer_id,
        models.Availability.date == event_date,
        models.Availability.is_available == False
    ).first()
    
    if availability:
        return RedirectResponse(url=f"/packages/{package_id}?error=date_unavailable", status_code=303)

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
        booking.venue_address = venue_address
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
            venue_address=venue_address,
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

    # 3. Save Selected Items
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

    return RedirectResponse(url=f"/bookings/step/kyc/{booking.id}", status_code=303)

# Phase 2: Identity Verification
@router.get("/step/kyc/{booking_id}", response_class=HTMLResponse)
async def step_kyc_page(booking_id: int, request: Request, db: Session = Depends(database.get_db)):
    booking = db.query(models.Booking).get(booking_id)
    if not booking: raise HTTPException(status_code=404)
    user = get_current_user_from_session(request, db)
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
    booking = db.query(models.Booking).get(booking_id)
    if not booking: raise HTTPException(status_code=404)
    
    # NEW: Transition status from draft to pending_quotation so it's visible to caterer
    if booking.status == 'draft':
        booking.status = 'pending_quotation'
        db.commit()
    
    # Ensure quotation exists or create one (default 30% downpayment)
    from ..services.quotation import quotation_service
    quotation = quotation_service.get_quotation_by_booking(db, booking_id)
    if not quotation:
        quotation = quotation_service.create_quotation(db, booking, 30)
    
    user = get_current_user_from_session(request, db)
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
@router.get("/step/payment/{booking_id}", response_class=HTMLResponse)
async def step_payment_v2_page(booking_id: int, request: Request, db: Session = Depends(database.get_db)):
    booking = db.query(models.Booking).get(booking_id)
    if not booking: raise HTTPException(status_code=404)
    user = get_current_user_from_session(request, db)
    return templates.TemplateResponse("customer/booking_wizard/step_payment.html", {
        "request": request,
        "booking_id": booking_id,
        "booking": booking,
        "profile": booking.caterer,
        "user": user,
        "current_step": 4,
        "active_page": "bookings"
    })

@router.post("/step/payment/{path_booking_id}")
@router.post("/step/payment")
async def step_payment_submit(
    request: Request,
    path_booking_id: Optional[int] = None,
    booking_id: Optional[int] = Form(None),
    payment_method: str = Form("GCash"),
    payment_proof: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db)
):
    actual_booking_id = path_booking_id or booking_id
    
    if not actual_booking_id:
        session_data = request.session.get("booking_data", {})
        actual_booking_id = session_data.get("id")
        
    if not actual_booking_id:
        raise HTTPException(status_code=400, detail="Booking ID is missing from request")

    booking = db.query(models.Booking).get(actual_booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    user = get_current_user_from_session(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Handle Payment Proof Upload
    proof_url = None
    if payment_proof and payment_proof.filename:
        # Validate MIME type
        allowed_types = ["image/jpeg", "image/png", "image/webp", "application/pdf"]
        if payment_proof.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type. Only JPG, PNG, WEBP, and PDF are allowed.")
            
        ext = os.path.splitext(payment_proof.filename)[1]
        filename = f"{booking.id}_down_{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(PROOF_UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(payment_proof.file, buffer)
            
        proof_url = f"/static/uploads/payment_proofs/{filename}"
        booking.payment_proof_url = proof_url

    # Handle Cash Payment
    if payment_method == "Cash":
        booking.payment_method = "Cash"
        # If cash, they might not have a proof yet, or it's just a promise
        booking.payment_status = "proof_submitted" if proof_url else "pending"
        booking.status = "pending"
        
        history = models.BookingHistory(
            booking_id=booking.id,
            status="pending",
            notes=f"Downpayment committed via Cash. Proof: {'Uploaded' if proof_url else 'None'}"
        )
        db.add(history)
        db.commit()
        
        # --- Trigger Notification (In-App, Email, SMS) ---
        await NotificationService.notify_new_booking(db, booking)
        if proof_url:
            await NotificationService.notify_payment_received(db, booking, float(booking.reservation_fee or 0), "Downpayment Proof")

        return RedirectResponse(url=f"/bookings/success/{booking.id}", status_code=303)

    # Paymongo Integration (Keep it if configured)
    paymongo_secret = os.getenv("PAYMONGO_SECRET_KEY")
    if paymongo_secret and not proof_url: # Only use Paymongo if no manual proof uploaded
        url = "https://api.paymongo.com/v1/links"
        amount_cents = int((booking.reservation_fee or 0) * 100)
        
        if amount_cents >= 10000:
            base_url = os.getenv("SITE_URL", "http://localhost:8000")
            payload = {
                "data": {
                    "attributes": {
                        "amount": amount_cents,
                        "description": f"Reservation Fee for Booking #{booking.id}",
                        "remarks": f"booking_id:{booking.id}",
                        "redirect": {
                            "success": f"{base_url}/bookings/my?payment=success",
                            "failed": f"{base_url}/bookings/my?payment=failed"
                        }
                    }
                }
            }
            
            async with httpx.AsyncClient() as client:
                try:
                    import httpx
                    response = await client.post(url, json=payload, auth=(paymongo_secret, ""))
                    if response.status_code == 200:
                        data = response.json()
                        checkout_url = data["data"]["attributes"]["checkout_url"]
                        booking.payment_method = payment_method
                        booking.status = "pending_payment"
                        db.commit()
                        return RedirectResponse(url=checkout_url, status_code=303)
                except Exception as e:
                    print("Paymongo Error:", str(e))

    # Default flow: Manual transfer / Direct Payment
    booking.payment_method = payment_method
    booking.payment_status = "proof_submitted" if proof_url else "pending"
    booking.status = "pending"
    
    history = models.BookingHistory(
        booking_id=booking.id,
        status="pending",
        notes=f"Downpayment proof submitted via {payment_method}. Awaiting caterer verification."
    )
    db.add(history)
    db.commit()

    # --- Trigger Notification (In-App, Email, SMS) ---
    await NotificationService.notify_new_booking(db, booking)
    if proof_url:
        await NotificationService.notify_payment_received(db, booking, float(booking.reservation_fee or 0), "Downpayment Proof")

    return RedirectResponse(url=f"/bookings/success/{booking.id}", status_code=303)


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
        
    if booking.status != 'confirmed':
        raise HTTPException(status_code=400, detail="Only confirmed bookings can have balances paid.")

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
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?success=balance_proof_submitted", status_code=303)


    return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?error=no_file", status_code=303)

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
    return RedirectResponse(url="/customer/dashboard?success=review_submitted", status_code=303)
