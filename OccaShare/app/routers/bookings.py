from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from ..core.templates import templates
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional
from datetime import date, time, datetime, timedelta
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
from ..services.booking_validator import BookingValidator
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

def save_upload_file(upload_file: UploadFile, folder: str = "general") -> str:
    from app.services.storage import upload_file_to_cloudinary
    content_bytes = upload_file.file.read()
    url = upload_file_to_cloudinary(content_bytes, folder=folder)
    return url or ""


def get_package_grouped_inclusions(package) -> dict:
    """Group package inclusions dynamically into Food & Beverages, Services, and Equipment."""
    grouped = {
        'food': [],
        'services': [],
        'equipment': []
    }
    if not package:
        return grouped

    seen_names = {'food': set(), 'services': set(), 'equipment': set()}

    def add_item(bucket: str, name: str, quantity: str = "", description: str = ""):
        name_clean = (name or "").strip()
        if not name_clean:
            return
        name_key = name_clean.lower()
        if name_key in seen_names[bucket]:
            return
        seen_names[bucket].add(name_key)
        grouped[bucket].append({
            'name': name_clean,
            'quantity': (str(quantity) if quantity is not None else "").strip(),
            'description': (str(description) if description is not None else "").strip()
        })

    # 1. Parse package.inclusions JSON / dict / list
    raw = getattr(package, 'inclusions', None)
    if raw:
        if isinstance(raw, str):
            try:
                import json
                raw = json.loads(raw)
            except Exception:
                raw = [i.strip() for i in raw.split(',') if i.strip()]

        if isinstance(raw, list):
            for item in raw:
                if not item:
                    continue
                if isinstance(item, str):
                    add_item('food', item)
                elif isinstance(item, dict):
                    name = item.get('name') or ''
                    qty = item.get('quantity') or item.get('qty') or ''
                    desc = item.get('description') or item.get('details') or item.get('notes') or ''
                    cat = (item.get('category') or '').strip().lower()

                    if any(k in cat for k in ['service', 'staff', 'coordination', 'waiter', 'host', 'crew', 'setup', 'cleanup']):
                        add_item('services', name, qty, desc)
                    elif any(k in cat for k in ['equipment', 'rental', 'furniture', 'table', 'chair', 'tent', 'utensil', 'chafing', 'sound', 'light']):
                        add_item('equipment', name, qty, desc)
                    else:
                        add_item('food', name, qty, desc)
        elif isinstance(raw, dict):
            for k, v in raw.items():
                if v:
                    add_item('equipment', k)

    # 2. Add linked package menu items (if not already listed)
    if hasattr(package, 'menu_items') and package.menu_items:
        for mi in package.menu_items:
            cat_lower = (mi.category or '').strip().lower()
            if any(k in cat_lower for k in ['rental', 'equipment', 'furniture']):
                add_item('equipment', mi.name, '', mi.description or '')
            elif any(k in cat_lower for k in ['service', 'staff', 'coordination']):
                add_item('services', mi.name, '', mi.description or '')
            else:
                add_item('food', mi.name, '', mi.description or '')

    # 3. Add linked services
    if hasattr(package, 'service_links') and package.service_links:
        for link in package.service_links:
            if link.service and not link.service.is_archived:
                qty_str = f"{link.quantity} staff" if link.quantity else ""
                add_item('services', link.service.name, qty_str, link.service.description or '')

    # 4. Add linked equipment
    if hasattr(package, 'equipment_links') and package.equipment_links:
        for link in package.equipment_links:
            if link.equipment and not link.equipment.is_archived:
                qty_str = f"{link.quantity} units" if link.quantity else ""
                add_item('equipment', link.equipment.name, qty_str, link.equipment.description or '')

    return grouped


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
async def alacarte_checkout_page(
    request: Request,
    caterer_id: str,
    items: str = "",
    booking_id: Optional[int] = None,
    verified: Optional[int] = None,
    db: Session = Depends(database.get_db)
):
    if caterer_id == "None" or not caterer_id.isdigit():
        return RedirectResponse(url="/customer/marketplace?error_msg=Invalid caterer selected.", status_code=303)
    caterer_id_int = int(caterer_id)
    caterer = db.query(models.CatererProfile).filter(models.CatererProfile.id == caterer_id_int).first()
    if not caterer or caterer.verification_status != 'Verified' or not caterer.user.is_verified:
        return RedirectResponse(url="/customer/marketplace?error_msg=This partner is not currently authorized to accept bookings.")
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/bookings/alacarte/checkout/{caterer_id}?items={items}")
    
    # Parse multiple IDs with type prefixes (m_ for MenuItem, e_ for Equipment, s_ for Service) and optional :quantity
    m_ids, e_ids, s_ids = [], [], []
    item_quantities = {}
    if items:
        for item_part in items.split(","):
            item_part = item_part.strip()
            if not item_part: continue
            qty = 1
            if ":" in item_part:
                id_str, qty_str = item_part.split(":", 1)
                try:
                    qty = max(1, int(qty_str))
                except (ValueError, TypeError):
                    qty = 1
            else:
                id_str = item_part

            if id_str.startswith('m_'):
                mid = int(id_str[2:])
                m_ids.append(mid)
                item_quantities[f"m_{mid}"] = qty
            elif id_str.startswith('e_'):
                eid = int(id_str[2:])
                e_ids.append(eid)
                item_quantities[f"e_{eid}"] = qty
            elif id_str.startswith('s_'):
                sid = int(id_str[2:])
                s_ids.append(sid)
                item_quantities[f"s_{sid}"] = qty
            elif id_str.isdigit():
                mid = int(id_str)
                m_ids.append(mid)
                item_quantities[f"m_{mid}"] = qty

    # Fallback to existing booking items if items query param was omitted (e.g. return from KYC)
    booking = db.query(models.Booking).get(booking_id) if booking_id else None
    if not (m_ids or e_ids or s_ids) and booking and booking.user_id == user.id:
        for b_item in (booking.selected_items or []):
            b_qty = int(b_item.quantity or 1)
            if b_item.menu_item_id:
                m_ids.append(b_item.menu_item_id)
                item_quantities[f"m_{b_item.menu_item_id}"] = b_qty
            elif b_item.equipment_id:
                e_ids.append(b_item.equipment_id)
                item_quantities[f"e_{b_item.equipment_id}"] = b_qty
            elif b_item.service_id:
                s_ids.append(b_item.service_id)
                item_quantities[f"s_{b_item.service_id}"] = b_qty
            
    menu_items = db.query(models.MenuItem).filter(
        models.MenuItem.id.in_(m_ids),
        models.MenuItem.available_for_order == True
    ).all() if m_ids else []
    
    equipment_items = db.query(models.Equipment).filter(
        models.Equipment.id.in_(e_ids),
        models.Equipment.is_archived == False,
        or_(
            func.lower(models.Equipment.status).in_(['available', 'published', 'active']),
            models.Equipment.status.is_(None)
        )
    ).all() if e_ids else []

    # Ensure all equipment items have a non-zero rental_price
    for eq in equipment_items:
        price_val = getattr(eq, 'rental_price', None)
        if not price_val or price_val == 0:
            price_val = getattr(eq, 'cost_value', 0.0) or getattr(eq, 'price', 0.0) or 0.0
        eq.rental_price = float(price_val)
    
    # Check if any e_ids were legacy equipment items stored in MenuItem
    found_e_ids = {eq.id for eq in equipment_items}
    missing_e_ids = [eid for eid in e_ids if eid not in found_e_ids]
    if missing_e_ids:
        legacy_eq = db.query(models.MenuItem).filter(
            models.MenuItem.id.in_(missing_e_ids),
            models.MenuItem.available_for_order == True
        ).all()
        for leg in legacy_eq:
            leg.rental_price = float(leg.price or 0.0)
            leg.unit_type = getattr(leg, 'pricing_unit', 'piece') or 'piece'
            leg.cost_value = float(leg.price or 0.0)
            leg.security_deposit_pct = 20.0
            leg.available_qty = getattr(leg, 'max_stock_quantity', 1) or 1
            equipment_items.append(leg)
    
    service_items = db.query(models.Service).filter(
        models.Service.id.in_(s_ids),
        models.Service.is_archived == False,
        or_(
            func.lower(models.Service.status).in_(['available', 'published', 'active']),
            models.Service.status.is_(None)
        )
    ).all() if s_ids else []
    
    if not caterer or (not menu_items and not equipment_items and not service_items):
        return RedirectResponse(url="/marketplace", status_code=303)

    # Pre-calculate base total on server
    server_base_total = 0.0
    for mi in menu_items:
        mi.selected_qty = item_quantities.get(f"m_{mi.id}", 1)
        server_base_total += float(mi.price or 0.0) * mi.selected_qty
    for eq in equipment_items:
        eq.selected_qty = item_quantities.get(f"e_{eq.id}", 1)
        server_base_total += float(eq.rental_price or 0.0) * eq.selected_qty
    for si in service_items:
        si.selected_qty = item_quantities.get(f"s_{si.id}", 1)
        server_base_total += float(si.selling_price or 0.0) * si.selected_qty
        
    # Verification Matrix:
    # Menu only -> No verification required
    # Equipment Rental or Event Service -> Verification required if user not verified
    has_equipment = len(equipment_items) > 0
    has_services = len(service_items) > 0
    is_user_verified = bool(user and user.is_verified and user.is_kyc_complete)
    requires_kyc = (has_equipment or has_services) and not is_user_verified
        
    if not booking and booking_id:
        booking = db.query(models.Booking).get(booking_id)
    
    return templates.TemplateResponse("customer/booking_wizard/alacarte_checkout.html", {
        "request": request,
        "user": user,
        "caterer": caterer,
        "menu_items": menu_items,
        "equipment_items": equipment_items,
        "service_items": service_items,
        "items_raw": items,
        "item_quantities": item_quantities,
        "server_base_total": server_base_total,
        "booking": booking,
        "requires_kyc": requires_kyc,
        "is_user_verified": is_user_verified,
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
    booking_id: Optional[int] = Form(None),
    db: Session = Depends(database.get_db)
):
    user = get_current_user_from_session(request, db)
    if not user: return {"success": False, "message": "Unauthorized"}
    
    try:
        event_date_obj = date.fromisoformat(delivery_date)
        event_time_obj = datetime.strptime(delivery_time, "%H:%M").time()
        
        # Validate Caterer Availability (Single Source of Truth)
        from app.services.availability_service import AvailabilityService
        avail_check = AvailabilityService.check_caterer_availability(
            db=db,
            caterer_id=caterer_id,
            event_date=event_date_obj,
            event_time=event_time_obj,
            exclude_booking_id=booking_id
        )
        if not avail_check["available"]:
            return {"success": False, "message": avail_check["message"]}

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

        downpayment_amt = round(total_amount * 0.5, 2) if (is_rental and not has_food) else total_amount
        payment_plan_val = 'downpayment' if (is_rental and not has_food) else 'full'

        # Check for existing draft booking to update or create new
        new_booking = db.query(models.Booking).get(booking_id) if booking_id else None
        if new_booking and new_booking.user_id == user.id:
            new_booking.event_name = event_name
            new_booking.event_type = event_type
            new_booking.event_date = event_date_obj
            new_booking.event_time = event_time_obj
            new_booking.venue_address = address
            new_booking.guest_count = quantity
            new_booking.total_amount = total_amount
            new_booking.total_price = total_amount
            new_booking.reservation_fee = downpayment_amt
            new_booking.payment_plan = payment_plan_val
            new_booking.document_type = document_type
            new_booking.custom_requirements = {
                "recipient_name": full_name,
                "recipient_contact": contact_number
            }
            # Clear existing items to re-insert fresh
            db.query(models.BookingMenuItem).filter(models.BookingMenuItem.booking_id == new_booking.id).delete()
        else:
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
                reservation_fee=downpayment_amt,
                payment_plan=payment_plan_val,
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
                    if not e_item:
                        e_item = db.query(models.MenuItem).get(int(item['id']))
                        actual_price = float(getattr(e_item, 'price', 0.0) or 0.0) if e_item else 0.0
                    else:
                        actual_price = float(getattr(e_item, 'rental_price', 0.0) or getattr(e_item, 'cost_value', 0.0) or getattr(e_item, 'price', 0.0) or 0.0)
                    
                    if e_item:
                        # Server-side date availability check to prevent overbooking
                        total_inv = int(getattr(e_item, 'available_qty', 1) or 1)
                        res_qty = 0
                        active_b_list = db.query(models.Booking).filter(
                            models.Booking.caterer_id == caterer_id,
                            or_(
                                func.lower(models.Booking.status).notin_(['cancelled', 'rejected', 'declined', 'archived']),
                                models.Booking.status.is_(None)
                            ),
                            models.Booking.id != new_booking.id,
                            models.Booking.event_date.between(event_date_obj - timedelta(days=1), event_date_obj + timedelta(days=1))
                        ).all()
                        for ab in active_b_list:
                            for si in (ab.selected_items or []):
                                if si.equipment_id == e_item.id:
                                    res_qty += int(si.quantity or 1)
                            if ab.package_id:
                                try:
                                    pkg_equip = db.query(models.PackageEquipment).filter(
                                        models.PackageEquipment.package_id == ab.package_id,
                                        models.PackageEquipment.equipment_id == e_item.id
                                    ).all()
                                    for pe in pkg_equip:
                                        res_qty += int(pe.quantity or 1)
                                except Exception:
                                    pass
                        avail_units = max(0, total_inv - res_qty)
                        if qty > avail_units:
                            return {"success": False, "message": f"Only {avail_units} unit{'s are' if avail_units != 1 else ' is'} available for {e_item.name} on {event_date_obj}."}

                        db.add(models.BookingMenuItem(
                            booking_id=new_booking.id,
                            equipment_id=e_item.id if hasattr(e_item, 'rental_price') else None,
                            menu_item_id=e_item.id if not hasattr(e_item, 'rental_price') else None,
                            price=actual_price,
                            quantity=qty,
                            custom_name=e_item.name
                        ))
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
            for item_part in items.split(","):
                item_part = item_part.strip()
                if not item_part: continue
                qty = 1
                if ":" in item_part:
                    id_str, qty_str = item_part.split(":", 1)
                    try:
                        qty = max(1, int(qty_str))
                    except (ValueError, TypeError):
                        qty = 1
                else:
                    id_str = item_part

                if id_str.startswith('e_'):
                    e_item = db.query(models.Equipment).get(int(id_str[2:]))
                    if e_item:
                        actual_price = float(getattr(e_item, 'rental_price', 0.0) or getattr(e_item, 'cost_value', 0.0) or getattr(e_item, 'price', 0.0) or 0.0)
                        db.add(models.BookingMenuItem(booking_id=new_booking.id, equipment_id=e_item.id, price=actual_price, quantity=qty, custom_name=e_item.name))
                elif id_str.startswith('s_'):
                    s_item = db.query(models.Service).get(int(id_str[2:]))
                    if s_item:
                        item_qty = qty
                        if getattr(s_item, 'capacity_type', 'unit_based') == 'staff_based' and getattr(s_item, 'staff_to_pax_ratio', 0) > 0:
                            import math
                            item_qty = max(getattr(s_item, 'min_staff_required', 1), math.ceil(quantity / s_item.staff_to_pax_ratio))
                        db.add(models.BookingMenuItem(booking_id=new_booking.id, service_id=s_item.id, price=s_item.selling_price, quantity=item_qty))
                else:
                    item_id = int(id_str[2:]) if id_str.startswith('m_') else int(id_str)
                    m_item = db.query(models.MenuItem).get(item_id)
                    if m_item:
                        db.add(models.BookingMenuItem(booking_id=new_booking.id, menu_item_id=m_item.id, price=m_item.price, quantity=qty))

        db.flush()

        # Recalculate totals for draft
        draft_subtotal = 0.0
        for b_item in db.query(models.BookingMenuItem).filter(models.BookingMenuItem.booking_id == new_booking.id).all():
            draft_subtotal += float(b_item.price or 0.0) * int(b_item.quantity or 1)
        
        if is_rental and not has_food:
            new_booking.reservation_fee = round(draft_subtotal * 0.5, 2)
            new_booking.payment_plan = 'downpayment'
        else:
            new_booking.reservation_fee = draft_subtotal
            new_booking.payment_plan = 'full'
        new_booking.total_amount = draft_subtotal
        new_booking.total_price = draft_subtotal

        db.commit()
        return {"success": True, "booking_id": new_booking.id}
    except Exception as e:
        db.rollback()
        print(f"Error saving draft: {e}")
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
    db: Session = Depends(database.get_db)
):
    user = get_current_user_from_session(request, db)
    if not user:
        return {"success": False, "message": "Unauthorized"}

    # Check if transaction contains equipment or services
    has_equipment = False
    has_service = False
    if cart_data:
        try:
            cart_items_check = json.loads(cart_data)
            for itm in cart_items_check:
                t = itm.get('type', 'Menu')
                if t == 'Equipment': has_equipment = True
                elif t == 'Service': has_service = True
        except Exception:
            pass
    elif items:
        for item_part in items.split(","):
            item_part = item_part.strip()
            if not item_part: continue
            id_str = item_part.split(":", 1)[0]
            if id_str.startswith('e_'): has_equipment = True
            elif id_str.startswith('s_'): has_service = True

    # STRICT GATE: Verification Matrix Rule
    # Menu only -> No verification required
    # Equipment Rental or Event Services -> Identity Verification Required if not verified
    if (has_equipment or has_service) and not (user.is_verified and user.is_kyc_complete):
        return {
            "success": False,
            "message": "Identity Verification Required: Please complete identity verification before confirming equipment rental or event services."
        }
        
    try:
        # Save payment proof if uploaded
        proof_url = None
        if payment_proof and payment_proof.filename:

            from app.services.storage import upload_file_to_cloudinary
            content_bytes = payment_proof.file.read()
            proof_url = upload_file_to_cloudinary(content_bytes, folder="payment_receipts")

        # Spam Limit Validation (Flow B Rule 1)
        unpaid_spam_count = db.query(models.Booking).filter(
            models.Booking.user_id == user.id,
            models.Booking.status.in_(['draft', 'pending', 'pending_quotation', 'awaiting_caterer', 'awaiting_payment', 'pending_payment']),
            models.Booking.id != (booking_id or 0)
        ).count()
        if unpaid_spam_count >= 2:
            return {"success": False, "message": "Spam Protection: You have 2 or more unpaid/pending bookings. Please complete them first."}

        # Validate Caterer Availability (Single Source of Truth)
        from app.services.availability_service import AvailabilityService
        avail_check = AvailabilityService.check_caterer_availability(
            db=db,
            caterer_id=caterer_id,
            event_date=delivery_date,
            event_time=delivery_time,
            exclude_booking_id=booking_id
        )
        if not avail_check["available"]:
            return {"success": False, "message": avail_check["message"]}
            
        booking = db.query(models.Booking).get(booking_id) if booking_id else None
        
        # CONTINUOUS REVALIDATION
        if booking:
            is_valid, error_msg = BookingValidator.validate_booking_state(db, booking, update_if_expired=True)
            if not is_valid:
                return {"success": False, "message": error_msg}

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
            for item_part in items.split(","):
                item_part = item_part.strip()
                if not item_part: continue
                id_str = item_part.split(":", 1)[0]
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

        # Check category to determine document type and payment plan first
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
            for item_part in items.split(","):
                item_part = item_part.strip()
                if not item_part: continue
                id_str = item_part.split(":", 1)[0]
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

        # Payment Logic: 50% Downpayment for Equipment Rentals
        if is_rental and not has_food:
            reservation_fee = round(total_amount * 0.5, 2)
            payment_plan = "downpayment"
        else:
            reservation_fee = total_amount
            payment_plan = "full"

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
                booking.total_price = total_amount
                booking.reservation_fee = reservation_fee
                booking.payment_plan = payment_plan
                booking.event_name = event_name
                booking.event_type = event_type
                booking.document_type = document_type
                if proof_url:
                    booking.payment_proof_url = proof_url
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
                payment_plan=payment_plan,
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
                    if not e_item:
                        e_item = db.query(models.MenuItem).get(int(item['id']))
                        actual_price = float(getattr(e_item, 'price', 0.0) or 0.0) if e_item else 0.0
                    else:
                        actual_price = float(getattr(e_item, 'rental_price', 0.0) or getattr(e_item, 'cost_value', 0.0) or getattr(e_item, 'price', 0.0) or 0.0)
                    
                    if e_item:
                        # Re-verify availability at submission to prevent race conditions / double booking
                        total_inv = int(getattr(e_item, 'available_qty', 1) or 1)
                        res_qty = 0
                        active_b_list = db.query(models.Booking).filter(
                            models.Booking.caterer_id == caterer_id,
                            or_(
                                func.lower(models.Booking.status).notin_(['cancelled', 'rejected', 'declined', 'archived']),
                                models.Booking.status.is_(None)
                            ),
                            models.Booking.id != booking.id,
                            models.Booking.event_date.between(event_date_obj - timedelta(days=1), event_date_obj + timedelta(days=1))
                        ).all()
                        for ab in active_b_list:
                            for si in (ab.selected_items or []):
                                if si.equipment_id == e_item.id:
                                    res_qty += int(si.quantity or 1)
                            if ab.package_id:
                                try:
                                    pkg_equip = db.query(models.PackageEquipment).filter(
                                        models.PackageEquipment.package_id == ab.package_id,
                                        models.PackageEquipment.equipment_id == e_item.id
                                    ).all()
                                    for pe in pkg_equip:
                                        res_qty += int(pe.quantity or 1)
                                except Exception:
                                    pass
                        avail_units = max(0, total_inv - res_qty)
                        item_qty = int(item.get('quantity', item.get('qty', 1)))
                        if item_qty > avail_units:
                            return {"success": False, "message": f"Only {avail_units} unit{'s are' if avail_units != 1 else ' is'} available for {e_item.name} on {event_date_obj}."}

                        booking_item = models.BookingMenuItem(
                            booking_id=booking.id,
                            equipment_id=e_item.id if hasattr(e_item, 'rental_price') else None,
                            menu_item_id=e_item.id if not hasattr(e_item, 'rental_price') else None,
                            price=actual_price,
                            quantity=item_qty,
                            custom_name=e_item.name,
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
            for item_part in items.split(","):
                item_part = item_part.strip()
                if not item_part: continue
                qty = 1
                if ":" in item_part:
                    id_str, qty_str = item_part.split(":", 1)
                    try:
                        qty = max(1, int(qty_str))
                    except (ValueError, TypeError):
                        qty = 1
                else:
                    id_str = item_part

                if id_str.startswith('e_'):
                    e_item = db.query(models.Equipment).get(int(id_str[2:]))
                    if e_item:
                        actual_price = float(getattr(e_item, 'rental_price', 0.0) or getattr(e_item, 'cost_value', 0.0) or getattr(e_item, 'price', 0.0) or 0.0)
                        db.add(models.BookingMenuItem(booking_id=booking.id, equipment_id=e_item.id, price=actual_price, quantity=qty, custom_name=e_item.name))
                elif id_str.startswith('s_'):
                    s_item = db.query(models.Service).get(int(id_str[2:]))
                    if s_item:
                        item_qty = qty
                        if getattr(s_item, 'capacity_type', 'unit_based') == 'staff_based' and getattr(s_item, 'staff_to_pax_ratio', 0) > 0:
                            import math
                            item_qty = max(getattr(s_item, 'min_staff_required', 1), math.ceil(quantity / s_item.staff_to_pax_ratio))
                        db.add(models.BookingMenuItem(booking_id=booking.id, service_id=s_item.id, price=s_item.selling_price, quantity=item_qty))
                else:
                    item_id = int(id_str[2:]) if id_str.startswith('m_') else int(id_str)
                    m_item = db.query(models.MenuItem).get(item_id)
                    if m_item:
                        db.add(models.BookingMenuItem(booking_id=booking.id, menu_item_id=m_item.id, price=m_item.price, quantity=qty))

        db.flush()

        # Recalculate totals server-side directly from DB models to guarantee 100% price integrity
        total_items_subtotal = 0.0
        total_security_deposit = 0.0
        for b_item in db.query(models.BookingMenuItem).filter(models.BookingMenuItem.booking_id == booking.id).all():
            total_items_subtotal += float(b_item.price or 0.0) * int(b_item.quantity or 1)
            if b_item.equipment_id:
                eq = db.query(models.Equipment).get(b_item.equipment_id)
                if eq and eq.cost_value and eq.security_deposit_pct:
                    deposit_rate = float(eq.security_deposit_pct) / 100.0
                    total_security_deposit += (float(eq.cost_value) * deposit_rate) * int(b_item.quantity or 1)

        server_delivery_fee = float(booking.travel_fee or 0.0)
        recalculated_total = round(total_items_subtotal + server_delivery_fee + total_security_deposit, 2)

        booking.total_amount = recalculated_total
        booking.total_price = recalculated_total
        if is_rental and not has_food:
            booking.reservation_fee = round(recalculated_total * 0.5, 2)
            booking.payment_plan = "downpayment"
        else:
            booking.reservation_fee = recalculated_total
            booking.payment_plan = "full"
        booking.security_deposit_amount = round(total_security_deposit, 2)

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
    
    force_new = request.query_params.get("force_new")
    
    if package_id and not force_new:
        existing_booking = db.query(models.Booking).filter(
            models.Booking.user_id == user.id,
            models.Booking.caterer_id == caterer_id,
            models.Booking.package_id == package_id,
            models.Booking.status.in_(['draft', 'pending_quotation', 'awaiting_caterer', 'pending_payment'])
        ).order_by(models.Booking.created_at.desc()).first()

        if existing_booking:
            if existing_booking.status == 'draft':
                request.session["booking_data"] = {
                    "caterer_id": caterer_id,
                    "package_id": package_id,
                    "user_id": user.id,
                    "booking_id": existing_booking.id
                }
                return RedirectResponse(url=f"/bookings/step/details/{existing_booking.id}", status_code=303)
            else:
                return RedirectResponse(
                    url=f"/customer/bookings/manage/{existing_booking.id}?msg=You+already+have+an+ongoing+booking+for+this+package.+To+create+another+one,+cancel+this+first+or+contact+support.", 
                    status_code=303
                )

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
        from app.services.storage import upload_file_to_cloudinary
        for file in reference_images:
            if file.filename and file.filename != '':
                content_bytes = file.file.read()
                c_url = upload_file_to_cloudinary(content_bytes, folder="gallery")
                if c_url:
                    image_urls.append(c_url)


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
    if booking.event_type in ["Ala Carte Order", "Equipment Rental", "Service Booking", "Mixed Order"] or not booking.package_id:
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
    # Requirement #14 & #15: Transaction History != Verified. Only successful KYC makes customer verified.
    if not (user.is_verified and user.is_kyc_complete):
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
    if not caterer:
        return RedirectResponse(url="/customer/marketplace", status_code=303)
    
    # Query all active packages for this caterer
    caterer_packages = db.query(models.CateringPackage).filter(
        models.CateringPackage.caterer_id == caterer.id,
        models.CateringPackage.is_active == True,
        models.CateringPackage.status == 'active'
    ).order_by(models.CateringPackage.price.asc()).all()

    package = None
    package_id = data.get("package_id")
    if package_id:
        package = db.query(models.CateringPackage).get(package_id)
    elif caterer_packages:
        package = caterer_packages[0]

    # Pre-map all caterer packages with their dynamic grouped inclusions for seamless instant UI switching
    packages_map = {}
    for p in caterer_packages:
        packages_map[str(p.id)] = {
            "id": p.id,
            "name": p.name,
            "event_type": p.service_type or "General Catering",
            "pricing_mode": p.pricing_mode or ('per_pax' if p.price_unit == 'per_guest' else 'fixed'),
            "price_per_head": float(p.price_per_head or p.price or 0),
            "price": float(p.price or p.price_per_head or 0),
            "price_unit": p.price_unit or 'per_guest',
            "additional_guest_price": float(p.additional_guest_price or 0),
            "min_guests": p.min_guests or caterer.min_pax or 10,
            "max_guests": p.max_guests or 1000,
            "service_duration": p.service_duration or 4,
            "booking_lead_time": p.booking_lead_time or caterer.booking_lead_time or 7,
            "grouped_inclusions": get_package_grouped_inclusions(p)
        }
    
    # All active items for this caterer (to allow swapping)
    all_menu_items = db.query(models.MenuItem).filter(
        models.MenuItem.caterer_id == caterer.id,
        models.MenuItem.is_archived == False,
        models.MenuItem.available_for_package == True
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

    grouped_inclusions = get_package_grouped_inclusions(package) if package else {"food": [], "services": [], "equipment": []}

    return templates.TemplateResponse("customer/booking_wizard/step_details.html", {
        "request": request,
        "booking_data": data,
        "booking": booking,
        "package": package,
        "caterer_packages": caterer_packages,
        "packages_map": packages_map,
        "grouped_inclusions": grouped_inclusions,
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
    package_id: Optional[str] = Form(None),
    booking_id: Optional[str] = Form(None),
    event_name: Optional[str] = Form(None),
    event_type: Optional[str] = Form(None),
    event_date: Optional[str] = Form(None),
    event_time: Optional[str] = Form(None),
    event_end_time: Optional[str] = Form(None),
    guest_count: Optional[str] = Form("0"),
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
    # ── DEBUG: print exactly what FastAPI parsed from the form ────────────────
    print(f"[StepDetails PARAMS] caterer_id={caterer_id!r}, event_date={event_date!r}, event_time={event_time!r}, event_name={event_name!r}, guest_count={guest_count!r}, package_id={package_id!r}, booking_id={booking_id!r}")
    # ─────────────────────────────────────────────────────────────────────────

    import logging
    logger = logging.getLogger(__name__)

    def _clean_str(val):
        if val is not None:
            return str(val).strip() or None
        return None

    # Safely parse IDs and numbers
    cleaned_pkg_str = _clean_str(package_id)
    package_id_int = int(cleaned_pkg_str) if cleaned_pkg_str and cleaned_pkg_str.isdigit() else None
    if not package_id_int:
        sess_data = request.session.get("booking_data", {})
        if isinstance(sess_data, dict):
            package_id_int = sess_data.get("package_id")

    cleaned_booking_str = _clean_str(booking_id)
    booking_id_int = int(cleaned_booking_str) if cleaned_booking_str and cleaned_booking_str.isdigit() else None

    # Safely parse guest count (stripping any formatting commas)
    cleaned_guest_str = (_clean_str(guest_count) or "0").replace(",", "")
    try:
        guest_count_int = int(cleaned_guest_str)
    except:
        guest_count_int = 0

    # Safely parse times and dates
    cleaned_end_time = _clean_str(event_end_time)
    event_end_time_parsed = None
    if cleaned_end_time:
        try:
            event_end_time_parsed = time.fromisoformat(cleaned_end_time)
        except Exception:
            pass

    cleaned_date_str = _clean_str(event_date)
    event_date_parsed = None
    if cleaned_date_str:
        # Try standard ISO first, then common date formats
        try:
            event_date_parsed = date.fromisoformat(cleaned_date_str)
        except Exception as _iso_err:
            print(f"[StepDetails] date.fromisoformat failed on {cleaned_date_str!r}: {_iso_err}, trying strptime...")
        if not event_date_parsed:
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    event_date_parsed = datetime.strptime(cleaned_date_str, fmt).date()
                    break
                except Exception:
                    pass

    cleaned_time_str = _clean_str(event_time)
    event_time_parsed = None
    if cleaned_time_str:
        try:
            parts = cleaned_time_str.split(':')
            if len(parts) >= 2:
                event_time_parsed = time(int(parts[0]), int(parts[1]))
        except Exception:
            pass

    print(f"[StepDetails PARSED] date={cleaned_date_str!r} -> {event_date_parsed}, time={cleaned_time_str!r} -> {event_time_parsed}, pkg={package_id_int}, booking={booking_id_int}")

    package = db.query(models.CateringPackage).get(package_id_int) if package_id_int else None

    event_name_clean = _clean_str(event_name) or ""
    event_type_clean = _clean_str(event_type) or ""

    if not event_type_clean and package and package.service_type:
        event_type_clean = package.service_type

    final_event_type = event_type_clean
    if event_type_clean == "Other" and other_event_type and str(other_event_type).strip():
        final_event_type = str(other_event_type).strip()
    elif not final_event_type and package and package.service_type:
        final_event_type = package.service_type
    elif not final_event_type:
        final_event_type = "General Catering"

    user = get_current_user_from_session(request, db)
    redirect_base = f"/bookings/step/details/{booking_id_int}" if booking_id_int else "/bookings/step/details"
    if not user:
        print("[StepDetails REJECT] User not logged in, redirecting to /auth/login")
        return RedirectResponse(url=f"/auth/login?next={redirect_base}", status_code=303)

    if booking_id_int:
        existing_booking = db.query(models.Booking).get(booking_id_int)
        if existing_booking and existing_booking.status not in ["draft", "pending", "pending_quotation", "awaiting_caterer"]:
            print("[StepDetails REJECT] Booking is locked")
            return RedirectResponse(url=f"{redirect_base}?booking_error=Booking+is+already+locked+and+cannot+be+modified.", status_code=303)

    if not event_date_parsed:
        print(f"[StepDetails REJECT] event_date_parsed is None! raw event_date={event_date!r}, cleaned={cleaned_date_str!r}")
        return RedirectResponse(url=f"{redirect_base}?booking_error=err-date:Valid+event+date+is+required", status_code=303)
    if not event_time_parsed:
        print(f"[StepDetails REJECT] event_time_parsed is None! raw event_time={event_time!r}, cleaned={cleaned_time_str!r}")
        return RedirectResponse(url=f"{redirect_base}?booking_error=err-time:Valid+event+time+is+required", status_code=303)
    if not event_name_clean:
        print(f"[StepDetails REJECT] event_name_clean is empty! raw={event_name!r}")
        return RedirectResponse(url=f"{redirect_base}?booking_error=err-name:Event+name+is+required", status_code=303)
    if not final_event_type:
        print("[StepDetails REJECT] final_event_type is empty!")
        return RedirectResponse(url=f"{redirect_base}?booking_error=err-type:Event+type+is+required", status_code=303)

    # Construct venue address if missing from hidden field
    if not venue_address and province and city and barangay:
        venue_address = f"{barangay}, {city}, {province}"

    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer:
        print(f"[StepDetails REJECT] Caterer profile {caterer_id} not found")
        return RedirectResponse(url=f"/customer/marketplace", status_code=303)

    today = date.today()
    
    # 🚨 SINGLE SOURCE OF TRUTH: Caterer Availability Validation
    from app.services.availability_service import AvailabilityService
    avail_check = AvailabilityService.check_caterer_availability(
        db=db,
        caterer_id=caterer_id,
        event_date=event_date_parsed,
        event_time=event_time_parsed,
        exclude_booking_id=booking_id_int
    )
    if not avail_check["available"]:
        code = avail_check.get("code", "error")
        field = "err-time" if code in ["outside_hours", "slot_conflict"] else "err-date"
        msg = avail_check.get("message", "Selected date or time is not available.")
        print(f"[StepDetails REJECT] Availability rule failed: {code} - {msg}")
        return RedirectResponse(url=f"{redirect_base}?booking_error={field}:{msg.replace(' ', '+')}", status_code=303)

    # 🚨 VALIDATION 1.8: Unpaid Booking Spam Limit (Flow B Rule 1)
    unpaid_spam_count = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        models.Booking.status.in_(['draft', 'pending', 'pending_quotation', 'awaiting_caterer', 'awaiting_payment', 'pending_payment']),
        models.Booking.id != (booking_id_int or 0)
    ).count()

    if unpaid_spam_count >= 2:
        print(f"[StepDetails REJECT] Unpaid spam limit hit: {unpaid_spam_count} >= 2")
        return RedirectResponse(url=f"{redirect_base}?booking_error=Spam+Protection:+You+have+2+or+more+unpaid+or+pending+bookings.+Please+pay+the+downpayment+or+cancel+them+before+making+a+new+one.", status_code=303)

    # 🚨 VALIDATION 2: Anti-Spam / Duplicate Booking Check
    existing_duplicate = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        models.Booking.caterer_id == caterer_id,
        models.Booking.event_date == event_date_parsed,
        models.Booking.event_time == event_time_parsed,
        models.Booking.id != (booking_id_int or 0),
        models.Booking.status.notin_(['cancelled'])
    ).first()
    
    if existing_duplicate:
        print(f"[StepDetails REJECT] Existing duplicate booking found: {existing_duplicate.id}")
        return RedirectResponse(url=f"{redirect_base}?booking_error=You+already+have+a+booking+request+for+this+exact+schedule+and+caterer.", status_code=303)

    # 🚨 VALIDATION 4: Guest Count Bounds
    is_package = package_id_int is not None
    min_guests_required = caterer.min_pax or 50 if is_package else 1
    if package:
        min_guests_required = package.min_guests or caterer.min_pax or 50
        if package.max_guests and guest_count_int > package.max_guests:
            return RedirectResponse(url=f"{redirect_base}?booking_error=Guest+count+exceeds+the+package+maximum+capacity+of+{package.max_guests}.", status_code=303)

    if guest_count_int < min_guests_required:
        return RedirectResponse(url=f"{redirect_base}?booking_error=Guest+count+cannot+be+less+than+the+minimum+requirement+of+{min_guests_required}.", status_code=303)


    # 1.5. Capacity Check for Addon Services
    requested_services = []
    for serv_id in selected_service_addons:
        serv_item = db.query(models.Service).get(serv_id)
        if serv_item:
            qty = 1
            if getattr(serv_item, 'capacity_type', 'unit_based') == 'staff_based' and getattr(serv_item, 'staff_to_pax_ratio', 0) > 0:
                import math
                qty = max(getattr(serv_item, 'min_staff_required', 1), math.ceil(guest_count_int / serv_item.staff_to_pax_ratio))
            requested_services.append((serv_id, qty))
            
    from ..services.capacity_service import CapacityService
    is_capacity_valid, capacity_msg = CapacityService.validate_booking_capacity(db, caterer_id, event_date_parsed, event_time_parsed, event_end_time_parsed, requested_services, booking_id_int)
    if not is_capacity_valid:
        print(f"[StepDetails REJECT] Capacity check failed: {capacity_msg}")
        return RedirectResponse(url=f"{redirect_base}?booking_error={capacity_msg}", status_code=303)

    # 2. Create or Update Booking
    booking = None
    if booking_id_int:
        booking = db.query(models.Booking).get(booking_id_int)
    
    if booking and booking.user_id == user.id:
        # Prevent editing bookings for past event dates
        if booking.event_date and booking.event_date < date.today():
            return RedirectResponse(url=f"{redirect_base}?booking_error=Cannot+edit+past+bookings", status_code=303)

        # Update existing
        booking.package_id = package_id_int
        booking.event_name = event_name_clean
        booking.event_type = package.service_type if package and package.service_type else final_event_type
        booking.event_date = event_date_parsed
        booking.event_time = event_time_parsed
        booking.event_end_time = event_end_time_parsed
        booking.venue_address = venue_address
        booking.event_address = venue_address
        booking.guest_count = guest_count_int
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
            package_id=package_id_int,
            event_name=event_name_clean,
            event_type=package.service_type if package and package.service_type else final_event_type,
            event_date=event_date_parsed,
            event_time=event_time_parsed,
            event_end_time=event_end_time_parsed,
            venue_address=venue_address,
            event_address=venue_address,
            guest_count=guest_count_int,
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
                booking.travel_fee = caterer.base_delivery_fee or 0.0
    else:
        booking.travel_fee_status = "pending"

    db.commit()
    db.refresh(booking)

    # 3. Save Selected Items and Validate Rules
    package = db.query(models.CateringPackage).get(package_id_int) if package_id_int else None
    
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
    if not selected_items and package and package.menu_items:
        default_pkg_items = [mi.id for mi in package.menu_items if getattr(mi, 'category', '') not in ["Rentals", "Services"] and not getattr(mi, 'is_addon', False)]
        all_items = default_pkg_items + selected_addons

    for item_id in all_items:
        menu_item = db.query(models.MenuItem).get(item_id)
        if menu_item:
            item_price = menu_item.addon_price if menu_item.is_addon else (getattr(menu_item, 'upgrade_fee', 0.0) or 0.0)
            booking_item = models.BookingMenuItem(
                booking_id=booking.id,
                menu_item_id=item_id,
                is_add_on=menu_item.is_addon,
                price=item_price,
                quantity=guest_count_int
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
                qty = max(getattr(serv_item, 'min_staff_required', 1), math.ceil(guest_count_int / serv_item.staff_to_pax_ratio))
                
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
        "package_id": package_id_int
    }

    # Requirement #14 & #15: Transaction History != Verified. Only successful KYC makes customer verified.
    if user.is_verified and user.is_kyc_complete:
        # Mark as verified immediately if they are already verified
        booking.ocr_verified = True
        booking.liveness_verified = True
        db.commit()
        print(f"[StepDetails SUCCESS] Booking #{booking.id} created/updated for verified user! Redirecting to Quotation Review.")
        return RedirectResponse(url=f"/bookings/step/quotation/{booking.id}", status_code=303)
        
    print(f"[StepDetails SUCCESS] Booking #{booking.id} created/updated! Redirecting to KYC Verification.")
    return RedirectResponse(url=f"/bookings/step/kyc/{booking.id}", status_code=303)

# Phase 2: Identity Verification
@router.get("/step/kyc/{booking_id}", response_class=HTMLResponse)
async def step_kyc_page(booking_id: int, request: Request, return_to: Optional[str] = None, db: Session = Depends(database.get_db)):
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/bookings/step/kyc/{booking_id}")
        
    booking = db.query(models.Booking).get(booking_id)
    if not booking: raise HTTPException(status_code=404)

    # Dynamic Routing for Fast-Track (only when not explicitly directed to KYC)
    if booking.transaction_type == 'fast_track' and not return_to:
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
        "return_to": return_to,
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
    has_equipment = any(item.equipment_id is not None for item in booking.selected_items)
    has_services = any(item.service_id is not None for item in booking.selected_items)
    if booking.transaction_type != 'fast_track' or has_equipment or has_services:
        if not (user.is_verified and user.is_kyc_complete):
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
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("[GEMINI VALIDATION] No Gemini key set, passing to caterer manual review.")
        return True

    import httpx, base64, json, re
    from app.services.payment_verification import payment_verification_service

    # 1. Load actual image bytes from Cloudinary URL, local file, or Base64
    try:
        raw_bytes = payment_verification_service._load_image_bytes(b64_string)
        encoded_string = base64.b64encode(raw_bytes).decode('utf-8')
    except Exception as load_err:
        print(f"[GEMINI VALIDATION ERROR] Could not load image bytes: {load_err}")
        return True # Pass to manual caterer review if image cannot be read locally

    # Auto-detect mimeType from magic bytes to avoid Gemini rejecting PNG uploads sent as jpeg
    mime_type = "image/jpeg"
    if raw_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        mime_type = "image/png"
    elif raw_bytes[:4] == b'RIFF' and raw_bytes[8:12] == b'WEBP':
        mime_type = "image/webp"
    print(f"[GEMINI VALIDATION] Detected mimeType: {mime_type}")

    # 2. Call Gemini Vision API with raw base64 image data
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    prompt = (
        f"You are verifying a Philippine mobile payment receipt for OccaServe catering marketplace. "
        f"The customer claims this is a {payment_method} payment screenshot. "
        "Your job is to check if this is a legitimate payment confirmation image.\n\n"
        "IMPORTANT RULES:\n"
        "1. Set is_valid: TRUE for any of these: GCash Express Send / Send Money confirmation, "
        "Maya payment confirmation, bank transfer receipt, deposit slip, BDO/BPI/Metrobank/UnionBank "
        "online transfer confirmation, or any Philippine e-wallet transaction success screen.\n"
        "2. GCash receipts often show masked names like 'MI••Y MA•••T J.' or '+63 9••••1719' — "
        "this is NORMAL and is a valid GCash receipt. Do NOT fail these.\n"
        "3. Set is_valid: FALSE ONLY for: selfie photos, food photos, random screenshots unrelated to payments, "
        "blank images, or obviously fake/edited receipts.\n"
        "4. Do NOT fail a receipt just because names are masked, amounts seem small, "
        "or you cannot read every field clearly.\n"
        "5. If there is ANY doubt and the image looks like a payment receipt, set is_valid: TRUE.\n\n"
        'Respond ONLY with a valid JSON: {"is_valid": true_or_false, "reason": "brief explanation"}'
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}, {"inlineData": {"mimeType": mime_type, "data": encoded_string}}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }

    headers = {"Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
            print(f"[GEMINI VALIDATION] Trying model: {model}")
            try:
                res = await client.post(url, json=payload, headers=headers, timeout=30.0)
                if res.status_code == 200:
                    text_resp = res.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '{}').strip()
                    if text_resp.startswith("```json"): text_resp = text_resp[7:]
                    if text_resp.startswith("```"): text_resp = text_resp[3:]
                    if text_resp.endswith("```"): text_resp = text_resp[:-3]

                    try:
                        parsed = json.loads(text_resp.strip())
                        is_valid = parsed.get("is_valid", True)  # Default True: pass to manual review if unclear
                        print(f"[GEMINI VALIDATION] Model '{model}' Result: {is_valid}, Reason: {parsed.get('reason')}")
                        return is_valid
                    except (json.JSONDecodeError, ValueError) as parse_err:
                        print(f"[GEMINI VALIDATION WARNING] Could not parse JSON from model '{model}': {parse_err}. Defaulting to True.")
                        return True  # If we cannot parse the response, pass to manual caterer review
                else:
                    print(f"[GEMINI VALIDATION WARNING] Model {model} status code: {res.status_code}")
            except Exception as err:
                print(f"[GEMINI VALIDATION WARNING] Model {model} request failed: {err}")

    # Fallback to True if Gemini API is rate-limited/unavailable so caterers can manually verify proof
    print("[GEMINI VALIDATION WARNING] AI service temporary fallback: Passing to caterer manual verification.")
    return True

# Phase 4: Payment Confirmation
@router.get("/step/payment/{booking_id}", response_class=HTMLResponse)
async def step_payment_page(booking_id: str, request: Request, db: Session = Depends(database.get_db)):
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/bookings/step/payment/{booking_id}")
        
    try:
        booking_id_int = int(booking_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid booking ID")
        
    booking = db.query(models.Booking).get(booking_id_int)
    if not booking: raise HTTPException(status_code=404)

    # CONTINUOUS REVALIDATION: Block loading payment page if expired
    is_valid, error_msg = BookingValidator.validate_booking_state(db, booking, update_if_expired=True)
    if not is_valid:
        return RedirectResponse(url=f"/customer/bookings/manage/{booking_id_int}?error_msg={error_msg}", status_code=303)

    # STRICT GATE: Ensure user is verified before payment (Skip for fast-track unless it's equipment rental or service)
    has_equipment = any(item.equipment_id is not None for item in booking.selected_items)
    has_services = any(item.service_id is not None for item in booking.selected_items)
    if booking.transaction_type != 'fast_track' or has_equipment or has_services:
        if not (user.is_verified and user.is_kyc_complete):
            return RedirectResponse(url=f"/bookings/step/kyc/{booking.id}?auth_needed=1", status_code=303)

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

    # CONTINUOUS REVALIDATION: Block submitting payment if expired
    is_valid, error_msg = BookingValidator.validate_booking_state(db, booking, update_if_expired=True)
    if not is_valid:
        # If ajax request: raise HTTP error, else redirect
        raise HTTPException(status_code=400, detail=error_msg)

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
            
        from app.services.storage import upload_file_to_cloudinary
        content_bytes = payment_proof.file.read()
        proof_url = upload_file_to_cloudinary(content_bytes, folder="payment_receipts")
        if not proof_url:
            raise HTTPException(status_code=500, detail="Failed to upload payment proof to Cloudinary.")

            
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
        
    # CONTINUOUS REVALIDATION
    is_valid, error_msg = BookingValidator.validate_booking_state(db, booking, update_if_expired=True)
    if not is_valid:
        return {"success": False, "message": error_msg}
        
    # File validation
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp", "application/pdf"]
    if proof_image.content_type not in allowed_types:
        return {"success": False, "message": "Invalid file type. Only JPG, PNG, WEBP, and PDF are allowed."}
        
    proof_image.file.seek(0, os.SEEK_END)
    if proof_image.file.tell() > 5 * 1024 * 1024:
        return {"success": False, "message": "File too large. Maximum size is 5MB."}
    proof_image.file.seek(0)
    
    from app.services.storage import upload_file_to_cloudinary
    content_bytes = await proof_image.read()
    proof_url = upload_file_to_cloudinary(content_bytes, folder="payment_receipts")
    if not proof_url:
        return {"success": False, "message": "Failed to upload payment proof to Cloudinary."}

        
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
        
    # CONTINUOUS REVALIDATION
    is_valid, error_msg = BookingValidator.validate_booking_state(db, booking, update_if_expired=True)
    if not is_valid:
        import urllib.parse
        encoded_error = urllib.parse.quote(error_msg)
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?error_msg={encoded_error}", status_code=303)

    if booking.payment_status not in ['reupload_requested']:
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?error_msg=No+re-upload+requested", status_code=303)

    if not payment_proof or not payment_proof.filename:
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?validation_error=Please+provide+an+image&open_reupload=1", status_code=303)

    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if payment_proof.content_type not in allowed_types:
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?validation_error=Invalid+file+type&open_reupload=1", status_code=303)

    from app.services.storage import upload_file_to_cloudinary
    content_bytes = await payment_proof.read()
    proof_url = upload_file_to_cloudinary(content_bytes, folder="payment_receipts")
    if not proof_url:
        import urllib.parse
        error_msg = urllib.parse.quote("Failed to upload proof to Cloudinary.")
        return RedirectResponse(url=f"/customer/bookings/manage/{booking.id}?validation_error={error_msg}&open_reupload=1", status_code=303)
        
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

    booking.payment_proof_url = proof_url
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
            
        from app.services.storage import upload_file_to_cloudinary
        content_bytes = await payment_proof.read()
        proof_url = upload_file_to_cloudinary(content_bytes, folder="payment_receipts")
        if not proof_url:
            raise HTTPException(status_code=500, detail="Failed to upload payment proof to Cloudinary.")

            
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

@router.get("/{booking_id}/messages")
async def get_booking_messages_universal(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db)
):
    user = get_current_user_from_session(request, db)
    if not user:
        return JSONResponse({"status": "error", "message": "Unauthorized"}, status_code=401)
        
    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        return JSONResponse({"status": "error", "message": "Booking not found"}, status_code=404)
        
    if user.id != booking.user_id and user.id != booking.caterer.user_id and user.role != 'admin':
        return JSONResponse({"status": "error", "message": "Forbidden"}, status_code=403)
        
    messages = []
    has_unread = False
    for msg in sorted(booking.messages, key=lambda x: x.id):
        if msg.sender_id != user.id and not msg.is_read:
            msg.is_read = True
            has_unread = True
        messages.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_name": f"{msg.sender.first_name or ''} {msg.sender.last_name or ''}".strip() if msg.sender else "User",
            "message": msg.message,
            "attachment_url": msg.attachment_url,
            "is_me": msg.sender_id == user.id,
            "is_read": msg.is_read,
            "created_at": msg.created_at.strftime('%b %d, %I:%M %p')
        })
    if has_unread:
        db.commit()
    return {"status": "success", "messages": messages}

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
        content_bytes = await attachment.read()
        if len(content_bytes) > 10 * 1024 * 1024:
            return JSONResponse({"success": False, "message": "Attachment file size exceeds 10MB limit."}, status_code=400)
            
        allowed_exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf', '.doc', '.docx')
        if not attachment.filename.lower().endswith(allowed_exts):
            return JSONResponse({"success": False, "message": "Invalid attachment format. Allowed: JPG, PNG, GIF, WEBP, PDF, DOC, DOCX."}, status_code=400)

        from app.services.storage import upload_file_to_cloudinary
        attachment_url = upload_file_to_cloudinary(content_bytes, folder="chat_attachments")

        
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

    # ── Persistent notification so receiver gets bell icon alert ──────────────
    _fname = (user.first_name or "").strip()
    _lname = (user.last_name or "").strip()
    sender_name = f"{_fname} {_lname}".strip() or user.email or "Someone"
    booking_ref = f"Booking #{booking_id}"
    is_sender_customer = user.id == booking.user_id
    notif_title = "New Consultation Message"
    notif_msg   = f"{sender_name} sent you a message about {booking_ref}."
    notif_link  = (
        f"/caterer/bookings" if is_sender_customer
        else f"/customer/bookings/manage/{booking_id}"
    )
    db.add(models.Notification(
        user_id=receiver_id,
        title=notif_title,
        message=notif_msg,
        type="info",
        link=notif_link,
        is_read=False,
    ))
    db.commit()

    # ── Real-time WebSocket push to receiver ──────────────────────────────────
    import asyncio
    asyncio.create_task(manager.broadcast_to_user(receiver_id, {
        "type": "new_booking_message",
        "booking_id": booking_id,
        "sender_id": user.id,
        "sender_name": sender_name,
        "message": new_msg.message,
        "attachment_url": new_msg.attachment_url,
        "created_at": new_msg.created_at.isoformat(),
        "notification_title": notif_title,
        "notification_body": notif_msg,
        "link": notif_link,
    }))
    
    is_ajax_or_fetch = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
        or "*/*" in request.headers.get("Accept", "")
        or request.headers.get("sec-fetch-dest") == "empty"
        or request.headers.get("sec-fetch-mode") in ["cors", "same-origin"]
    )
    if is_ajax_or_fetch:
        return JSONResponse({"success": True, "message": "Message sent", "data": {"id": new_msg.id, "message": new_msg.message, "attachment_url": new_msg.attachment_url, "created_at": new_msg.created_at.strftime('%b %d, %I:%M %p')}})
    return RedirectResponse(url=request.headers.get("referer", f"/customer/bookings/manage/{booking_id}"), status_code=303)
