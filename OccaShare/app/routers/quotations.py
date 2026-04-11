from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, BackgroundTasks, Body
from sqlalchemy.orm import Session, joinedload
from ..db import database, models
from ..core import security as auth
from ..services.quotation import quotation_service
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func
from jose import jwt, JWTError
from ..db.models import BookingMenuItem
from ..core.templates import templates
from ..services.realtime import manager

router = APIRouter(prefix="/api/bookings", tags=["quotations"])

async def send_signature_notification(db_session_factory, user_id, title, message, type, link):
    """Background task to send notification without blocking the response"""
    db = db_session_factory()
    try:
        notif = models.Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            link=link
        )
        db.add(notif)
        db.commit()

        await manager.broadcast_to_user(user_id, {
            "type": "new_notification",
            "message": f"{title}: {message}",
            "count": unread_count
        })
    except Exception as e:

        print(f"Error sending background notification: {e}")
    finally:
        db.close()

def get_session_user(request: Request, db: Session):
    """Helper for session-based auth in wizard routes"""
    token = request.cookies.get("access_token")
    if not token:
        return None
    if token.startswith("Bearer "):
        token = token.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email = payload.get("sub")
        if not email:
            return None
        return db.query(models.User).filter(models.User.email == email).first()
    except Exception:
        return None

@router.post("/quote")
async def create_quote_request(
    caterer_id: int = Form(...),
    package_id: int = Form(...),
    event_date: str = Form(...),
    event_time: str = Form(...),
    guest_count: int = Form(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # check availability
    date_obj = datetime.strptime(event_date, '%Y-%m-%d').date()
    availability = db.query(models.Availability).filter(
        models.Availability.caterer_id == caterer_id,
        models.Availability.date == date_obj,
        models.Availability.is_available == False
    ).first()
    
    if availability:
        raise HTTPException(status_code=400, detail="Date is unavailable")

    package = db.query(models.CateringPackage).get(package_id)
    if not package:
         raise HTTPException(status_code=404, detail="Package not found")

    # Create pending booking (was draft, now visible to caterer)
    booking = models.Booking(
        user_id=current_user.id,
        caterer_id=caterer_id,
        package_id=package_id,
        event_date=date_obj,
        event_time=datetime.strptime(event_time, '%H:%M').time(),
        guest_count=guest_count,
        status="pending",
        total_amount=0 # will be set by quotation
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    
    return {"booking_id": booking.id}

@router.get("/{booking_id}")
async def get_booking(
    booking_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or (booking.user_id != current_user.id and current_user.role != 'admin'):
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return booking

@router.post("/{booking_id}/calculate")
async def calculate_quotation(
    booking_id: int,
    request: Request,
    guest_count: int = Form(...),
    downpayment_percent: int = Form(...),
    db: Session = Depends(database.get_db),
):
    current_user = get_session_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    package = booking.package
    
    # Calculate base amount
    actual_unit_price = package.price_per_head if hasattr(package, 'price_per_head') and package.price_per_head else package.price
    unit_price = Decimal(str(actual_unit_price))
    base_amount = unit_price * Decimal(str(guest_count))
    
    # Calculate addon total
    addon_total = db.query(func.sum(BookingMenuItem.price)).filter(
        BookingMenuItem.booking_id == booking_id,
        BookingMenuItem.is_add_on == True
    ).scalar() or 0.0
    
    total_amount = base_amount + Decimal(str(addon_total))
    deposit_amount = total_amount * (Decimal(str(downpayment_percent)) / Decimal("100"))
    
    return {
        "success": True,
        "base_amount": float(base_amount),
        "total_amount": float(total_amount),
        "deposit_amount": float(deposit_amount),
        "guest_count": guest_count,
        "downpayment_percent": downpayment_percent,
        "unit_price": float(unit_price)
    }

@router.post("/{booking_id}/quotation")
async def generate_quotation(
    booking_id: int,
    downpayment_percent: int = Form(30),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    try:
        quotation = quotation_service.create_quotation(db, booking, downpayment_percent)
        
        # NEW: Notify Customer that a quotation is ready
        notif = models.Notification(
            user_id=booking.user_id,
            title="Quotation Ready",
            message=f"The caterer has generated a new quotation for your event '{booking.event_name}'.",
            type="Booking",
            link=f"/bookings/step/quotation/{booking.id}"
        )
        db.add(notif)
        db.commit()
        
        # Real-time WebSocket Alert to Customer
        await manager.broadcast_to_user(booking.user_id, {
            "type": "new_quotation",
            "message": f"New quotation generated for '{booking.event_name}'",
            "booking_id": booking.id
        })
        
        return quotation
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{booking_id}/contract/sign")
async def sign_contract(
    booking_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    data: dict = Body(...),
    db: Session = Depends(database.get_db)
):
    signature_data = data.get("signature_data")
    if not signature_data:
        raise HTTPException(status_code=422, detail="Missing signature_data")

    current_user = get_session_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    quotation = db.query(models.Quotation).options(
        joinedload(models.Quotation.booking).joinedload(models.Booking.caterer)
    ).filter(models.Quotation.booking_id == booking_id).first()
    
    if not quotation or not quotation.booking:
        raise HTTPException(status_code=404, detail="Quotation or Booking not found")

    booking = quotation.booking
    
    # Update Downpayment Percentage
    downpayment_percent = data.get("downpayment_percent")
    if downpayment_percent is not None:
        quotation.downpayment_percent = int(downpayment_percent)
    
    # Use 30 as default if not set to avoid crash in Decimal calculation
    current_dp = quotation.downpayment_percent if quotation.downpayment_percent is not None else 30
    dp_factor = Decimal(str(current_dp)) / Decimal("100")
    
    # Sync guest count if adjusted
    guest_count = data.get("guest_count")
    if guest_count and guest_count != quotation.package_details.get("guest_count"):
        unit_price = Decimal(str(quotation.package_details.get("unit_price", 0)))
        new_guest_count = int(guest_count)
        new_base_amount = unit_price * new_guest_count
        
        addon_total = sum(Decimal(str(a.get("price", 0))) for a in (quotation.addons or []))
        new_total = new_base_amount + addon_total
        
        details = quotation.package_details.copy()
        details["guest_count"] = new_guest_count
        details["base_amount"] = float(new_base_amount)
        quotation.package_details = details
        quotation.total_amount = float(new_total)
        
        booking.guest_count = new_guest_count
        booking.total_amount = float(new_total)
        booking.reservation_fee = new_total * dp_factor
    else:
        # Use 0 as default if total_amount is somehow None to avoid crash
        base_total = quotation.total_amount if quotation.total_amount is not None else 0
        new_total = Decimal(str(base_total))
        booking.reservation_fee = new_total * dp_factor

    # Strict ID-based identity check (Safer than role-based)
    is_customer = (current_user.id == booking.user_id)
    is_caterer = (booking.caterer and booking.caterer.user_id == current_user.id)

    if is_customer:
        quotation.customer_signature = signature_data
        quotation.customer_signed_at = datetime.now()
    elif is_caterer:
        quotation.caterer_signature = signature_data
        quotation.caterer_signed_at = datetime.now()
    else:
        # Fallback to role if ID check is ambiguous (should not happen for valid bookings)
        if current_user.role == 'caterer':
            quotation.caterer_signature = signature_data
            quotation.caterer_signed_at = datetime.now()
            is_caterer = True
        else:
            quotation.customer_signature = signature_data
            quotation.customer_signed_at = datetime.now()
            is_customer = True

    # Re-evaluate status based on BOTH signatures
    has_cust = bool(quotation.customer_signature and len(str(quotation.customer_signature)) > 20)
    has_cat = bool(quotation.caterer_signature and len(str(quotation.caterer_signature)) > 20)

    if has_cust and has_cat:
        quotation.status = "signed"
        booking.status = "awaiting_payment"
        
        # Notify both parties of full completion
        background_tasks.add_task(
            send_signature_notification,
            database.SessionLocal,
            booking.user_id,
            "Contract Fully Signed",
            f"Caterer {booking.caterer.business_name} has signed. Proceed to payment.",
            "success",
            f"/bookings/step/payment/{booking.id}"
        )
        background_tasks.add_task(
            send_signature_notification,
            database.SessionLocal,
            booking.caterer.user_id,
            "Contract Fully Signed",
            f"Customer {booking.user.first_name} has signed. Awaiting payment.",
            "success",
            f"/caterer/bookings"
        )
    elif has_cust:
        quotation.status = "awaiting_caterer"
        booking.status = "awaiting_caterer"
        
        # Notify Caterer
        background_tasks.add_task(
            send_signature_notification,
            database.SessionLocal,
            booking.caterer.user_id,
            "Action Required: Sign Contract",
            f"Customer {current_user.first_name} has signed the contract.",
            "info",
            f"/caterer/bookings/{booking.id}/sign"
        )
    elif has_cat:
        quotation.status = "awaiting_customer"
        booking.status = "awaiting_customer"
        
        # Notify Customer
        background_tasks.add_task(
            send_signature_notification,
            database.SessionLocal,
            booking.user_id,
            "Action Required: Sign Contract",
            f"Caterer {booking.caterer.business_name} has signed the contract.",
            "info",
            f"/bookings/step/quotation/{booking.id}"
        )

    # Real-time Broadcasts
    if is_customer:
        # Broadcast to caterer that customer signed
        background_tasks.add_task(
            manager.broadcast_to_user,
            booking.caterer.user_id,
            {"type": "signature_update", "role": "customer", "booking_id": booking.id, "status": quotation.status}
        )
    if is_caterer:
        # Broadcast to customer that caterer signed
        background_tasks.add_task(
            manager.broadcast_to_user,
            booking.user_id,
            {"type": "signature_update", "role": "caterer", "booking_id": booking.id, "status": quotation.status}
        )
    
    db.commit()
    return {"success": True, "status": quotation.status}

@router.post("/{booking_id}/update-dp")
async def update_dp(
    booking_id: int, 
    request: Request,
    payload: dict,
    db: Session = Depends(database.get_db)
):
    current_user = get_session_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = current_user # alias for consistency with previous logic
    
    booking = db.query(models.Booking).get(booking_id)
    if not booking: raise HTTPException(status_code=404)
    if booking.user_id != user.id: raise HTTPException(status_code=403)
    
    quotation = booking.quotation
    if not quotation: raise HTTPException(status_code=404)
    
    # LOCK: Prevent changing DP if already signed
    if quotation.customer_signature:
        raise HTTPException(status_code=400, detail="Downpayment cannot be changed once the contract is signed.")
    
    percent = int(payload.get("percent", 30))
    quotation.downpayment_percent = percent
    
    from decimal import Decimal
    dp_factor = Decimal(str(percent)) / Decimal("100")
    new_deposit = Decimal(str(quotation.total_amount)) * dp_factor
    booking.reservation_fee = float(new_deposit)
    
    db.commit()
    
    return {"success": True, "new_deposit": float(new_deposit)}

@router.get("/{booking_id}/contract/content")
async def get_contract_content(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db)
):
    current_user = get_session_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    # Check if user is caterer OR the customer who made the booking
    if current_user.role == 'caterer':
        if booking.caterer_id != current_user.caterer_profile.id:
            raise HTTPException(status_code=403, detail="Unauthorized access to contract")
    elif current_user.role == 'customer':
        if booking.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized access to contract")
    else:
        raise HTTPException(status_code=403, detail="Unauthorized")

    quotation = booking.quotation
    if not quotation:
        raise HTTPException(status_code=404, detail="Contract/Quotation not found")

    return templates.TemplateResponse("shared/contract_content_partial.html", {
        "request": request,
        "booking": booking,
        "quotation": quotation,
        "user": current_user
    })

@router.post("/{booking_id}/set-due-date")
async def set_balance_due_date(
    booking_id: int, 
    request: Request,
    payload: dict,
    db: Session = Depends(database.get_db)
):
    current_user = get_session_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = current_user
    
    booking = db.query(models.Booking).get(booking_id)
    if not booking: raise HTTPException(status_code=404)
    
    # Check if user is the caterer for this booking
    if booking.caterer.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the assigned caterer can set the due date.")

    if booking.status == 'completed':
        raise HTTPException(status_code=400, detail="Cannot change due date for completed bookings.")
        
    due_date_str = payload.get("due_date")
    if not due_date_str:
        raise HTTPException(status_code=400, detail="Due date is required.")
        
    try:
        booking.balance_due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        db.commit()
        
        # Notify Customer
        notif = models.Notification(
            user_id=booking.user_id,
            title="Balance Due Date Set",
            message=f"The caterer has set the balance due date for your event '{booking.event_name}' to {due_date_str}.",
            type="info",
            link=f"/customer/bookings/manage/{booking.id}"
        )
        db.add(notif)
        db.commit()
        
        return {"status": "success", "due_date": due_date_str}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
