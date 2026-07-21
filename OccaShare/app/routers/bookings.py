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
from ..services.payment_verification import payment_verification_service
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
    import base64
    content_bytes = upload_file.file.read()
    b64 = base64.b64encode(content_bytes).decode('utf-8')
    mime = upload_file.content_type or 'image/jpeg'
    return f"data:{mime};base64,{b64}"

def save_base64_file(base64_str: str) -> str:
    if not base64_str or "," not in base64_str:
        return ""
    # Already a data URI, just return it
    return base64_str

@router.get("/my")
async def my_bookings_redirect():
    return RedirectResponse(url="/customer/bookings", status_code=303)

# --- Wizard Steps ---

# --- Dedicated A La Carte Checkout ---
@router.get("/alacarte/checkout/{caterer_id}", response_class=HTMLResponse)
async def alacarte_checkout_page(request: Request, caterer_id: str, items: str, booking_id: Optional[int] = None, db: Session = Depends(database.get_db)):
    if caterer_id == "None" or not caterer_id.isdigit():
        return RedirectResponse(url="/customer/marketplace?error_msg=Invalid caterer selected.", status_code=303)
    caterer_id_int = int(caterer_id)
    caterer = db.query(models.CatererProfile).filter(models.CatererProfile.id == caterer_id_int).first()
    if not caterer or caterer.verification_status != 'Verified' or not caterer.user.is_verified:
        return RedirectResponse(url="/customer/marketplace?error_msg=This partner is not currently authorized to accept bookings.")
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/bookings/alacarte/checkout/{caterer_id}?items={items}")
    
    # Parse multiple IDs with type prefixes (m_ for MenuItem, e_ for Equipment, s_ for Service)
    m_ids, e_ids, s_ids = [], [], []
    for id_str in items.split(","):
        id_str = id_str.strip()
        if not id_str: continue
        if id_str.startswith('m_'):
            m_ids.append(int(id_str[2:]))
        elif id_str.startswith('e_'):
            e_ids.append(int(id_str[2:]))
        elif id_str.startswith('s_'):
            s_ids.append(int(id_str[2:]))
        elif id_str.isdigit():
            m_ids.append(int(id_str)) # legacy fallback
            
    menu_items = db.query(models.MenuItem).filter(
        models.MenuItem.id.in_(m_ids),
        models.MenuItem.available_for_order == True
    ).all() if m_ids else []
    
    equipment_items = db.query(models.Equipment).filter(
        models.Equipment.id.in_(e_ids),
        models.Equipment.status == 'available'
    ).all() if e_ids else []
    
    service_items = db.query(models.Service).filter(
        models.Service.id.in_(s_ids),
        models.Service.status == 'available'
    ).all() if s_ids else []
    
    if not caterer or (not menu_items and not equipment_items and not service_items):
        return RedirectResponse(url="/marketplace", status_code=303)
        
    requires_kyc = any(eq.requires_kyc for eq in equipment_items)
        
    booking = db.query(models.Booking).get(booking_id) if booking_id else None
    
    return templates.TemplateResponse("customer/booking_wizard/alacarte_checkout.html", {
        "request": request,
        "user": user,
        "caterer": caterer,
        "menu_items": menu_items,
        "equipment_items": equipment_items,
        "service_items": service_items,
        "items_raw": items,
        "booking": booking,
        "requires_kyc": requires_kyc,
        "current_step": 1
    })

@router.post("/alacarte/checkout/draft")
async def alacarte_checkout_draft(
    request: Request,
    caterer_id: int = Form(...),
    items: str = Form(""),
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
        
        # Determine Booking Type for Draft
        is_rental = False
        has_services = False
        has_food = False
        if cart_data:
            cart_items = json.loads(cart_data)
            for item in cart_items:
                i_type = item.get('type', 'Menu')
                if i_type == 'Equipment': is_rental = True
                elif i_type == 'Service': has_services = True
                else: has_food = True
        elif items:
            for id_str in items.split(","):
                id_str = id_str.strip()
                if not id_str: continue
                if id_str.startswith('e_'): is_rental = True
                elif id_str.startswith('s_'): has_services = True
                else: has_food = True
                
        is_mixed = ((has_food and is_rental) or (has_food and has_services) or (is_rental and has_services))
        
        if is_mixed:
            document_type = "booking_agreement"
            event_name = f"Mixed Order (Draft): {full_name}"
            event_type = "Mixed Order"
        elif is_rental:
            document_type = "rental_agreement"
            event_name = f"Equipment Rental (Draft): {full_name}"
            event_type = "Equipment Rental"
        elif has_services:
            document_type = "service_agreement"
            event_name = f"Service Booking (Draft): {full_name}"
            event_type = "Service Booking"
        else:
            document_type = "invoice"
            event_name = f"Food Order (Draft): {full_name}"
            event_type = "Ala Carte Order"

        # Create Draft Booking
        new_booking = models.Booking(
            user_id=user.id,
            caterer_id=caterer_id,
            event_name=event_name,
            event_type=event_type,
            event_date=event_date_obj,
            event_time=event_time_obj,
            venue_address=address,
            guest_count=quantity,
            total_amount=total_amount,
            total_price=total_amount,
            reservation_fee=total_amount,
            status="draft",
            transaction_type="fast_track",
            document_type=document_type,
            custom_requirements={
                "recipient_name": full_name,
                "recipient_contact": contact_number
            }
        )
        db.add(new_booking)
        db.flush()

        # Add Menu Items to Draft
        if cart_data:
            cart_items = json.loads(cart_data)
            for item in cart_items:
                item_type = item.get('type', 'Menu')
                qty = int(item.get('qty', item.get('quantity', 1)))
                if item_type == 'Equipment':
                    e_item = db.query(models.Equipment).get(int(item['id']))
                    if e_item:
                        price = item.get('price')
                        if price is None: price = e_item.rental_price
                        db.add(models.BookingMenuItem(booking_id=new_booking.id, equipment_id=e_item.id, price=float(price or 0), quantity=qty))
                elif item_type == 'Service':
                    s_item = db.query(models.Service).get(int(item['id']))
                    if s_item:
                        price = item.get('price')
                        if price is None: price = s_item.selling_price
                        
                        # --- Smart Capacity Phase 2 ---
                        item_qty = qty
                        if getattr(s_item, 'capacity_type', 'unit_based') == 'staff_based' and getattr(s_item, 'staff_to_pax_ratio', 0) > 0:
                            import math
                            required = max(getattr(s_item, 'min_staff_required', 1), math.ceil(quantity / s_item.staff_to_pax_ratio))
                            if item_qty < required:
                                item_qty = required
                                
                        db.add(models.BookingMenuItem(booking_id=new_booking.id, service_id=s_item.id, price=float(price or 0), quantity=item_qty))
                else:
                    m_item = db.query(models.MenuItem).get(int(item['id']))
                    if m_item:
                        price = item.get('price')
                        if price is None: price = m_item.price
                        db.add(models.BookingMenuItem(
                            booking_id=new_booking.id,
                            menu_item_id=m_item.id,
                            price=float(price or 0),
                            quantity=qty,
                            choices=item.get('choices')
                        ))
        elif items:
            for id_str in items.split(","):
                id_str = id_str.strip()
                if not id_str: continue
                if id_str.startswith('e_'):
                    e_item = db.query(models.Equipment).get(int(id_str[2:]))
                    if e_item: db.add(models.BookingMenuItem(booking_id=new_booking.id, equipment_id=e_item.id, price=e_item.rental_price))
                elif id_str.startswith('s_'):
                    s_item = db.query(models.Service).get(int(id_str[2:]))
                    if s_item:
                        qty = 1
                        if getattr(s_item, 'capacity_type', 'unit_based') == 'staff_based' and getattr(s_item, 'staff_to_pax_ratio', 0) > 0:
                            import math
                            qty = max(getattr(s_item, 'min_staff_required', 1), math.ceil(quantity / s_item.staff_to_pax_ratio))
                        db.add(models.BookingMenuItem(booking_id=new_booking.id, service_id=s_item.id, price=s_item.selling_price, quantity=qty))
                else:
                    item_id = int(id_str[2:]) if id_str.startswith('m_') else int(id_str)
                    m_item = db.query(models.MenuItem).get(item_id)
                    if m_item: db.add(models.BookingMenuItem(booking_id=new_booking.id, menu_item_id=m_item.id, price=m_item.price))
            
        db.commit()

        return {"success": True, "booking_id": new_booking.id}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": str(e)}

@router.post("/alacarte/checkout/submit")
async def alacarte_checkout_submit(
    request: Request,
    caterer_id: int = Form(...),
    items: str = Form(""), # Legacy
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
    terms_agreement: Optional[str] = Form(None),
    pullout_time: Optional[str] = Form(None),
    event_duration: Optional[int] = Form(None),
    province: Optional[str] = Form(None),
    municipality: Optional[str] = Form(None),
    security_deposit_amount: float = Form(0.0),
    payment_proof: Optional[UploadFile] = File(None),
    id_document: Optional[UploadFile] = File(None),
    selfie: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db)
):
    user = get_current_user_from_session(request, db)
    if not user:
        return {"success": False, "message": "Unauthorized"}
    
    try:
        # Save payment proof if uploaded
        proof_url = None
        if payment_proof and payment_proof.filename:
            import base64
            content_bytes = payment_proof.file.read()
            b64 = base64.b64encode(content_bytes).decode('utf-8')
            mime = payment_proof.content_type or 'image/jpeg'
            proof_url = f"data:{mime};base64,{b64}"
            
        # Handle KYC Documents if provided
        if id_document and id_document.filename and selfie and selfie.filename:
            import base64
            id_content = id_document.file.read()
            id_b64 = base64.b64encode(id_content).decode('utf-8')
            id_mime = id_document.content_type or 'image/jpeg'
            id_url = f"data:{id_mime};base64,{id_b64}"
            
            selfie_content = selfie.file.read()
            selfie_b64 = base64.b64encode(selfie_content).decode('utf-8')
            selfie_mime = selfie.content_type or 'image/jpeg'
            selfie_url = f"data:{selfie_mime};base64,{selfie_b64}"
            
            kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == user.id).first()
            if not kyc_record:
                kyc_record = models.IdentityVerification(user_id=user.id)
                db.add(kyc_record)
            
            kyc_record.document_url = id_url
            kyc_record.selfie_url = selfie_url
            kyc_record.verification_status = "pending_manual_review"
            kyc_record.fraud_score = 0.0
            
            user.is_verified = False
            user.is_kyc_complete = False
            db.commit()

        # Spam Limit Validation (Flow B Rule 1)
        unpaid_spam_count = db.query(models.Booking).filter(
            models.Booking.user_id == user.id,
            models.Booking.status.in_(['draft', 'pending', 'pending_quotation', 'awaiting_caterer', 'awaiting_payment', 'pending_payment']),
            models.Booking.id != (booking_id or 0)
        ).count()
        if unpaid_spam_count >= 2:
            return {"success": False, "message": "Spam Protection: You have 2 or more unpaid/pending bookings. Please complete them first."}
            
        booking = db.query(models.Booking).get(booking_id) if booking_id else None
        
        # --- AI Receipt Verification (Zero-Trust) ---
        if proof_url and payment_method not in ["CASH", "COD"]:
            verify_booking = booking if booking else models.Booking(id=0, total_amount=total_amount, caterer_id=caterer_id, payment_method=payment_method)
            
            # We must temporarily set total_amount and method so check_for_fraud can use it
            original_amount = verify_booking.total_amount
            original_method = verify_booking.payment_method
            verify_booking.total_amount = total_amount
            verify_booking.payment_method = payment_method
            
            verify_results = await payment_verification_service.check_for_fraud(db, verify_booking, proof_url)
            
            # Revert amount if validation fails
            verify_booking.total_amount = original_amount
            
            if verify_results["confidence"] < 40:
                flags = verify_results.get("flags", [])
                error_detail = flags[0] if flags else "The uploaded image is either not a valid receipt, or the details (amount, date, reference, caterer name) do not match the required booking information."
                return {"success": False, "message": f"Payment Verification Failed: {error_detail}"}
            
            # Extract ref if missing
            extracted_ref = verify_results.get("extracted_data", {}).get("reference_no")
            extracted_hash = payment_verification_service.get_image_hash(proof_url)
            
            if booking:
                if extracted_ref: booking.payment_reference = extracted_ref
                booking.proof_image_hash = extracted_hash

        # --- Phase 2: Capacity Validation ---
        event_date_obj = date.fromisoformat(delivery_date)
        event_time_obj = datetime.strptime(delivery_time, "%H:%M").time()
        event_end_time_obj = None
        if event_duration:
            event_end_time_obj = (datetime.combine(event_date_obj, event_time_obj) + timedelta(hours=event_duration)).time()

        requested_services = []
        if cart_data:
            cart_items = json.loads(cart_data)
            for item in cart_items:
                if item.get('type', 'Menu') == 'Service':
                    s_item = db.query(models.Service).get(int(item['id']))
                    if s_item:
                        item_qty = int(item.get('quantity', 1))
                        if getattr(s_item, 'capacity_type', 'unit_based') == 'staff_based' and getattr(s_item, 'staff_to_pax_ratio', 0) > 0:
                            import math
                            required = max(getattr(s_item, 'min_staff_required', 1), math.ceil(quantity / s_item.staff_to_pax_ratio))
                            if item_qty < required: item_qty = required
                        requested_services.append((s_item.id, item_qty))
        elif items:
            for id_str in items.split(","):
                id_str = id_str.strip()
                if id_str.startswith('s_'):
                    s_item = db.query(models.Service).get(int(id_str[2:]))
                    if s_item:
                        item_qty = 1
                        if getattr(s_item, 'capacity_type', 'unit_based') == 'staff_based' and getattr(s_item, 'staff_to_pax_ratio', 0) > 0:
                            import math
                            item_qty = max(getattr(s_item, 'min_staff_required', 1), math.ceil(quantity / s_item.staff_to_pax_ratio))
                        requested_services.append((s_item.id, item_qty))
                        
        from ..services.capacity_service import CapacityService
        is_capacity_valid, capacity_msg = CapacityService.validate_booking_capacity(db, caterer_id, event_date_obj, event_time_obj, event_end_time_obj, requested_services, booking_id)
        if not is_capacity_valid:
            return {"success": False, "message": capacity_msg}

        # 1. Update or Create Booking
        
        # New Payment Logic for Ala Carte:
        reservation_fee = total_amount
        if payment_method in ["CASH", "COD"]:
            status = "pending"
            payment_status = "pending"
        else:
            if proof_url:
                status = "pending"
                payment_status = "proof_submitted"
            else:
                status = "pending_payment"
                payment_status = "pending"
        
        if booking:
            if booking.user_id == user.id:
                booking.status = status
                booking.payment_status = payment_status
                booking.payment_method = payment_method
                booking.venue_address = address if fulfillment == "delivery" else "PICKUP"
                booking.special_requests = landmark
                booking.total_amount = total_amount
                booking.reservation_fee = reservation_fee
                booking.security_deposit_amount = security_deposit_amount
                if security_deposit_amount > 0:
                    booking.security_deposit_status = "held" if payment_status in ["paid", "proof_submitted"] else "unpaid"
                
                if fulfillment == "delivery" and province and municipality:
                    caterer = db.query(models.CatererProfile).get(caterer_id)
                    if caterer:
                        zone = db.query(models.DeliveryZone).filter(
                            models.DeliveryZone.caterer_id == caterer.id,
                            models.DeliveryZone.province.ilike(f"%{province}%"),
                            models.DeliveryZone.city_municipality.ilike(f"%{municipality}%")
                        ).first()
                        if zone:
                            if zone.is_manual_quote:
                                booking.travel_fee_status = "manual_quote"
                                booking.travel_fee = 0.0
                            else:
                                booking.travel_fee_status = "calculated"
                                booking.travel_fee = zone.fee
                        else:
                            if caterer.out_of_coverage_action == "manual":
                                booking.travel_fee_status = "manual_quote"
                                booking.travel_fee = 0.0
                            else:
                                booking.travel_fee_status = "calculated"
                                booking.travel_fee = caterer.base_delivery_fee or 150.0
                else:
                    booking.travel_fee_status = "waived"
                    booking.travel_fee = 0.0
                
                custom_reqs = booking.custom_requirements or {}
                if pullout_time: custom_reqs["pullout_time"] = pullout_time
                if event_duration: custom_reqs["event_duration"] = event_duration
                custom_reqs["recipient_name"] = full_name
                custom_reqs["recipient_contact"] = contact_number
                booking.custom_requirements = custom_reqs
                
                if terms_agreement:
                    booking.terms_accepted_at = datetime.utcnow()
                    booking.terms_accepted_ip = request.client.host if request.client else "unknown"
                    booking.transaction_type = "fast_track"
                # Clear old items to re-save
                db.query(models.BookingMenuItem).filter(models.BookingMenuItem.booking_id == booking.id).delete()
        
        # Check category to determine document type
        is_rental = False
        has_services = False
        has_food = False
        if cart_data:
            cart_items = json.loads(cart_data)
            for item in cart_items:
                i_type = item.get('type', 'Menu')
                if i_type == 'Equipment': is_rental = True
                elif i_type == 'Service': has_services = True
                else: has_food = True
        elif items:
            for id_str in items.split(","):
                id_str = id_str.strip()
                if not id_str: continue
                if id_str.startswith('e_'): is_rental = True
                elif id_str.startswith('s_'): has_services = True
                else: has_food = True
                
        is_mixed = ((has_food and is_rental) or (has_food and has_services) or (is_rental and has_services))
        
        # Phase 2: Dynamic Document Routing Algorithm
        if is_mixed:
            document_type = "booking_agreement"
            event_name = f"Mixed Order: {full_name}"
            event_type = "Mixed Order"
        elif is_rental:
            document_type = "rental_agreement"
            event_name = f"Equipment Rental: {full_name}"
            event_type = "Equipment Rental"
        elif has_services:
            document_type = "service_agreement"
            event_name = f"Service Booking: {full_name}"
            event_type = "Service Booking"
        else:
            document_type = "invoice"
            event_name = f"Food Order: {full_name}"
            event_type = "Ala Carte Order"
        
        if booking:
            booking.event_name = event_name
            booking.event_type = event_type
            booking.document_type = document_type
            if proof_url:
                booking.payment_proof_url = proof_url
            
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
                security_deposit_amount=security_deposit_amount,
                security_deposit_status="held" if security_deposit_amount > 0 and status == "awaiting_payment" else "unpaid",
                status=status,
                payment_status=payment_status,
                payment_method=payment_method,
                payment_proof_url=proof_url,
                special_requests=landmark,
                transaction_type="fast_track",
                document_type=document_type,
                custom_requirements={
                    "pullout_time": pullout_time if pullout_time else None,
                    "event_duration": event_duration if event_duration else None,
                    "recipient_name": full_name,
                    "recipient_contact": contact_number
                }
            )
            
            if fulfillment == "delivery" and province and municipality:
                caterer = db.query(models.CatererProfile).get(caterer_id)
                if caterer:
                    zone = db.query(models.DeliveryZone).filter(
                        models.DeliveryZone.caterer_id == caterer.id,
                        models.DeliveryZone.province.ilike(f"%{province}%"),
                        models.DeliveryZone.city_municipality.ilike(f"%{municipality}%")
                    ).first()
                    if zone:
                        if zone.is_manual_quote:
                            booking.travel_fee_status = "manual_quote"
                            booking.travel_fee = 0.0
                        else:
                            booking.travel_fee_status = "calculated"
                            booking.travel_fee = zone.fee
                    else:
                        if caterer.out_of_coverage_action == "manual":
                            booking.travel_fee_status = "manual_quote"
                            booking.travel_fee = 0.0
                        else:
                            booking.travel_fee_status = "calculated"
                            booking.travel_fee = caterer.base_delivery_fee or 150.0
            else:
                booking.travel_fee_status = "waived"
                booking.travel_fee = 0.0
                
            # Apply extracted data from AI if this is a new booking
            if 'extracted_ref' in locals() and extracted_ref:
                booking.payment_reference = extracted_ref
            if 'extracted_hash' in locals() and extracted_hash:
                booking.proof_image_hash = extracted_hash

            if terms_agreement:
                booking.terms_accepted_at = datetime.utcnow()
                booking.terms_accepted_ip = request.client.host if request.client else "unknown"
            
            db.add(booking)
            db.flush()

        # Add Items
        if cart_data:
            cart_items = json.loads(cart_data)
            for item in cart_items:
                i_type = item.get('type', 'Menu')
                if i_type == 'Equipment':
                    e_item = db.query(models.Equipment).get(int(item['id']))
                    if e_item:
                        price = item.get('price')
                        if price is None: price = e_item.rental_price
                        booking_item = models.BookingMenuItem(
                            booking_id=booking.id,
                            equipment_id=e_item.id,
                            price=float(price or 0),
                            quantity=int(item.get('quantity', 1)),
                            choices=item.get('choices')
                        )
                        db.add(booking_item)
                elif i_type == 'Service':
                    s_item = db.query(models.Service).get(int(item['id']))
                    if s_item:
                        price = item.get('price')
                        if price is None: price = s_item.selling_price
                        
                        # --- Smart Capacity Phase 2 ---
                        item_qty = int(item.get('quantity', 1))
                        if getattr(s_item, 'capacity_type', 'unit_based') == 'staff_based' and getattr(s_item, 'staff_to_pax_ratio', 0) > 0:
                            import math
                            required = max(getattr(s_item, 'min_staff_required', 1), math.ceil(quantity / s_item.staff_to_pax_ratio))
                            if item_qty < required:
                                item_qty = required

                        booking_item = models.BookingMenuItem(
                            booking_id=booking.id,
                            service_id=s_item.id,
                            price=float(price or 0),
                            quantity=item_qty,
                            choices=item.get('choices')
                        )
                        db.add(booking_item)
                else:
                    m_item = db.query(models.MenuItem).get(int(item['id']))
                    if m_item:
                        price = item.get('price')
                        if price is None: price = m_item.price
                        booking_item = models.BookingMenuItem(
                            booking_id=booking.id,
                            menu_item_id=m_item.id,
                            price=float(price or 0),
                            quantity=int(item.get('quantity', 1)),
                            choices=item.get('choices')
                        )
                        db.add(booking_item)
        elif items:
            # Legacy Fallback Parsing
            for id_str in items.split(","):
                id_str = id_str.strip()
                if not id_str: continue
                if id_str.startswith('e_'):
                    e_item = db.query(models.Equipment).get(int(id_str[2:]))
                    if e_item:
                        db.add(models.BookingMenuItem(booking_id=booking.id, equipment_id=e_item.id, price=e_item.rental_price, quantity=1))
                elif id_str.startswith('s_'):
                    s_item = db.query(models.Service).get(int(id_str[2:]))
                    if s_item:
                        qty = 1
                        if getattr(s_item, 'capacity_type', 'unit_based') == 'staff_based' and getattr(s_item, 'staff_to_pax_ratio', 0) > 0:
                            import math
                            qty = max(getattr(s_item, 'min_staff_required', 1), math.ceil(quantity / s_item.staff_to_pax_ratio))
                        db.add(models.BookingMenuItem(booking_id=booking.id, service_id=s_item.id, price=s_item.selling_price, quantity=qty))
                else:
                    item_id = int(id_str[2:]) if id_str.startswith('m_') else int(id_str)
                    m_item = db.query(models.MenuItem).get(item_id)
                    if m_item:
                        db.add(models.BookingMenuItem(booking_id=booking.id, menu_item_id=m_item.id, price=m_item.price, quantity=1))

        db.commit()
        
        # Trigger real-time notifications
        from ..services.notification import NotificationService
        await NotificationService.notify_new_booking(db, booking)
        if proof_url:
            await NotificationService.notify_payment_received(db, booking, float(total_amount), "Payment")
            
        return {"success": True, "booking_id": booking.id}
    except Exception as e:
        db.rollback()
        print(f"Error in alacarte submit: {e}")
        return {"success": False, "message": str(e)}


# Step 1: Initialize/Select Caterer (from Profile Page)
@router.get("/start/{caterer_id}")
async def start_booking(request: Request, caterer_id: int, package_id: Optional[int] = None, db: Session = Depends(database.get_db)):
    caterer = db.query(models.CatererProfile).filter(models.CatererProfile.id == caterer_id).first()
    if not caterer or caterer.verification_status != 'Verified' or not caterer.user.is_verified:
        return RedirectResponse(url="/customer/marketplace?error_msg=This partner is not currently authorized to accept bookings.")
    
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

@router.get("/custom/request/{caterer_id}")
async def custom_booking_request_form(request: Request, caterer_id: int, db: Session = Depends(database.get_db)):
    caterer = db.query(models.CatererProfile).filter(models.CatererProfile.id == caterer_id).first()
    if not caterer or caterer.verification_status != 'Verified' or not caterer.user.is_verified:
        return RedirectResponse(url="/customer/marketplace?error_msg=This partner is not currently authorized to accept bookings.")

    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/bookings/custom/request/{caterer_id}")
    
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer:
        return RedirectResponse(url="/customer/marketplace", status_code=303)
        
    return templates.TemplateResponse("customer/booking_wizard/custom_rfq.html", {
        "request": request,
        "caterer": caterer,
        "user": user,
        "active_page": "bookings",
        "current_step": 1
    })

@router.post("/custom/submit")
async def custom_booking_submit(
    request: Request,
    caterer_id: int = Form(...),
    event_name: str = Form(...),
    event_type: str = Form(...),
    event_date: date = Form(...),
    event_time: time = Form(...),
    guest_count: int = Form(...),
    venue_address: str = Form(...),
    budget: float = Form(0.0),
    theme_description: str = Form(""),
    reference_images: list[UploadFile] = File(None),
    db: Session = Depends(database.get_db)
):
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/bookings/custom/request/{caterer_id}", status_code=303)
    
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer:
        return RedirectResponse(url="/customer/marketplace", status_code=303)
        
    min_guests = caterer.min_pax or 20
    if guest_count < min_guests:
        return RedirectResponse(url=f"/bookings/custom/request/{caterer_id}?error=Minimum+guest+count+is+{min_guests}", status_code=303)
        
    # Handle File Uploads
    image_urls = []
    upload_dir = "app/static/uploads/custom_events"
    os.makedirs(upload_dir, exist_ok=True)
    
    if reference_images:
        for file in reference_images:
            if file.filename and file.filename != '':
                import base64
                content_bytes = file.file.read()
                b64 = base64.b64encode(content_bytes).decode('utf-8')
                mime = file.content_type or 'image/jpeg'
                image_urls.append(f"data:{mime};base64,{b64}")

    new_booking = models.Booking(
        caterer_id=caterer_id,
        user_id=user.id,
        event_name=event_name,
        event_type=event_type,
        event_date=event_date,
        event_time=event_time,
        guest_count=guest_count,
        venue_address=venue_address,
        is_custom_event=True,
        custom_requirements={
            "budget": budget,
            "theme_description": theme_description,
            "reference_images": image_urls
        },
        status="pending_review", # Updated to PENDING REVIEW as per the workflow plan
        total_amount=0.0,
        reservation_fee=0.0,
        document_type="booking_agreement"
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    
    # Send Notification to Caterer
    from ..services.notification import NotificationService
    import asyncio
    from ..services.realtime import manager

    caterer_msg = f"New Custom Event Request from {user.first_name or user.email}."
    notif = models.Notification(
        user_id=caterer.user_id,
        title="Custom Request Received",
        message=caterer_msg,
        type="Booking",
        link=f"/caterer/dashboard?page=bookings"
    )
    db.add(notif)
    db.commit()

    asyncio.create_task(manager.broadcast_to_user(caterer.user_id, {
        "type": "new_notification",
        "title": notif.title,
        "message": notif.message,
        "url": notif.link
    }))
    
    # Broadcast Dashboard Update
    asyncio.create_task(manager.broadcast_to_user(caterer.user_id, {
        "type": "dashboard_update",
        "message": "New custom request received."
    }))
    
    # Redirect straight to the management dashboard to show the pending review status
    return RedirectResponse(url=f"/customer/bookings/manage/{new_booking.id}", status_code=303)

@router.get("/continue/{booking_id}")
async def continue_draft_booking(booking_id: int, request: Request, db: Session = Depends(database.get_db)):
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/bookings/continue/{booking_id}")
        
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.user_id != user.id:
        return RedirectResponse(url="/customer/dashboard?error_msg=Booking+not+found", status_code=303)
        
    # Valid in-progress statuses before payment is completed
    valid_statuses = [
        'draft', 'pending_quotation', 'awaiting_caterer', 'awaiting_payment',
        'pending_review', 'additional_info_required', 'under_review', 'revision_requested'
    ]
    if booking.status not in valid_statuses:
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}", status_code=303)
        
    # Re-populate session so back-navigation works
    request.session["booking_data"] = {
        "booking_id": booking.id,
        "caterer_id": booking.caterer_id,
        "package_id": booking.package_id,
        "user_id": user.id
    }
    
    # Step logic routing
    
    # 0. Ala Carte / Fast-Track Logic
    if booking.event_type in ["Ala Carte Order", "Equipment Rental", "Service Booking"] or not booking.package_id:
        if booking.status == 'draft':
            # Reconstruct menu_id parameter
            items = db.query(models.BookingMenuItem).filter(models.BookingMenuItem.booking_id == booking.id).all()
            menu_parts = []
            for item in items:
                if item.equipment_id: menu_parts.append(f"e_{item.equipment_id}")
                elif item.service_id: menu_parts.append(f"s_{item.service_id}")
                elif item.menu_item_id: menu_parts.append(f"m_{item.menu_item_id}")
            items_str = ",".join(menu_parts)
            
            # Stale Data Validation (Inventory Check)
            from datetime import date
            is_valid = True
            if booking.event_date and booking.event_date < date.today():
                is_valid = False
                request.session["flash_error"] = "The draft's delivery date has passed. Please select a new date."
                
            if not is_valid:
                db.delete(booking)
                db.commit()
                return RedirectResponse(url=f"/bookings/alacarte/checkout/{booking.caterer_id}?items={items_str}", status_code=303)
                
            # If valid, just go to checkout and pass booking_id
            return RedirectResponse(url=f"/bookings/alacarte/checkout/{booking.caterer_id}?items={items_str}&booking_id={booking.id}", status_code=303)
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}", status_code=303)

    # 1. Does user need KYC?
    # NEW: Skip KYC if user has booking history
    has_history = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        models.Booking.id != booking.id,
        models.Booking.status.notin_(['draft', 'cancelled', 'pending_quotation'])
    ).first() is not None

    if not user.is_verified and not user.is_kyc_complete and not has_history:
        return RedirectResponse(url=f"/bookings/step/kyc/{booking.id}", status_code=303)
        
    # If custom event and waiting for caterer, redirect to dashboard/manage
    if booking.is_custom_event and booking.status in ["pending_quotation", "pending_review", "additional_info_required", "under_review", "revision_requested"]:
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}", status_code=303)
        
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
        models.MenuItem.is_archived == False,
        models.MenuItem.available_for_package == True,
        models.MenuItem.pricing_type == "fixed"
    ).all()
    
    addon_items = [i for i in all_menu_items if i.is_addon]
    
    addon_equipment = db.query(models.Equipment).filter(
        models.Equipment.caterer_id == caterer.id,
        models.Equipment.is_archived == False,
        models.Equipment.is_addon == True
    ).all()

    addon_services = db.query(models.Service).filter(
        models.Service.caterer_id == caterer.id,
        models.Service.is_archived == False,
        models.Service.is_addon == True
    ).all()

    # Get selected addons if existing booking
    selected_addon_ids = []
    selected_addon_equipment_ids = []
    selected_addon_service_ids = []
    if booking:
        selected_addon_ids = [item.menu_item_id for item in booking.selected_items if item.is_add_on and item.menu_item_id]
        selected_addon_equipment_ids = [item.equipment_id for item in booking.selected_items if item.is_add_on and item.equipment_id]
        selected_addon_service_ids = [item.service_id for item in booking.selected_items if item.is_add_on and item.service_id]

    return templates.TemplateResponse("customer/booking_wizard/step_details.html", {
        "request": request,
        "booking_data": data,
        "booking": booking,
        "package": package,
        "caterer": caterer,
        "all_menu_items": all_menu_items,
        "addon_items": addon_items,
        "addon_equipment": addon_equipment,
        "addon_services": addon_services,
        "selected_addon_ids": selected_addon_ids,
        "selected_addon_equipment_ids": selected_addon_equipment_ids,
        "selected_addon_service_ids": selected_addon_service_ids,
        "user": user,
        "current_step": 1,
        "active_page": "bookings",
        "is_locked": booking.status not in ["draft", "pending", "pending_quotation", "awaiting_caterer"] if booking else False,
        "getattr": getattr
    })

@router.post("/step/details")
async def step_details_submit(
    request: Request,
    caterer_id: int = Form(...),
    package_id_str: Optional[str] = Form(None, alias="package_id"),
    booking_id_str: Optional[str] = Form(None, alias="booking_id"),
    event_name_str: Optional[str] = Form(None, alias="event_name"),
    event_type_str: Optional[str] = Form(None, alias="event_type"),
    event_date_str: Optional[str] = Form(None, alias="event_date"),
    event_time_str: Optional[str] = Form(None, alias="event_time"),
    event_end_time_str: Optional[str] = Form(None, alias="event_end_time"),
    guest_count_str: Optional[str] = Form("0", alias="guest_count"),
    venue_address: Optional[str] = Form(""),
    total_price: Optional[float] = Form(0.0),
    reservation_fee: Optional[float] = Form(0.0),
    selected_items: list[int] = Form(default=[]),
    selected_addons: list[int] = Form(default=[]),
    selected_equipment_addons: list[int] = Form(default=[]),
    selected_service_addons: list[int] = Form(default=[]),
    special_requests: Optional[str] = Form(""),
    theme_motif: Optional[str] = Form(None),
    province: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    barangay: Optional[str] = Form(None),
    other_event_type: Optional[str] = Form(None),
    db: Session = Depends(database.get_db)
):
    # Safely parse times and dates
    event_end_time = None
    if event_end_time_str and event_end_time_str.strip():
        try:
            event_end_time = time.fromisoformat(event_end_time_str)
        except:
            pass
            
    event_date = None
    if event_date_str and event_date_str.strip():
        try:
            event_date = date.fromisoformat(event_date_str)
        except:
            pass
            
    event_time = None
    if event_time_str and event_time_str.strip():
        try:
            # Handle HH:MM format
            parts = event_time_str.split(':')
            if len(parts) >= 2:
                event_time = time(int(parts[0]), int(parts[1]))
        except:
            pass
            
    guest_count = 0
    if guest_count_str and guest_count_str.strip():
        try:
            guest_count = int(guest_count_str)
        except:
            pass

    # Safely parse IDs from strings to handle empty form values
    package_id = int(package_id_str) if package_id_str and package_id_str.strip() else None
    booking_id = int(booking_id_str) if booking_id_str and booking_id_str.strip() else None

    event_name = event_name_str.strip() if event_name_str else ""
    event_type = event_type_str.strip() if event_type_str else ""

    # Handle custom event type
    final_event_type = event_type
    if event_type == "Other" and other_event_type and other_event_type.strip():
        final_event_type = other_event_type.strip()

    user = get_current_user_from_session(request, db)
    redirect_base = f"/bookings/step/details/{booking_id}" if booking_id else "/bookings/step/details"
    if not user: return RedirectResponse(url=f"/auth/login?next={redirect_base}", status_code=303)

    if booking_id:
        existing_booking = db.query(models.Booking).get(booking_id)
        if existing_booking and existing_booking.status not in ["draft", "pending", "pending_quotation", "awaiting_caterer"]:
            return RedirectResponse(url=f"{redirect_base}?booking_error=Booking+is+already+locked+and+cannot+be+modified.", status_code=303)

    if not event_date:
        return RedirectResponse(url=f"{redirect_base}?booking_error=err-date:Valid+event+date+is+required", status_code=303)
    if not event_time:
        return RedirectResponse(url=f"{redirect_base}?booking_error=err-time:Valid+event+time+is+required", status_code=303)
    if not event_name:
        return RedirectResponse(url=f"{redirect_base}?booking_error=err-name:Event+name+is+required", status_code=303)
    if not final_event_type:
        return RedirectResponse(url=f"{redirect_base}?booking_error=err-type:Event+type+is+required", status_code=303)

    # Construct venue address if missing from hidden field
    if not venue_address and province and city and barangay:
        venue_address = f"{barangay}, {city}, {province}"

    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer: return RedirectResponse(url=f"/customer/marketplace", status_code=303)

    from datetime import date as dt_date, timedelta, datetime
    today = dt_date.today()
    
    # 🚨 VALIDATION 1: Strict Lead Time Validation
    # Must be at least `caterer.booking_lead_time` days in the future
    lead_time = caterer.booking_lead_time or 3
    min_lead_date = today + timedelta(days=lead_time)
    if event_date < min_lead_date:
        return RedirectResponse(url=f"{redirect_base}?booking_error=err-date:Event+date+must+be+at+least+{lead_time}+days+in+advance+for+proper+preparation.", status_code=303)

    max_advance_date = today + timedelta(days=210)
    if event_date > max_advance_date:
        return RedirectResponse(url=f"{redirect_base}?booking_error=err-date:Bookings+can+only+be+made+up+to+7+months+in+advance.", status_code=303)

    # 🚨 VALIDATION 1.5: Sensible Operating Hours Check
    # Restrict events to standard operating hours (8:00 AM to 8:00 PM)
    if event_time.hour < 8 or event_time.hour >= 21:
        return RedirectResponse(url=f"{redirect_base}?booking_error=err-time:Please+select+a+time+between+8:00+AM+and+8:00+PM.", status_code=303)

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
    
    turnover = caterer.equipment_turnover_hours or 4.0
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

    # 1.5. Capacity Check for Addon Services
    requested_services = []
    for serv_id in selected_service_addons:
        serv_item = db.query(models.Service).get(serv_id)
        if serv_item:
            qty = 1
            if getattr(serv_item, 'capacity_type', 'unit_based') == 'staff_based' and getattr(serv_item, 'staff_to_pax_ratio', 0) > 0:
                import math
                qty = max(getattr(serv_item, 'min_staff_required', 1), math.ceil(guest_count / serv_item.staff_to_pax_ratio))
            requested_services.append((serv_id, qty))
            
    from ..services.capacity_service import CapacityService
    is_capacity_valid, capacity_msg = CapacityService.validate_booking_capacity(db, caterer_id, event_date, event_time, event_end_time, requested_services, booking_id)
    if not is_capacity_valid:
        return RedirectResponse(url=f"{redirect_base}?booking_error={capacity_msg}", status_code=303)

    # 2. Create or Update Booking
    booking = None
    if booking_id:
        booking = db.query(models.Booking).get(booking_id)
    
    if booking and booking.user_id == user.id:
        # Update existing
        booking.event_name = event_name
        booking.event_type = final_event_type
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
        booking.document_type = "booking_agreement"
        
        custom_reqs = booking.custom_requirements or {}
        if theme_motif: custom_reqs["theme_motif"] = theme_motif
        booking.custom_requirements = custom_reqs
        
        # Clear old items to re-save
        db.query(models.BookingMenuItem).filter(models.BookingMenuItem.booking_id == booking.id).delete()
    else:
        # Create New Draft
        booking = models.Booking(
            user_id=user.id,
            caterer_id=caterer_id,
            package_id=package_id,
            event_name=event_name,
            event_type=final_event_type,
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
            status="draft",
            document_type="booking_agreement",
            custom_requirements={"theme_motif": theme_motif} if theme_motif else None
        )
        db.add(booking)
    
    # Update Travel Fee
    if province and city:
        zone = db.query(models.DeliveryZone).filter(
            models.DeliveryZone.caterer_id == caterer.id,
            models.DeliveryZone.province.ilike(f"%{province}%"),
            models.DeliveryZone.city_municipality.ilike(f"%{city}%")
        ).first()
        if zone:
            if zone.is_manual_quote:
                booking.travel_fee_status = "manual_quote"
                booking.travel_fee = 0.0
            else:
                booking.travel_fee_status = "calculated"
                booking.travel_fee = zone.fee
        else:
            if caterer.out_of_coverage_action == "manual":
                booking.travel_fee_status = "manual_quote"
                booking.travel_fee = 0.0
            else:
                booking.travel_fee_status = "calculated"
                booking.travel_fee = caterer.base_delivery_fee or 150.0
    else:
        booking.travel_fee_status = "pending"

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
            
    for equip_id in selected_equipment_addons:
        equip_item = db.query(models.Equipment).get(equip_id)
        if equip_item:
            booking_item = models.BookingMenuItem(
                booking_id=booking.id,
                equipment_id=equip_id,
                is_add_on=True,
                price=equip_item.addon_price or 0.0
            )
            db.add(booking_item)

    for serv_id in selected_service_addons:
        serv_item = db.query(models.Service).get(serv_id)
        if serv_item:
            # --- Smart Capacity Phase 2 ---
            qty = 1
            if getattr(serv_item, 'capacity_type', 'unit_based') == 'staff_based' and getattr(serv_item, 'staff_to_pax_ratio', 0) > 0:
                import math
                qty = max(getattr(serv_item, 'min_staff_required', 1), math.ceil(guest_count / serv_item.staff_to_pax_ratio))
                
            booking_item = models.BookingMenuItem(
                booking_id=booking.id,
                service_id=serv_id,
                is_add_on=True,
                price=serv_item.addon_price or 0.0,
                quantity=qty
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

    # Dynamic Routing for Fast-Track
    if booking.transaction_type == 'fast_track':
        if booking.document_type == 'invoice':
            return RedirectResponse(url=f"/bookings/step/payment/{booking.id}", status_code=303)
        elif booking.document_type == 'service_agreement':
            return RedirectResponse(url=f"/bookings/step/quotation/{booking.id}", status_code=303)

    return templates.TemplateResponse("customer/booking_wizard/step_kyc.html", {
        "request": request,
        "booking_id": booking_id,
        "booking": booking,
        "user": user,
        "current_step": 2,
        "active_page": "bookings",
        "is_locked": booking.status not in ["draft", "pending", "pending_quotation", "awaiting_caterer"] if booking else False
    })

# Phase 3: Quotation Review & Contract
@router.get("/step/quotation/{booking_id}", response_class=HTMLResponse)
async def step_quotation_page(booking_id: int, request: Request, db: Session = Depends(database.get_db)):
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/bookings/step/quotation/{booking_id}")
        
    booking = db.query(models.Booking).get(booking_id)
    if not booking: raise HTTPException(status_code=404)
    
    # Dynamic Routing for Fast-Track
    if booking.transaction_type == 'fast_track' and booking.document_type == 'invoice':
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}", status_code=303)
    
    # STRICT GATE: Ensure user is verified before seeing quotation/contract
    # NEW: Also allow if user has booking history
    has_history = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        models.Booking.id != booking.id,
        models.Booking.status.notin_(['draft', 'cancelled', 'pending_quotation'])
    ).first() is not None

    has_equipment = any(item.equipment_id is not None for item in booking.selected_items)
    if booking.transaction_type != 'fast_track' or has_equipment:
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
        if booking.is_custom_event or booking.travel_fee_status == "manual_quote":
            return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?msg=Waiting+for+caterer+proposal", status_code=303)
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
async def _validate_receipt_with_gemini(b64_string: str, payment_method: str, expected_amount: float = 0.0) -> bool:
    is_valid = False
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        import httpx, base64, json, re
        try:
            # Check if b64_string is already prefixed with data:image
            encoded_string = b64_string.split(",", 1)[1] if "," in b64_string else b64_string
            
            # Try gemini-2.0-flash first, and fallback to gemini-1.5-flash
            models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash"]
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
            
            response = None
            async with httpx.AsyncClient() as client:
                for model in models_to_try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                    print(f"[GEMINI VALIDATION] Trying model: {model}")
                    try:
                        res = await client.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=20.0)
                        if res.status_code == 200:
                            response = res
                            break
                        else:
                            print(f"[GEMINI VALIDATION WARNING] Model {model} failed with status {res.status_code}")
                    except Exception as err:
                        print(f"[GEMINI VALIDATION WARNING] Model {model} request failed: {err}")
            
            if response and response.status_code == 200:
                text = response.json()['candidates'][0]['content']['parts'][0]['text']
                match = re.search(r'\{.*\}', text.strip(), re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    is_valid = parsed.get("is_valid", False)
                    print(f"[GEMINI VALIDATION] Result: {is_valid}, Reason: {parsed.get('reason')}")
            else:
                print(f"[GEMINI API ERROR] All models failed or returned non-200 status code.")
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
                            os.environ["TESSDATA_PREFIX"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tessdata"))
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
        
    booking = db.query(models.Booking).get(booking_id)
    if not booking: raise HTTPException(status_code=404)

    # STRICT GATE: Ensure user is verified before payment (Skip for fast-track unless it's equipment rental)
    has_equipment = any(item.equipment_id is not None for item in booking.selected_items)
    if booking.transaction_type != 'fast_track' or has_equipment:
        has_history = db.query(models.Booking).filter(
            models.Booking.user_id == user.id,
            models.Booking.id != booking_id,
            models.Booking.status.notin_(['draft', 'cancelled', 'pending_quotation'])
        ).first() is not None

        if not user.is_verified and not has_history:
            return RedirectResponse(url=f"/bookings/step/kyc/{booking_id}?auth_needed=1", status_code=303)

    # Get signed quotation to enforce contractual amounts
    from ..services.quotation import quotation_service
    quotation = quotation_service.get_quotation_by_booking(db, booking_id)

    # STRICT GATE: Ensure both parties have signed before allowing payment (ONLY for contract-track)
    if booking.transaction_type != 'fast_track':
        if not quotation or quotation.status != 'signed':
            return RedirectResponse(url=f"/bookings/step/quotation/{booking_id}?error_msg=Both+parties+must+sign+the+contract+before+proceeding+to+payment", status_code=303)
    else:
        # Fast-track (Ala Carte) orders should use their own manage page for payments
        return RedirectResponse(url=f"/customer/bookings/manage/{booking_id}", status_code=303)

    template_name = "customer/booking_wizard/step_payment.html"
    
    return templates.TemplateResponse(template_name, {
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
    if booking.transaction_type != 'fast_track':
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
            
        import base64
        content_bytes = payment_proof.file.read()
        b64 = base64.b64encode(content_bytes).decode('utf-8')
        mime = payment_proof.content_type or 'image/jpeg'
        proof_url = f"data:{mime};base64,{b64}"
            
        # --- AI RECEIPT VALIDATION (GEMINI / OCR) ---
        if payment_plan == 'balance':
            expected_fee = float(booking.total_amount or 0) - float(booking.reservation_fee or 0)
        elif payment_plan == 'full':
            expected_fee = float(booking.total_amount or 0)
            booking.reservation_fee = expected_fee # Update reservation fee to reflect the selected full amount
        elif payment_plan.isdigit():
            # Support dynamic percentage plans (e.g., '30', '50')
            percent = float(payment_plan)
            expected_fee = float(booking.total_amount or 0) * (percent / 100.0)
            booking.reservation_fee = expected_fee # Update reservation fee to reflect the selected tier
        else:
            expected_fee = float(booking.reservation_fee or 0)
            
        is_valid_receipt = await _validate_receipt_with_gemini(proof_url, payment_method, expected_amount=expected_fee)

        if not is_valid_receipt:
            # Encode URL manually for redirect since we can't use complex URL building easily
            request.session["flash_error"] = "Invalid Receipt Detected: Our AI could not verify the Reference Number or Amount. Please ensure the screenshot is clear."
            return RedirectResponse(url=f"/bookings/step/payment/{booking.id}?error=invalid_receipt&method={payment_method}", status_code=303)
        
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



@router.post("/alacarte/payment/{booking_id}")
async def alacarte_manage_payment_submit(
    booking_id: int,
    request: Request,
    payment_method: str = Form("GCash"),
    proof_image: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):
    user = get_current_user_from_session(request, db)
    if not user:
        return {"success": False, "message": "Unauthorized"}
        
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.user_id != user.id:
        return {"success": False, "message": "Booking not found"}
        
    # File validation
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp", "application/pdf"]
    if proof_image.content_type not in allowed_types:
        return {"success": False, "message": "Invalid file type. Only JPG, PNG, WEBP, and PDF are allowed."}
        
    proof_image.file.seek(0, os.SEEK_END)
    if proof_image.file.tell() > 5 * 1024 * 1024:
        return {"success": False, "message": "File too large. Maximum size is 5MB."}
    proof_image.file.seek(0)
    
    import base64
    content_bytes = await proof_image.read()
    b64 = base64.b64encode(content_bytes).decode('utf-8')
    mime = proof_image.content_type or 'image/jpeg'
    proof_url = f"data:{mime};base64,{b64}"
        
    # AI Receipt Validation
    from ..services.payment_verification import payment_verification_service
    verify_results = payment_verification_service.check_for_fraud(db, booking, proof_url)
    
    if verify_results["confidence"] < 40:
        flags = verify_results.get("flags", [])
        error_detail = flags[0] if flags else "The uploaded image does not appear to be a valid receipt for the required amount."
        return {"success": False, "message": f"{error_detail}"}
        
    # Save extracted details
    extracted_ref = verify_results.get("extracted_data", {}).get("reference_no")
    extracted_hash = payment_verification_service.get_image_hash(proof_url)
    
    booking.payment_proof_url = proof_url
    
    if extracted_ref: booking.payment_reference = extracted_ref
    booking.proof_image_hash = extracted_hash
    
    booking.payment_proof_url = proof_url
    booking.payment_method = payment_method
    booking.payment_status = "proof_submitted"
    if booking.status in ['draft', 'pending_payment', 'awaiting_payment']:
        booking.status = "pending"
        
    # History
    history = models.BookingHistory(
        booking_id=booking.id,
        status="pending",
        notes=f"Ala Carte payment proof submitted via {payment_method}. Awaiting caterer verification."
    )
    db.add(history)
    db.commit()
    
    # Notify
    from ..services.notification import NotificationService
    import asyncio
    asyncio.create_task(NotificationService.notify_payment_received(db, booking, float(booking.total_amount or 0), "Payment"))
    
    return {"success": True}


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

    import base64
    content_bytes = await payment_proof.read()
    b64 = base64.b64encode(content_bytes).decode('utf-8')
    mime = payment_proof.content_type or 'image/jpeg'
    proof_url = f"data:{mime};base64,{b64}"
        
    # --- AI RECEIPT VALIDATION (GEMINI / OCR) ---
    expected_fee = float(booking.reservation_fee or 0)
    
    # Temporarily modify booking for validation
    original_amount = booking.total_amount
    original_method = booking.payment_method
    booking.total_amount = expected_fee
    booking.payment_method = payment_method
    
    verify_results = await payment_verification_service.check_for_fraud(db, booking, proof_url)
    
    # Revert
    booking.total_amount = original_amount
    booking.payment_method = original_method

    if verify_results["confidence"] < 40:
        import urllib.parse
        encoded_method = urllib.parse.quote(payment_method)
        flags = verify_results.get("flags", [])
        error_detail = flags[0] if flags else "Amount did not match or receipt is illegible."
        error_msg = urllib.parse.quote(f"Invalid Receipt Detected: {error_detail}")
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?validation_error={error_msg}&method={encoded_method}&open_reupload=1", status_code=303)

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
            
        import base64
        content_bytes = await payment_proof.read()
        b64 = base64.b64encode(content_bytes).decode('utf-8')
        mime = payment_proof.content_type or 'image/jpeg'
        proof_url = f"data:{mime};base64,{b64}"
            
        # --- AI RECEIPT VALIDATION ---
        original_amount = booking.total_amount
        original_method = booking.payment_method
        booking.total_amount = outstanding_balance
        booking.payment_method = payment_method
        
        verify_results = await payment_verification_service.check_for_fraud(db, booking, proof_url)
        
        # Revert
        booking.total_amount = original_amount
        booking.payment_method = original_method
        
        if verify_results["confidence"] < 40:
            import urllib.parse
            flags = verify_results.get("flags", [])
            error_detail = flags[0] if flags else "Amount did not match or receipt is illegible."
            error_msg = urllib.parse.quote(f"Invalid Receipt Detected: {error_detail}")
            return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?error_msg={error_msg}", status_code=303)
            
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

@router.post("/{booking_id}/messages")
async def send_booking_message(
    booking_id: int,
    request: Request,
    message: str = Form(None),
    attachment: UploadFile = File(None),
    db: Session = Depends(database.get_db)
):
    user = get_current_user_from_session(request, db)
    if not user:
        return JSONResponse({"success": False, "message": "Unauthorized"}, status_code=401)
        
    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        return JSONResponse({"success": False, "message": "Booking not found"}, status_code=404)
        
    if user.id != booking.user_id and user.id != booking.caterer.user_id:
        return JSONResponse({"success": False, "message": "Forbidden"}, status_code=403)
        
    if not message and not attachment:
        return JSONResponse({"success": False, "message": "Empty message"}, status_code=400)
        
    attachment_url = None
    if attachment and attachment.filename:
        import base64
        content_bytes = await attachment.read()
        b64 = base64.b64encode(content_bytes).decode('utf-8')
        mime = attachment.content_type or 'image/jpeg'
        attachment_url = f"data:{mime};base64,{b64}"
        
    new_msg = models.BookingMessage(
        booking_id=booking_id,
        sender_id=user.id,
        message=message,
        attachment_url=attachment_url
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    
    receiver_id = booking.caterer.user_id if user.id == booking.user_id else booking.user_id
    from ..services.realtime import manager
    import asyncio
    asyncio.create_task(manager.broadcast_to_user(receiver_id, {
        "type": "new_booking_message",
        "booking_id": booking_id,
        "sender_id": user.id,
        "message": new_msg.message,
        "attachment_url": new_msg.attachment_url,
        "created_at": new_msg.created_at.isoformat()
    }))
    
    return RedirectResponse(url=request.headers.get("referer", f"/customer/bookings/manage/{booking_id}"), status_code=303)
