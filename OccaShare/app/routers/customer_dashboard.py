from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, UploadFile, File, BackgroundTasks, WebSocket, WebSocketDisconnect
from typing import Optional
from fastapi.responses import HTMLResponse, RedirectResponse
from ..core.templates import templates
from sqlalchemy.orm import Session
from datetime import date
import os
import shutil
import uuid
import time
from ..db import database, models
from ..core import security as auth
from ..services.verification import verification_service
from ..services.realtime import manager
import asyncio

router = APIRouter(prefix="/customer", tags=["customer"])

# Standard dependency for customer access
customer_only = auth.RoleChecker(["customer"])

@router.get("/dashboard", response_class=HTMLResponse)
async def customer_dashboard(
    request: Request, 
    page: int = 1,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    bookings = user.bookings
    today = date.today()
    upcoming_count = 0
    
    # Calculate upcoming count safely
    for b in bookings:
        if b.event_date and b.status != 'cancelled':
            try:
                b_date = b.event_date.date() if hasattr(b.event_date, 'date') else b.event_date
                if b_date >= today:
                    upcoming_count += 1
            except:
                continue

    # Pagination Logic
    PER_PAGE = 5
    page = max(1, page)
    total_bookings = len(bookings)
    total_pages = (total_bookings + PER_PAGE - 1) // PER_PAGE if total_bookings > 0 else 1
    page = min(page, total_pages)
    
    start_idx = (page - 1) * PER_PAGE
    end_idx = start_idx + PER_PAGE
    paged_bookings = bookings[start_idx:end_idx]

    # Create display-friendly booking list
    display_bookings = []
    for b in paged_bookings:
        b_data = {
            "id": b.id,
            "event_name": b.event_name or "Event Name",
            "caterer_name": b.caterer.business_name if b.caterer else "Unknown Caterer",
            "status": b.status or "pending",
            "payment_status": b.payment_status or "pending",
            "payment_method": b.payment_method or "Method TBD",
            "has_review": b.review is not None
        }
        
        # Safe Date Formatting
        try:
            if b.event_date:
                b_data["display_date"] = b.event_date.strftime('%B %d, %Y')
            else:
                b_data["display_date"] = "Date TBD"
        except:
            b_data["display_date"] = str(b.event_date) if b.event_date else "Date TBD"
            
        # Safe Time Formatting
        try:
            if b.event_time:
                b_data["display_time"] = b.event_time.strftime('%I:%M %p')
            else:
                b_data["display_time"] = "Time TBD"
        except:
            b_data["display_time"] = str(b.event_time) if b.event_time else "Time TBD"
            
        # Safe Amount Formatting
        try:
            if b.total_amount is not None:
                amount = float(b.total_amount)
                b_data["display_amount"] = f"₱{amount:,.2f}"
            else:
                b_data["display_amount"] = "₱0.00"
        except:
            b_data["display_amount"] = f"₱{b.total_amount or '0.00'}"
            
        display_bookings.append(b_data)

    # Build conversations list for Live Messages widget
    from sqlalchemy import or_
    all_msgs = db.query(models.ChatMessage).filter(
        or_(models.ChatMessage.sender_id == user.id, models.ChatMessage.receiver_id == user.id)
    ).order_by(models.ChatMessage.created_at.desc()).all()

    conversations_dict = {}
    for msg in all_msgs:
        peer_id = msg.receiver_id if msg.sender_id == user.id else msg.sender_id
        if peer_id not in conversations_dict:
            peer = db.query(models.User).get(peer_id)
            if peer:
                c_name = (
                    peer.caterer_profile.business_name
                    if peer.role == 'caterer' and peer.caterer_profile
                    else (f"{peer.first_name or ''} {peer.last_name or ''}").strip() or peer.email
                )
                if msg.message_type == 'image':
                    text = "📷 Photo"
                elif msg.message_type == 'file':
                    text = "📄 File"
                else:
                    text = msg.content or ""
                if msg.sender_id == user.id:
                    text = "You: " + text
                conversations_dict[peer_id] = {
                    "caterer_name": c_name,
                    "last_msg_time": msg.created_at.strftime('%I:%M %p').lstrip('0'),
                    "last_msg_text": text
                }
    conversations_list = list(conversations_dict.values())[:4]


    return templates.TemplateResponse("customer/dashboard.html", {
        "request": request,
        "user": user,
        "bookings": display_bookings,
        "total_count": total_bookings,
        "upcoming_count": upcoming_count,
        "current_page": page,
        "total_pages": total_pages,
        "active_page": "overview",
        "conversations": conversations_list,
        "client_id": f"dashboard_{user.id}"
    })

@router.get("/feedback/{booking_id}", response_class=HTMLResponse)
async def feedback_page(
    request: Request,
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.user_id != user.id:
        return RedirectResponse(url="/customer/dashboard?error_msg=Booking+not+found", status_code=303)
    
    if booking.status != 'completed':
        return RedirectResponse(url="/customer/dashboard?error_msg=Booking+is+not+completed", status_code=303)
        
    if booking.review:
        return RedirectResponse(url="/customer/dashboard?error_msg=Booking+already+reviewed", status_code=303)

    return templates.TemplateResponse("customer/feedback.html", {
        "request": request,
        "user": user,
        "booking": booking
    })

@router.post("/platform-feedback")
async def submit_platform_feedback(
    rating: int = Form(...),
    comment: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    # Prevent duplicate submissions
    existing_fb = db.query(models.PlatformFeedback).filter_by(user_id=user.id).first()
    if existing_fb:
        error_msg = "You have already submitted feedback. Thank you!"
        return RedirectResponse(url=f"/customer/dashboard?error_msg={error_msg}", status_code=303)

    if rating < 1 or rating > 5:
        return RedirectResponse(url="/customer/dashboard?error_msg=Invalid+rating", status_code=303)
    if not comment or len(comment.strip()) < 10:
        return RedirectResponse(url="/customer/dashboard?error_msg=Feedback+too+short", status_code=303)

    fb = models.PlatformFeedback(
        user_id=user.id,
        rating=rating,
        comment=comment.strip(),
        role="customer"
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)

    # Broadcast real-time update to all connected admins
    from ..services.realtime import manager
    await manager.broadcast_to_role("admin", {
        "type": "new_platform_feedback",
        "id": fb.id,
        "rating": fb.rating,
        "comment": fb.comment,
        "role": "customer",
        "user_name": f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
        "user_email": user.email,
        "created_at": fb.created_at.strftime('%b %d, %Y') if fb.created_at else 'Just now'
    })

    return RedirectResponse(url="/customer/dashboard?success_msg=Thank+you+for+your+feedback!", status_code=303)

@router.get("/bookings", response_class=HTMLResponse)
async def customer_bookings(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    return templates.TemplateResponse("customer/bookings.html", {
        "request": request,
        "user": user,
        "bookings": user.bookings,
        "active_page": "bookings"
    })

@router.get("/bookings/manage/{booking_id}", response_class=HTMLResponse)
async def manage_booking(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.user_id != user.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Calculate status progress for timeline
    current_status = (booking.status or "pending").lower()
    is_food_order = booking.package_id is None
    
    if is_food_order:
        # Auto-fix for legacy bookings with 0 reservation fee
        if (booking.reservation_fee is None or booking.reservation_fee == 0) and (booking.total_amount and booking.total_amount > 0):
            booking.reservation_fee = booking.total_amount
            db.commit()
            db.refresh(booking)

        # 8-Step Food Order Flow
        if current_status in ["pending", "pending_quotation", "awaiting_caterer", "draft"]:
            current_step_idx = 1 # Pending
        elif current_status in ["confirmed", "pending_payment", "awaiting_payment", "deposit_paid"]:
            current_step_idx = 2 # Confirmed
        elif current_status == "preparing":
            current_step_idx = 3 # Preparing Food
        elif current_status == "ready_for_delivery":
            current_step_idx = 4 # Ready for Delivery
        elif current_status == "on_the_way":
            current_step_idx = 5 # Out for Delivery
        elif current_status == "arrived":
            current_step_idx = 6 # Arrived
        elif current_status in ["setup_ongoing", "in_progress"]:
            current_step_idx = 7 # Setup Ongoing
        elif current_status in ["completed", "paid"]:
            current_step_idx = 8 # Completed
        else:
            current_step_idx = 1
    else:
        # Standard 6-Step Package Flow
        if current_status == "draft":
            current_step_idx = 2 if user.is_kyc_complete else 1
        elif current_status in ["pending", "pending_quotation", "awaiting_caterer"]:
            current_step_idx = 3 # Quotation phase
        elif current_status in ["pending_payment", "awaiting_payment", "confirmed"]:
            # If confirmed but not even a deposit is paid, they are in Payment phase (Step 4)
            if booking.payment_status in ["pending", "proof_submitted", "reupload_requested"]:
                current_step_idx = 4
            else:
                # If deposit_paid or paid, they move to Prep (Step 5)
                current_step_idx = 5
        elif current_status in ["confirmed", "preparing", "ready_for_delivery", "on_the_way", "arrived", "setup_ongoing", "in_progress"]:
            current_step_idx = 5 # Prep & Service phase
        elif current_status in ["completed", "paid"]:
            current_step_idx = 6 # Done phase (Can still have balance payment in UI)
        else:
            current_step_idx = 1 # Fallback
        
    # Decide which template to use
    template_name = "customer/booking_manage_alacarte.html" if is_food_order else "customer/booking_manage_package.html"

    from datetime import date as date_cls, datetime as datetime_cls
    return templates.TemplateResponse(template_name, {
        "request": request,
        "user": user,
        "booking": booking,
        "is_food_order": is_food_order,
        "current_step_idx": current_step_idx,
        "active_page": "bookings",
        "today": date_cls.today(),
        "now": datetime_cls.now()
    })

@router.get("/bookings/{booking_id}/contract", response_class=HTMLResponse)
async def view_contract_customer(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.user_id != user.id:
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

@router.post("/bookings/manage/{booking_id}/cancel")
async def cancel_booking(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.user_id != user.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Only allow cancelling drafts or unpaid pending bookings
    if booking.status in ['draft', 'pending', 'pending_payment'] and booking.payment_status not in ['paid', 'deposit_paid']:
        if booking.status == 'draft':
            # Physical delete for drafts to prevent database bloat
            db.delete(booking)
            db.commit()
            return RedirectResponse(url="/customer/bookings?success_msg=Draft+deleted+successfully", status_code=303)
        else:
            # Soft cancel for submitted but unpaid bookings
            booking.status = 'cancelled'
            db.commit()
            return RedirectResponse(url=f"/customer/bookings/manage/{booking_id}?success_msg=Booking+cancelled+successfully", status_code=303)
    else:
        return RedirectResponse(url=f"/customer/bookings/manage/{booking_id}?error_msg=Booking+cannot+be+cancelled", status_code=303)

@router.get("/payments", response_class=HTMLResponse)
async def customer_payments(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    bookings = user.bookings
    return templates.TemplateResponse("customer/payments.html", {
        "request": request,
        "user": user,
        "bookings": bookings,
        "active_page": "payments"
    })

@router.get("/reviews", response_class=HTMLResponse)
async def customer_reviews(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    return templates.TemplateResponse("customer/reviews.html", {
        "request": request,
        "user": user,
        "reviews": user.reviews,
        "active_page": "reviews"
    })

@router.get("/messages", response_class=HTMLResponse)
async def customer_messages(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    """Render the chat messaging interface for the customer."""
    return templates.TemplateResponse("customer/messages.html", {
        "request": request,
        "user": user,
        "active_page": "messages"
    })

@router.get("/profile", response_class=HTMLResponse)
async def customer_profile(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    return templates.TemplateResponse("customer/profile.html", {
        "request": request,
        "user": user,
        "active_page": "profile"
    })

@router.post("/profile/change-password")
async def customer_change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    import re
    if new_password != confirm_password:
        return {"success": False, "message": "New passwords do not match."}
    
    if len(new_password) < 8:
        return {"success": False, "message": "Password must be at least 8 characters long."}
        
    if not re.search(r"[A-Z]", new_password):
        return {"success": False, "message": "Password must contain at least one uppercase letter."}

    if not re.search(r"[a-z]", new_password):
        return {"success": False, "message": "Password must contain at least one lowercase letter."}

    if not re.search(r"[0-9]", new_password):
        return {"success": False, "message": "Password must contain at least one number."}

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_password):
        return {"success": False, "message": "Password must contain at least one special character."}
        
    if not auth.verify_password(current_password, user.password_hash):
        return {"success": False, "message": "Current password is incorrect."}
    
    # Update password
    user.password_hash = auth.get_password_hash(new_password)
    user.must_change_password = False
    db.commit()
    
    return {"success": True, "message": "Password updated successfully."}

@router.get("/promotions", response_class=HTMLResponse)
async def customer_promotions(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    promotions = db.query(models.Promotion).filter(
        models.Promotion.is_active == True,
        models.Promotion.end_date >= date.today()
    ).all()
    
    return templates.TemplateResponse("customer/promotions.html", {
        "request": request,
        "user": user,
        "promotions": promotions,
        "active_page": "promotions"
    })

@router.get("/notifications", response_class=HTMLResponse)
async def customer_notifications(
    request: Request, 
    page: int = 1,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
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
    
    return templates.TemplateResponse("customer/notifications.html", {
        "request": request,
        "user": user,
        "notifications": notifications,
        "active_page": "notifications",
        "current_page": page,
        "total_pages": total_pages,
        "total_notifications": total_notifications
    })

@router.get("/marketplace", response_class=HTMLResponse)
async def customer_marketplace(
    request: Request,
    q: Optional[str] = None,
    event_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    rating: Optional[float] = None,
    city: Optional[str] = None,
    sort: Optional[str] = "newest",
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    from sqlalchemy import func

    # Subquery to get minimum price and maximum capacity per caterer
    stats_subquery = db.query(
        models.CateringPackage.caterer_id,
        func.min(models.CateringPackage.price).label("min_price"),
        func.max(models.CateringPackage.max_guests).label("max_capacity")
    ).group_by(models.CateringPackage.caterer_id).subquery()

    # Base query for verified caterers
    query = db.query(
        models.CatererProfile,
        stats_subquery.c.min_price,
        stats_subquery.c.max_capacity
    ).outerjoin(stats_subquery, models.CatererProfile.id == stats_subquery.c.caterer_id)\
     .filter(models.CatererProfile.verification_status == "Verified")

    # Search filter
    if q:
        search_filter = f"%{q}%"
        query = query.filter(
            (models.CatererProfile.business_name.ilike(search_filter)) |
            (models.CatererProfile.description.ilike(search_filter)) |
            (models.CatererProfile.city.ilike(search_filter))
        )
    
    # Category filter
    if event_type:
        query = query.filter(models.CatererProfile.business_type == event_type)
    
    # Rating filter
    if rating:
        query = query.filter(models.CatererProfile.rating >= rating)
    
    # City filter
    if city:
        query = query.filter(models.CatererProfile.city == city)

    # Price range filter (on the calculated min_price)
    if min_price is not None:
        query = query.filter(stats_subquery.c.min_price >= min_price)
    if max_price is not None:
        query = query.filter(stats_subquery.c.min_price <= max_price)

    # Sorting
    if sort == "rating":
        query = query.order_by(models.CatererProfile.rating.desc())
    elif sort == "price_low":
        query = query.order_by(stats_subquery.c.min_price.asc())
    elif sort == "price_high":
        query = query.order_by(stats_subquery.c.min_price.desc())
    else:
        query = query.order_by(models.CatererProfile.created_at.desc())

    # Execute
    results = query.all()
    
    # Map results to objects with computed attributes for the template
    caterers = []
    for profile, min_p, max_c in results:
        profile.min_package_price = min_p or profile.starting_price or 0
        profile.max_capacity = max_c or 0
        caterers.append(profile)

    # Dynamic filter options
    cities = db.query(models.CatererProfile.city).filter(models.CatererProfile.city != None).distinct().all()
    types = db.query(models.CatererProfile.business_type).filter(models.CatererProfile.business_type != None).distinct().all()

    # Check for AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return templates.TemplateResponse("customer/marketplace_partial.html", {
            "request": request,
            "caterers": caterers
        })

    return templates.TemplateResponse("customer/marketplace.html", {
        "request": request,
        "user": user,
        "caterers": caterers,
        "cities": sorted([c[0] for c in cities]),
        "types": sorted([t[0] for t in types]),
        "active_page": "marketplace",
        "filters": {
            "q": q or "",
            "event_type": event_type or "",
            "min_price": min_price,
            "max_price": max_price,
            "rating": rating or 0,
            "city": city or "",
            "sort": sort
        }
    })

@router.get("/marketplace/{caterer_id}", response_class=HTMLResponse)
async def caterer_detail(
    caterer_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    from ..db import crud
    caterer = crud.get_caterer(db, caterer_id=caterer_id)
    if not caterer:
        raise HTTPException(status_code=404, detail="Caterer not found")
    
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

@router.post("/profile/update")
async def update_profile(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone_number: Optional[str] = Form(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    user.first_name = first_name
    user.last_name = last_name
    user.phone_number = phone_number
    db.commit()
    return RedirectResponse(url="/customer/profile?success_msg=Profile+updated+successfully", status_code=303)

@router.post("/profile/photo")
async def update_profile_photo(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    UPLOAD_DIR = "app/static/uploads/profiles"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    user.profile_image_url = f"/static/uploads/profiles/{filename}"
    db.commit()
    
    return RedirectResponse(url="/customer/profile?success_msg=Profile+photo+updated", status_code=303)

@router.get("/verification", response_class=HTMLResponse)
async def customer_verification(
    request: Request,
    user: models.User = Depends(customer_only)
):
    return templates.TemplateResponse("customer/verification.html", {
        "request": request,
        "user": user,
        "client_id": f"verify_{user.id}"
    })

@router.post("/verification/process")
async def process_verification(
    background_tasks: BackgroundTasks,
    client_id: str = Form(...),
    id_document: UploadFile = File(...),
    selfie: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    # Setup upload directory
    UPLOAD_DIR = "app/static/uploads/verification"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Save ID Document
    id_ext = os.path.splitext(id_document.filename)[1]
    id_filename = f"user_{user.id}_id_{uuid.uuid4()}{id_ext}"
    id_path = os.path.join(UPLOAD_DIR, id_filename)
    with open(id_path, "wb") as buffer:
        shutil.copyfileobj(id_document.file, buffer)
        
    # Save Selfie
    selfie_ext = os.path.splitext(selfie.filename)[1]
    selfie_filename = f"user_{user.id}_selfie_{uuid.uuid4()}{selfie_ext}"
    selfie_path = os.path.join(UPLOAD_DIR, selfie_filename)
    with open(selfie_path, "wb") as buffer:
        shutil.copyfileobj(selfie.file, buffer)
        
    # Create Verification Record
    kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == user.id).first()
    if not kyc_record:
        kyc_record = models.IdentityVerification(user_id=user.id)
        db.add(kyc_record)
    
    kyc_record.document_url = f"/static/uploads/verification/{id_filename}"
    kyc_record.selfie_url = f"/static/uploads/verification/{selfie_filename}"
    kyc_record.verification_status = "processing"
    db.commit()
    
    # Run verification in background
    background_tasks.add_task(
        run_customer_verification_bg,
        user.id,
        client_id,
        id_path,
        [selfie_path]
    )
    
    return RedirectResponse(url="/customer/dashboard?success_msg=Verification+started.+Please+wait.", status_code=303)

async def run_customer_verification_bg(user_id: int, client_id: str, id_path: str, selfie_paths: list):
    """Background task for proof of concept identity verification."""
    db = next(database.get_db())
    try:
        user = db.query(models.User).get(user_id)
        
        # 1. Update UI via WS
        await manager.broadcast_to_client(client_id, {
            "type": "verification_update",
            "status": "processing",
            "message": "Analyzing document clarity..."
        })
        await asyncio.sleep(2)
        
        # 2. OCR and Matching
        await manager.broadcast_to_client(client_id, {
            "type": "verification_update",
            "status": "processing",
            "message": "Matching face with ID photo..."
        })
        await asyncio.sleep(2)
        
        # Call verification service
        result = verification_service.verify_identity_v2(
            id_path, 
            selfie_paths, 
            f"{user.first_name} {user.last_name}", 
            "MOCK-ID-123", 
            "Passport"
        )
        
        # 3. Update DB
        kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == user_id).first()
        kyc_record.verification_status = result["status"]
        kyc_record.fraud_score = result["fraud_score"]
        
        if result["status"] == "approved":
            user.is_verified = True
            user.is_kyc_complete = True
            msg = "Verification Successful! Redirecting..."
        else:
            msg = "Verification Failed: Low clarity or fraud detected."
            
        db.commit()
        
        # 4. Final UI Update
        await manager.broadcast_to_client(client_id, {
            "type": "verification_update",
            "status": "success" if result["status"] == "approved" else "error",
            "message": msg
        })
        
    except Exception as e:
        print(f"Error in background verification: {e}")
        await manager.broadcast_to_client(client_id, {
            "type": "verification_update",
            "status": "error",
            "message": "A technical error occurred during verification."
        })
    finally:
        db.close()

@router.websocket("/verification/ws/{client_id}")
async def verification_ws(
    websocket: WebSocket, 
    client_id: str,
    db: Session = Depends(database.get_db)
):
    # We attempt to get user from session/cookies
    user = auth.get_current_user_from_session_ws(websocket, db)
    user_id = user.id if user else None
    
    await manager.connect(client_id, websocket, user_id=user_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(client_id)

