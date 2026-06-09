from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, UploadFile, File, BackgroundTasks, WebSocket, WebSocketDisconnect
from typing import Optional
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from ..core.templates import templates
from sqlalchemy import or_, and_
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
    # Filter out archived bookings
    bookings = [b for b in user.bookings if not b.customer_archived]
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


    # Elite Tier Data Additions
    reviews_count = db.query(models.Review).filter(models.Review.user_id == user.id).count()
    
    total_spent = sum(float(b.total_amount or 0) for b in bookings if b.status != 'cancelled')
    
    # Get the single most recent active booking for the Journey Tracker
    latest_booking = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        models.Booking.status.in_(['confirmed', 'preparing', 'processing', 'out_for_delivery'])
    ).order_by(models.Booking.created_at.desc()).first()

    return templates.TemplateResponse("customer/dashboard.html", {
        "request": request,
        "user": user,
        "recent_bookings": bookings[:5], # Use the raw objects for the elite table if possible, or display_bookings
        "total_bookings": total_bookings,
        "upcoming_count": upcoming_count,
        "reviews_count": reviews_count,
        "total_spent": total_spent,
        "latest_booking": latest_booking,
        "current_page": page,
        "total_pages": total_pages,
        "active_page": "overview",
        "recent_messages": conversations_list, # Map to the template's expected name
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
    # Calculate Intelligence Stats
    active_bookings = [b for b in user.bookings if not b.customer_archived]
    total_reservations = len(active_bookings)
    total_spent = sum([b.total_amount for b in active_bookings if b.status in ['confirmed', 'completed'] and b.total_amount])
    
    # Calculate Pending Obligations (remaining balance of active bookings)
    pending_obligations = 0
    for b in active_bookings:
        if b.status in ['pending', 'pending_payment', 'awaiting_payment']:
            # Total minus whatever was already paid (reservation fee)
            balance = float(b.total_amount or 0) - float(b.reservation_fee or 0)
            pending_obligations += max(0, balance)

    return templates.TemplateResponse("customer/bookings.html", {
        "request": request,
        "user": user,
        "bookings": sorted(active_bookings, key=lambda x: x.id, reverse=True),
        "stats": {
            "total_reservations": total_reservations,
            "total_spent": total_spent,
            "pending_obligations": pending_obligations
        },
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
        # Auto-fix for legacy bookings with 0 reservation fee (ONLY if not CASH/COD)
        is_cash = booking.payment_method in ["CASH", "COD"]
        
        if is_cash:
            # UNDO: If it was incorrectly set to total_amount, reset to 0
            if booking.reservation_fee != 0:
                booking.reservation_fee = 0
                if booking.status == 'pending_payment':
                    booking.status = 'confirmed'
                db.commit()
                db.refresh(booking)
        else:
            # FIX: If it was missing but should be full amount (GCASH)
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
            # Check for booking history to skip KYC step in UI
            has_history = db.query(models.Booking).filter(
                models.Booking.user_id == user.id,
                models.Booking.id != booking.id,
                models.Booking.status.notin_(['draft', 'cancelled', 'pending_quotation'])
            ).first() is not None
            current_step_idx = 2 if (user.is_kyc_complete or user.is_verified or has_history) else 1
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

@router.get("/booking/{booking_id}/invoice", response_class=HTMLResponse)
async def view_public_invoice(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: Optional[models.User] = Depends(auth.get_current_user_optional)
):
    """Public route for a customer to view their auto-generated invoice via a shareable link."""
    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
        
    # We will reuse the caterer's contract view or create a specific public invoice template
    quotation = booking.quotation
    if not quotation:
        quotation = {
            "total_amount": booking.total_amount,
            "package_details": {"name": booking.event_type},
            "addons": [],
            "terms": "Standard terms apply."
        }
        
    return templates.TemplateResponse("customer/public_invoice.html", {
        "request": request,
        "user": user,
        "booking": booking,
        "quotation": quotation
    })

@router.post("/booking/{booking_id}/upload-proof")
async def upload_public_proof_of_payment(
    booking_id: int,
    request: Request,
    proof_image: UploadFile = File(...),
    reference_no: Optional[str] = Form(None),
    payment_method: Optional[str] = Form(None),
    db: Session = Depends(database.get_db)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
        
    import os
    import shutil
    import uuid
    import re
    
    # Validation: File Type
    allowed_types = ["image/jpeg", "image/png", "image/jpg"]
    if proof_image.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPG and PNG are allowed.")
        
    # Validation: File Size (Read file to check size, then seek back to 0)
    proof_image.file.seek(0, os.SEEK_END)
    file_size = proof_image.file.tell()
    proof_image.file.seek(0)
    
    if file_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB.")
        
    # Validation: Reference Number
    if reference_no:
        reference_no = reference_no.strip()
        if not re.match(r"^[a-zA-Z0-9]+$", reference_no):
            raise HTTPException(status_code=400, detail="Reference number must be alphanumeric.")
        if len(reference_no) < 6 or len(reference_no) > 30:
            raise HTTPException(status_code=400, detail="Reference number must be between 6 and 30 characters.")
        if re.search(r"(.)\1{5,}", reference_no):
            raise HTTPException(status_code=400, detail="Reference number looks invalid (excessive repeating characters).")
    
    # Save the uploaded proof image
    UPLOAD_DIR = "app/static/uploads/payments"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    file_extension = os.path.splitext(proof_image.filename)[1]
    filename = f"proof_{booking_id}_{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(proof_image.file, buffer)
        
    booking.payment_proof_url = f"/static/uploads/payments/{filename}"
    if reference_no:
        booking.special_requests = (booking.special_requests or "") + f"\n[Payment Ref: {reference_no}]"
    if payment_method:
        booking.payment_method = payment_method
        
    booking.payment_status = 'proof_submitted'
    if booking.status in ['pending', 'draft', 'pending_payment']:
        booking.status = 'awaiting_payment' # To signify it's waiting for caterer verification
        
    db.commit()
    
    # Send notification to caterer
    from ..services.realtime import manager
    caterer_msg = f"New payment proof submitted for booking #{booking.id}"
    
    notif = models.Notification(
        user_id=booking.caterer.user_id,
        title="Payment Submitted",
        message=caterer_msg,
        type="Payment",
        link=f"/caterer/dashboard?page=bookings"
    )
    db.add(notif)
    db.commit()
    
    import asyncio
    asyncio.create_task(manager.broadcast_to_user(booking.caterer.user_id, {
        "type": "new_notification",
        "title": notif.title,
        "message": notif.message,
        "url": notif.link
    }))
    
    # Redirect back to the public invoice
    return RedirectResponse(url=f"/customer/booking/{booking_id}/invoice?success=1", status_code=303)

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
        # Prevent race condition: Block cancellation if admin is currently reviewing a payment proof
        if booking.payment_status == 'proof_submitted':
            return RedirectResponse(url=f"/customer/bookings/manage/{booking_id}?error_msg=Cannot+cancel+while+payment+is+under+review", status_code=303)
            
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
    lat: Optional[float] = None,
    lon: Optional[float] = None,
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
     .filter(models.CatererProfile.status == "Published")

    # Search filter (deep unified search across all fields)
    if q:
        search_filter = f"%{q}%"
        from sqlalchemy import or_, distinct

        # Subquery: caterer IDs matching via menu item names
        menu_match_sq = db.query(
            distinct(models.MenuItem.caterer_id)
        ).filter(
            models.MenuItem.name.ilike(search_filter),
            models.MenuItem.is_archived == False
        ).subquery()

        # Subquery: caterer IDs matching via package name or service_type
        pkg_match_sq = db.query(
            distinct(models.CateringPackage.caterer_id)
        ).filter(
            or_(
                models.CateringPackage.name.ilike(search_filter),
                models.CateringPackage.service_type.ilike(search_filter)
            ),
            models.CateringPackage.is_active == True
        ).subquery()

        query = query.filter(
            or_(
                models.CatererProfile.business_name.ilike(search_filter),
                models.CatererProfile.description.ilike(search_filter),
                models.CatererProfile.city.ilike(search_filter),
                models.CatererProfile.contact_address.ilike(search_filter),
                models.CatererProfile.coverage_area.ilike(search_filter),
                func.coalesce(func.array_to_string(models.CatererProfile.event_types, ','), '').ilike(search_filter),
                func.coalesce(func.array_to_string(models.CatererProfile.cuisine_types, ','), '').ilike(search_filter),
                models.CatererProfile.id.in_(menu_match_sq),
                models.CatererProfile.id.in_(pkg_match_sq),
            )
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
    if lat is not None and lon is not None:
        from sqlalchemy import text
        # Haversine formula in SQL
        distance_query = text("""
            (6371 * acos(
                cos(radians(:lat)) * cos(radians(latitude)) * 
                cos(radians(longitude) - radians(:lon)) + 
                sin(radians(:lat)) * sin(radians(latitude))
            ))
        """).bindparams(lat=lat, lon=lon)
        query = query.order_by(distance_query.asc())
    elif sort == "rating":
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

@router.get("/book/{caterer_id}")
async def legacy_booking_link_redirect(caterer_id: int):
    """Redirects old /customer/book/{id} links sent in FB Messenger to the new /bookings/start/{id} route."""
    return RedirectResponse(url=f"/bookings/start/{caterer_id}", status_code=301)

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
    
    # Unique views per account — only count once per user per caterer
    existing_view = db.query(models.ProfileView).filter(
        models.ProfileView.caterer_id == caterer_id,
        models.ProfileView.viewer_id == user.id
    ).first()
    
    if not existing_view:
        # First-time view from this account — record it and increment
        new_view = models.ProfileView(caterer_id=caterer_id, viewer_id=user.id)
        db.add(new_view)
        caterer.profile_views = (caterer.profile_views or 0) + 1
        db.commit()

    # Filter active data only
    active_packages = [p for p in caterer.packages if p.is_active]
    active_menu = [m for m in caterer.menu_items if not m.is_archived]

    # Check for previous relationship
    has_previous_bookings = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        models.Booking.caterer_id == caterer.id,
        models.Booking.status != 'cancelled'
    ).first() is not None

    # Check for previous communication
    has_previous_communication = db.query(models.ChatMessage).filter(
        or_(
            and_(models.ChatMessage.sender_id == user.id, models.ChatMessage.receiver_id == caterer.user_id),
            and_(models.ChatMessage.sender_id == caterer.user_id, models.ChatMessage.receiver_id == user.id)
        )
    ).first() is not None

    # Guard: check if caterer can accept new bookings
    caterer_unavailable = bool(
        (caterer.account_status and caterer.account_status.lower() != 'active') or 
        (caterer.status != 'Published')
    )

    return templates.TemplateResponse("customer/caterer_profile_view.html", {
        "request": request, 
        "caterer": caterer,
        "packages": active_packages,
        "active_menu": active_menu,
        "gallery_items": caterer.gallery_items,
        "reviews": caterer.reviews,
        "user": user,
        "has_previous_bookings": has_previous_bookings,
        "has_previous_communication": has_previous_communication,
        "caterer_unavailable": caterer_unavailable,
        "active_page": "marketplace",
        "nav_page": "caterers"
    })

@router.post("/profile/update")
async def update_profile(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: Optional[str] = Form(None),
    middle_name: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    import re
    if phone_number:
        # Sanitize by removing spaces or dashes
        phone_number = phone_number.replace(" ", "").replace("-", "")
        if not re.match(r"^09\d{9}$", phone_number):
            return RedirectResponse(url="/customer/profile?error_msg=Invalid+phone+number.+Must+be+11+digits+starting+with+09.", status_code=303)
            
    if email and email.strip() != user.email:
        existing_email = db.query(models.User).filter(models.User.email == email.strip()).first()
        if existing_email:
            return RedirectResponse(url="/customer/profile?error_msg=Email+address+is+already+in+use.", status_code=303)
        user.email = email.strip()
            
    user.first_name = first_name
    user.last_name = last_name
    user.middle_name = middle_name
    user.phone_number = phone_number
    user.address = address
    db.commit()
    return RedirectResponse(url="/customer/profile?success_msg=Profile+updated+successfully", status_code=303)

@router.post("/profile/deactivate")
async def deactivate_profile(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    # Check for active bookings
    active_bookings = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        ~models.Booking.status.in_(['completed', 'success', 'cancelled', 'rejected', 'draft'])
    ).count()

    if active_bookings > 0:
        return JSONResponse(
            content={"success": False, "message": "You cannot deactivate your account while you have active or pending bookings. Please settle or cancel them first."},
            status_code=400
        )

    user.status = "deactivated"
    db.commit()
    
    request.session.pop("user", None)
    return JSONResponse(content={"success": True, "message": "Account deactivated."})

@router.post("/profile/notifications")
async def update_notifications(
    request: Request,
    email_alerts: Optional[str] = Form(None),
    sms_alerts: Optional[str] = Form(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    # Currently just flashes success. 
    # To fully implement, User model needs a notification_preferences column.
    return RedirectResponse(url="/customer/profile?success_msg=Notification+preferences+saved+successfully.", status_code=303)

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
        
        if result["status"] == "pending_manual_review":
            msg = "Verification submitted for manual review! Please wait for caterer approval."
        elif result["status"] in ["approved", "verified"]:
            user.is_verified = True
            user.is_kyc_complete = True
            msg = "Verification Successful! Redirecting..."
        else:
            msg = f"Verification Failed: {result.get('failure_reason', 'Low clarity or fraud detected.')}"
            
        db.commit()
        
        # 4. Final UI Update
        await manager.broadcast_to_client(client_id, {
            "type": "verification_update",
            "status": "success" if result["status"] in ["approved", "verified", "pending_manual_review"] else "error",
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

@router.get("/api/notifications/recent")
async def get_recent_notifications(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    notifs = db.query(models.Notification).filter(
        models.Notification.user_id == user.id
    ).order_by(models.Notification.created_at.desc()).limit(5).all()
    
    results = []
    for n in notifs:
        # Safe Timezone Handling
        from datetime import datetime, timezone
        now = datetime.now(n.created_at.tzinfo) if n.created_at.tzinfo else datetime.now()
        diff = now - n.created_at
        if diff.days > 0:
            time_ago = f"{diff.days}d ago"
        elif diff.seconds > 3600:
            time_ago = f"{diff.seconds // 3600}h ago"
        else:
            time_ago = f"{max(1, diff.seconds // 60)}m ago"
            
        results.append({
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "link": n.link,
            "time_ago": time_ago
        })
    return results

@router.get("/api/messages/recent")
async def get_recent_messages(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    from sqlalchemy import or_
    # Get last 5 distinct conversations
    all_msgs = db.query(models.ChatMessage).filter(
        or_(models.ChatMessage.sender_id == user.id, models.ChatMessage.receiver_id == user.id)
    ).order_by(models.ChatMessage.created_at.desc()).all()

    results = []
    seen_peers = set()
    for msg in all_msgs:
        peer_id = msg.receiver_id if msg.sender_id == user.id else msg.sender_id
        if peer_id not in seen_peers:
            seen_peers.add(peer_id)
            peer = db.query(models.User).get(peer_id)
            if peer:
                # Time ago calculation
                from datetime import datetime, timezone
                now = datetime.now(msg.created_at.tzinfo) if msg.created_at.tzinfo else datetime.now()
                diff = now - msg.created_at
                if diff.days > 0: time_ago = f"{diff.days}d"
                elif diff.seconds > 3600: time_ago = f"{diff.seconds // 3600}h"
                else: time_ago = f"{max(1, diff.seconds // 60)}m"

                content = msg.content or ""
                if msg.message_type == 'image': content = "📷 Photo"
                elif msg.message_type == 'file': content = "📄 File"

                results.append({
                    "sender_name": peer.caterer_profile.business_name if peer.role == 'caterer' and peer.caterer_profile else f"{peer.first_name} {peer.last_name}",
                    "message": content,
                    "time_ago": time_ago,
                    "is_read": msg.is_read if msg.receiver_id == user.id else True
                })
        if len(results) >= 5: break
    return results

@router.get("/api/omni-search")
async def customer_omni_search(
    q: str,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    if not q or len(q) < 2:
        return []

    search_filter = f"%{q}%"
    results = []

    # 1. Search Caterers
    caterers = db.query(models.CatererProfile).filter(
        models.CatererProfile.status == "Published",
        models.CatererProfile.business_name.ilike(search_filter)
    ).limit(5).all()

    for c in caterers:
        results.append({
            "title": c.business_name,
            "subtitle": f"{c.city or 'Various Locations'} • {c.rating or 5.0} ⭐",
            "icon": "fas fa-utensils",
            "link": f"/customer/marketplace/{c.id}",
            "type": "caterer"
        })

    # 2. Search My Bookings
    bookings = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        models.Booking.event_name.ilike(search_filter)
    ).limit(5).all()

    for b in bookings:
        results.append({
            "title": b.event_name or "Event Booking",
            "subtitle": f"ID: {b.id} • {b.status.replace('_', ' ').title()}",
            "icon": "fas fa-calendar-check",
            "link": f"/customer/bookings/manage/{b.id}",
            "type": "booking"
        })

    return results

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


@router.post("/api/bookings/{booking_id}/report")
async def report_booking(
    booking_id: int,
    request: Request,
    reason: str = Form(...),
    details: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    import uuid
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.user_id == user.id
    ).first()

    if not booking:
        return JSONResponse(status_code=404, content={"success": False, "message": "Booking not found"})

    # Check if a report already exists
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
        reported_id=booking.caterer.user_id,
        reason=reason,
        details=details,
        status="pending"
    )
    db.add(report)
    db.commit()

    return JSONResponse(content={"success": True, "message": f"Report submitted successfully. Reference ID: {reference_id}"})


@router.post("/bookings/{booking_id}/archive")
async def archive_customer_booking(
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.user_id == user.id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    if booking.status not in ['completed', 'cancelled']:
        raise HTTPException(status_code=400, detail="Only completed or cancelled bookings can be archived.")
        
    booking.customer_archived = True
    db.commit()
    return {"status": "success", "message": "Booking archived successfully."}

@router.post("/bookings/{booking_id}/delete")
async def delete_customer_booking(
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.user_id == user.id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    if not getattr(booking, 'customer_archived', False):
        raise HTTPException(status_code=400, detail="Only archived bookings can be permanently deleted.")
        
    db.delete(booking)
    db.commit()
    return {"status": "success", "message": "Booking permanently deleted."}

@router.get("/archives")
async def customer_archives(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(customer_only)
):
    archived_bookings = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        models.Booking.customer_archived == True
    ).order_by(models.Booking.updated_at.desc()).all()
    
    return templates.TemplateResponse(
        "customer/archives.html",
        {
            "request": request,
            "user": user,
            "bookings": archived_bookings,
            "active_page": "archives"
        }
    )
