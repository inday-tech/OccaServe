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
from ..services.notification import NotificationService
from ..services.booking_validator import BookingValidator

router = APIRouter(prefix="/api/bookings", tags=["quotations"])


def get_caterer_payment_terms(caterer):
    raw_terms = getattr(caterer, "accepted_payment_terms", None) or [30]
    terms = set()
    for raw_term in raw_terms:
        try:
            term = int(raw_term)
        except (TypeError, ValueError):
            continue
        if 20 <= term <= 100 and term % 5 == 0:
            terms.add(term)
    return sorted(terms) or [30]


def get_quotation_payment_terms(quotation, caterer):
    saved_terms = (quotation.package_details or {}).get("accepted_payment_terms") if quotation else None
    if saved_terms:
        terms = set()
        for raw_term in saved_terms:
            try:
                term = int(raw_term)
            except (TypeError, ValueError):
                continue
            if 20 <= term <= 100 and term % 5 == 0:
                terms.add(term)
        if terms:
            return sorted(terms)
    return get_caterer_payment_terms(caterer)


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
    if current_user.role != "customer":
        raise HTTPException(status_code=403, detail="Only customers can request a quotation.")
    if guest_count < 1 or guest_count > 999:
        raise HTTPException(status_code=400, detail="Number of guests must be between 1 and 999.")
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
    if not package or package.caterer_id != caterer_id:
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

    if guest_count < 1 or guest_count > 999:
        raise HTTPException(status_code=400, detail="Number of guests must be between 1 and 999.")
    if downpayment_percent < 20 or downpayment_percent > 100 or downpayment_percent % 5:
        raise HTTPException(status_code=400, detail="Deposit percentage must be in 5% steps from 20% to 100%.")

    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    is_owner = (booking.user_id == current_user.id)
    is_caterer = bool(current_user.caterer_profile and booking.caterer_id == current_user.caterer_profile.id)
    if not is_owner and not is_caterer and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Unauthorized")
    if downpayment_percent not in get_caterer_payment_terms(booking.caterer):
        raise HTTPException(status_code=400, detail="Choose one of this caterer's accepted deposit options.")
    
    package = booking.package
    is_customizable = (package and getattr(package, 'pricing_mode', '') == 'customizable') or (booking.custom_requirements and booking.custom_requirements.get('package_type') == 'customizable') or (booking.quotation and booking.quotation.package_details and booking.quotation.package_details.get('package_type') == 'customizable')
    if is_customizable and (not is_caterer or booking.status != "inquiry"):
        raise HTTPException(status_code=409, detail="A caterer must accept the booking request before preparing a quotation.")
    
    if is_customizable:
        # CUSTOMIZABLE PACKAGE: Compute customized total directly from selections
        if booking.custom_requirements and "customization" in booking.custom_requirements:
            cust = booking.custom_requirements["customization"]
            cust["guest_count"] = guest_count
            booking.custom_requirements["customization"] = cust
        booking.guest_count = guest_count
        quotation = quotation_service.create_quotation(db, booking, downpayment_percent)
        
        return {
            "success": True,
            "package_type": "customizable",
            "base_amount": float(quotation.package_details.get("customized_total", quotation.total_amount)),
            "total_amount": float(quotation.total_amount),
            "deposit_amount": float(booking.reservation_fee),
            "guest_count": guest_count,
            "downpayment_percent": downpayment_percent,
            "unit_price": 0.0
        }
    else:
        # FIXED PACKAGE: Keep existing fixed package rate & inclusion logic
        p_mode = getattr(package, 'pricing_mode', 'per_pax') if package else 'per_pax'
        p_unit = getattr(package, 'price_unit', 'per_guest') if package else 'per_guest'
        
        actual_unit_price = (package.price_per_head if hasattr(package, 'price_per_head') and package.price_per_head else package.price) if package else 0
        unit_price = Decimal(str(actual_unit_price or 0))
        
        if p_mode == 'fixed' or p_unit != 'per_guest':
            base_amount = Decimal(str(package.price or actual_unit_price or 0))
            min_guests = getattr(package, 'min_guests', 0) or 0
            add_price = Decimal(str(getattr(package, 'additional_guest_price', 0) or 0))
            if guest_count > min_guests and add_price > 0:
                base_amount += Decimal(str(guest_count - min_guests)) * add_price
        else:
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
            "package_type": "fixed",
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

    is_assigned_caterer = bool(
        current_user.caterer_profile
        and booking.caterer_id == current_user.caterer_profile.id
    )
    if not is_assigned_caterer:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "inquiry":
        raise HTTPException(status_code=409, detail="Accept the booking request before generating a quotation.")
    if booking.is_custom_event or booking.travel_fee_status == "manual_quote":
        raise HTTPException(status_code=400, detail="Prepare custom quotations in the caterer quotation workspace.")
    if booking.quotation and booking.quotation.status != "draft":
        raise HTTPException(status_code=409, detail="A quotation has already been sent for this booking.")
    
    try:
        # Dynamic downpayment percent from caterer profile
        if booking.caterer:
            downpayment_percent = min(get_caterer_payment_terms(booking.caterer))
            
        quotation = quotation_service.create_quotation(db, booking, downpayment_percent)
        if not quotation or not quotation.total_amount or quotation.total_amount <= 0:
            if quotation and quotation.status == "draft":
                db.delete(quotation)
                db.commit()
            raise ValueError("A valid quotation could not be generated for this booking.")
        quotation.status = "draft"
        effective_downpayment_percent = int(quotation.downpayment_percent or downpayment_percent)
        booking.reservation_fee = float(quotation.total_amount or 0) * effective_downpayment_percent / 100
        db.commit()
        
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
    current_user = get_session_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    quotation = db.query(models.Quotation).options(
        joinedload(models.Quotation.booking).joinedload(models.Booking.caterer)
    ).filter(models.Quotation.booking_id == booking_id).first()
    
    if not quotation or not quotation.booking:
        raise HTTPException(status_code=404, detail="Quotation or Booking not found")

    booking = quotation.booking

    # Authorize before changing quote or booking data. The quote service may
    # commit internally when it rebuilds a customizable quotation.
    is_customer = current_user.id == booking.user_id
    is_caterer = bool(booking.caterer and booking.caterer.user_id == current_user.id)
    if not is_customer and not is_caterer:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized: you are not an authorized party to this booking contract.",
        )

    use_saved_signature = bool(data.get("use_saved_signature"))
    save_signature = bool(data.get("save_signature"))
    if is_caterer and use_saved_signature:
        signature_data = booking.caterer.saved_signature if booking.caterer else None
        if not signature_data:
            raise HTTPException(status_code=409, detail="No saved caterer signature is available.")
    else:
        signature_data = data.get("signature_data")
    if not signature_data:
        raise HTTPException(status_code=422, detail="Please provide a signature before signing.")
    if data.get("confirm_agreement") is not True:
        raise HTTPException(status_code=400, detail="Confirm that you agree to the agreement before signing.")
    if is_customer and not quotation.caterer_signature:
        raise HTTPException(status_code=409, detail="The caterer must sign and send the agreement before you can sign it.")
    if is_caterer and quotation.status != "awaiting_caterer":
        raise HTTPException(status_code=409, detail="The customer must choose and submit a deposit option before you can sign the agreement.")
    if is_customer and quotation.customer_signature:
        raise HTTPException(status_code=409, detail="You have already signed this agreement.")
    if is_caterer and quotation.caterer_signature:
        raise HTTPException(status_code=409, detail="The caterer has already signed this agreement.")

    package_details = quotation.package_details or {}
    is_customizable = (
        package_details.get("package_type") == "customizable"
        or (booking.package and getattr(booking.package, "pricing_mode", "") == "customizable")
        or (booking.custom_requirements and booking.custom_requirements.get("package_type") == "customizable")
    )
    has_prior_signature = bool(quotation.customer_signature or quotation.caterer_signature)

    # CONTINUOUS REVALIDATION: Check if booking is still valid before signing
    is_valid, error_msg = BookingValidator.validate_booking_state(db, booking, update_if_expired=True)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
        
    # Update Downpayment Percentage
    downpayment_percent = data.get("downpayment_percent")
    if downpayment_percent is not None:
        try:
            downpayment_percent = int(downpayment_percent)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid downpayment percentage.")
        if downpayment_percent < 20 or downpayment_percent > 100 or downpayment_percent % 5:
            raise HTTPException(status_code=400, detail="Downpayment must be in 5% steps from 20% to 100%.")
        if downpayment_percent not in get_quotation_payment_terms(quotation, booking.caterer):
            raise HTTPException(status_code=400, detail="Choose one of this caterer's accepted deposit options.")
        if has_prior_signature and quotation.downpayment_percent is not None and downpayment_percent != quotation.downpayment_percent:
            raise HTTPException(status_code=409, detail="The downpayment terms cannot change after either party has signed.")
        quotation.downpayment_percent = downpayment_percent
    
    # Use 30 as default if not set to avoid crash in Decimal calculation
    current_dp = quotation.downpayment_percent if quotation.downpayment_percent is not None else 30
    dp_factor = Decimal(str(current_dp)) / Decimal("100")
    
    # Sync guest count if adjusted
    guest_count = data.get("guest_count")
    if guest_count is not None:
        try:
            guest_count = int(guest_count)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Number of guests must be between 1 and 999.")
        if guest_count < 1 or guest_count > 999:
            raise HTTPException(status_code=400, detail="Number of guests must be between 1 and 999.")

    quoted_guest_count = int(package_details.get("guest_count") or booking.guest_count or 0)
    if has_prior_signature and guest_count is not None and guest_count != quoted_guest_count:
        raise HTTPException(status_code=409, detail="Guest count cannot change after either party has signed.")

    if guest_count and guest_count != package_details.get("guest_count"):
        new_guest_count = int(guest_count)
        booking.guest_count = new_guest_count
        
        if is_customizable:
            # Recompute customizable quotation with new guest count
            quotation = quotation_service.create_quotation(db, booking, quotation.downpayment_percent or 30)
            new_total = Decimal(str(quotation.total_amount))
            booking.reservation_fee = new_total * dp_factor
        else:
            # Fixed package calculation
            unit_price = Decimal(str(package_details.get("unit_price", 0)))
            p_mode = package_details.get("pricing_mode", "per_pax")
            p_unit = package_details.get("price_unit", "per_guest")
            
            if p_mode == "fixed" or p_unit != "per_guest":
                new_base_amount = Decimal(str(package_details.get("base_amount", 0)))
            else:
                new_base_amount = unit_price * new_guest_count
            
            addon_total = sum(Decimal(str(a.get("price", 0))) for a in (quotation.addons or []))
            new_total = new_base_amount + addon_total
            
            details = package_details.copy()
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

    if is_customer:
        quotation.customer_signature = signature_data
        quotation.customer_signed_at = datetime.now()
    elif is_caterer:
        quotation.caterer_signature = signature_data
        quotation.caterer_signed_at = datetime.now()
        if save_signature and booking.caterer:
            booking.caterer.saved_signature = signature_data
    else:
        raise HTTPException(
            status_code=403, 
            detail="Unauthorized: you are not an authorized party to this booking contract."
        )

    # Re-evaluate status based on BOTH signatures
    has_cust = bool(quotation.customer_signature and len(str(quotation.customer_signature)) > 20)
    has_cat = bool(quotation.caterer_signature and len(str(quotation.caterer_signature)) > 20)

    if has_cust and has_cat:
        quotation.status = "signed"
        booking.status = "awaiting_payment"
        from ..services.payment_deadline import activate_initial_payment_request, format_payment_deadline
        payment_request_activated = activate_initial_payment_request(booking)
        deadline_text = format_payment_deadline(booking.payment_deadline_at) or "the configured deadline"
        
        # Notify Both Parties
        if payment_request_activated:
            background_tasks.add_task(NotificationService.notify_status_update, db, booking.user_id, "Payment Request Activated", f"Both parties signed the agreement. Submit the initial payment by {deadline_text}.", f"/bookings/step/payment/{booking.id}", "payment")
            background_tasks.add_task(NotificationService.notify_status_update, db, booking.caterer.user_id, "Payment Request Activated", f"Both parties signed the agreement. The customer has until {deadline_text} to submit the initial payment.", f"/caterer/bookings?open_booking={booking.id}&open_tab=payment", "payment")
    elif has_cust:
        quotation.status = "awaiting_caterer"
        booking.status = "awaiting_caterer"
        
        background_tasks.add_task(NotificationService.notify_status_update, db, booking.caterer.user_id, "Action Required: Sign Contract", f"Customer {current_user.first_name} has signed the contract.", f"/caterer/bookings?open_booking={booking.id}")
    elif has_cat:
        quotation.status = "awaiting_customer"
        booking.status = "awaiting_customer"
        booking.expires_at = None
        db.add(models.BookingHistory(
            booking_id=booking.id,
            status="awaiting_customer",
            notes="Caterer signed and sent the quotation-agreement to the customer.",
        ))
        
        background_tasks.add_task(NotificationService.notify_quotation_ready, db, booking)

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

@router.post("/{booking_id}/quotation/approve")
async def approve_quotation(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db)
):
    current_user = get_session_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    quotation = booking.quotation
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
        
    quotation.customer_approved_at = datetime.now()
    db.commit()
    
    return {"success": True}

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
    
    if quotation.status != "quoted" or booking.status != "pending_quotation":
        raise HTTPException(status_code=409, detail="Deposit options can only be selected while the quotation is awaiting your choice.")
    
    try:
        raw_percent = payload.get("percent", 30)
        percent = int(raw_percent)
        if float(raw_percent) != percent:
            raise ValueError("percentage must be a whole number")
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid deposit percentage.")
    if percent < 20 or percent > 100 or percent % 5:
        raise HTTPException(status_code=400, detail="Deposit percentage must be in 5% steps from 20% to 100%.")
    if percent not in get_quotation_payment_terms(quotation, booking.caterer):
        raise HTTPException(status_code=400, detail="Choose one of the deposit options included with this quotation.")
    quotation.downpayment_percent = percent
    
    from decimal import Decimal
    dp_factor = Decimal(str(percent)) / Decimal("100")
    total_amount = Decimal(str(quotation.total_amount or 0)).quantize(Decimal("0.01"))
    new_deposit = (total_amount * dp_factor).quantize(Decimal("0.01"))
    booking.reservation_fee = float(new_deposit)

    submitted = payload.get("confirm") is True
    if submitted:
        quotation.status = "awaiting_caterer"
        booking.status = "awaiting_caterer"
        booking.expires_at = None
        db.add(models.BookingHistory(
            booking_id=booking.id,
            status="awaiting_caterer",
            notes=f"Customer submitted a {percent}% downpayment choice for caterer review.",
        ))
    
    db.commit()

    if submitted and booking.caterer:
        await NotificationService.notify_status_update(
            db,
            booking.caterer.user_id,
            "Customer selected a deposit option",
            f"The customer chose a {percent}% downpayment (₱{new_deposit:,.2f}) for '{booking.event_name or booking.event_type}'. Review the quotation and sign the agreement.",
            f"/caterer/bookings?open_booking={booking.id}",
        )
        await manager.broadcast_to_user(
            booking.user_id,
            {"type": "status_update", "booking_id": booking.id, "status": booking.status},
        )
    
    return {
        "success": True,
        "total_amount": float(total_amount),
        "downpayment_percent": percent,
        "new_deposit": float(new_deposit),
        "remaining_balance": float(max(total_amount - new_deposit, Decimal("0.00"))),
        "status": quotation.status,
        "submitted": submitted,
    }

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
        
    if not booking.event_date:
        raise HTTPException(status_code=400, detail="Booking has no event date for the balance due date.")

    try:
        from datetime import date as date_cls
        requested_due = date_cls.fromisoformat(str(payload.get("due_date") or "").strip())
        if requested_due < date_cls.today():
            raise ValueError("Due date cannot be in the past.")
        due_date_str = requested_due.isoformat()
        booking.balance_due_date = datetime.combine(requested_due, datetime.min.time())
        db.add(models.BookingHistory(
            booking_id=booking.id,
            status=booking.status,
            notes=f"Balance due date set to {due_date_str} by caterer."
        ))
        db.commit()
        
        # --- Trigger Notification ---
        await NotificationService.notify_status_update(
            db,
            booking.user_id,
            "Balance Due Date Updated",
            f"The remaining balance for '{booking.event_name}' is due by {due_date_str}. You may pay online via GCash or Bank, or request cash payment from the caterer.",
            f"/customer/bookings/manage/{booking.id}",
        )
        
        return {"status": "success", "due_date": due_date_str}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
