import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db import database, models

router = APIRouter(prefix="/customer/api", tags=["customer_api"])

@router.post("/check-inventory")
async def check_inventory(request: Request, db: Session = Depends(database.get_db)):
    data = await request.json()
    caterer_id = data.get("caterer_id")
    event_date_str = data.get("date")
    event_time_str = data.get("time")
    cart_items = data.get("items", []) # List of {id: int, qty: int}

    if not caterer_id or not event_date_str or not cart_items:
        return {"status": "success", "message": "Incomplete data for check"}

    # Parse date
    try:
        event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
    except:
        return {"status": "success"}

    caterer = db.query(models.CatererProfile).filter(models.CatererProfile.id == caterer_id).first()
    if not caterer:
        return {"status": "error", "message": "Caterer not found"}

    turnover_hours = caterer.equipment_turnover_hours or 24

    # Extract all item IDs requested
    item_ids = [int(i["id"]) for i in cart_items if i.get("id")]
    if not item_ids:
        return {"status": "success"}

    menu_items_db = db.query(models.MenuItem).filter(models.MenuItem.id.in_(item_ids)).all()
    menu_item_map = {mi.id: mi for mi in menu_items_db}

    # Gather required quantities for items that have max_stock_quantity
    req_qty_map = {}
    for item in cart_items:
        i_id = int(item["id"])
        qty = int(item["qty"])
        db_item = menu_item_map.get(i_id)
        if db_item and db_item.max_stock_quantity is not None:
            req_qty_map[i_id] = req_qty_map.get(i_id, 0) + qty

    if not req_qty_map:
        return {"status": "success", "message": "No limited stock items"}

    # Find overlapping bookings
    # For simplicity, we check bookings on the exact same date and the date before (if turnover > 0)
    overlapping_bookings = db.query(models.Booking).filter(
        models.Booking.caterer_id == caterer_id,
        models.Booking.status.in_(["Approved", "Pending", "Preparing", "Out for Delivery"]),
        models.Booking.event_date.between(event_date - timedelta(days=1), event_date + timedelta(days=1))
    ).all()

    # Calculate booked stock on that date
    booked_qty_map = {i_id: 0 for i_id in req_qty_map.keys()}
    
    for b in overlapping_bookings:
        if not b.cart_items:
            continue
            
        # Parse cart items if it's string (JSON)
        items = b.cart_items
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except:
                items = []

        for b_item in items:
            b_id = int(b_item.get("id", 0))
            if b_id in booked_qty_map:
                booked_qty_map[b_id] += int(b_item.get("qty", 0))

    # Check for conflicts
    conflicts = []
    for i_id, req_qty in req_qty_map.items():
        db_item = menu_item_map[i_id]
        total_booked = booked_qty_map[i_id]
        available = db_item.max_stock_quantity - total_booked
        
        if req_qty > available:
            conflicts.append({
                "name": db_item.name,
                "requested": req_qty,
                "available": available if available > 0 else 0
            })

    if conflicts:
        conflict_msgs = [f"Not enough {c['name']} (Available: {c['available']})" for c in conflicts]
        return {
            "status": "error",
            "message": "Inventory conflict detected!",
            "conflicts": conflicts,
            "error_text": " + ".join(conflict_msgs) + f". Please consider the {turnover_hours}-hour cleaning/turnover buffer time for other bookings."
        }

    return {"status": "success", "message": "Inventory available"}


@router.api_route("/check-equipment-availability", methods=["GET", "POST"])
async def check_equipment_availability(
    request: Request,
    db: Session = Depends(database.get_db)
):
    if request.method == "POST":
        try:
            data = await request.json()
        except Exception:
            data = {}
    else:
        data = dict(request.query_params)
        
    equipment_id = data.get("equipment_id")
    date_str = data.get("date") or data.get("event_date")
    try:
        requested_qty = int(data.get("requested_qty", 1) or 1)
    except (ValueError, TypeError):
        requested_qty = 1

    if not equipment_id or not date_str:
        return {"status": "error", "available": False, "message": "Equipment ID and date are required"}

    import traceback
    try:
        try:
            eq_id = int(str(equipment_id).replace("eq_", ""))
        except (ValueError, TypeError):
            return {"status": "error", "available": False, "message": "Invalid equipment ID"}

        try:
            event_date = datetime.strptime(str(date_str).strip(), "%Y-%m-%d").date()
        except Exception:
            return {"status": "error", "available": False, "message": "Invalid date format (use YYYY-MM-DD)"}

        equipment = db.query(models.Equipment).filter(models.Equipment.id == eq_id).first()
        legacy_item = None
        if not equipment:
            legacy_item = db.query(models.MenuItem).filter(models.MenuItem.id == eq_id).first()
            if not legacy_item:
                return {"status": "error", "available": False, "message": "Equipment item not found"}

        caterer_id = equipment.caterer_id if equipment else legacy_item.caterer_id
        total_inventory = int(equipment.available_qty if equipment else (legacy_item.available_qty or legacy_item.max_stock_quantity or 1))

        # Active bookings on this event date (or within turnover buffer)
        # Exclude cancelled, rejected, and declined bookings
        inactive_statuses = ['cancelled', 'rejected', 'declined', 'archived']

        bookings = db.query(models.Booking).filter(
            models.Booking.caterer_id == caterer_id,
            models.Booking.event_date.between(event_date - timedelta(days=1), event_date + timedelta(days=1))
        ).all()

        # Filter active in python
        bookings = [
            b for b in bookings 
            if not b.status or str(b.status).lower().strip() not in inactive_statuses
        ]

        reserved_qty = 0
        for b in bookings:
            # Check selected_items (BookingMenuItem)
            if b.selected_items:
                for item in b.selected_items:
                    if item.equipment_id == eq_id:
                        reserved_qty += int(item.quantity or 1)
            
            # Check package equipment inclusions if booking has a package
            if b.package_id:
                try:
                    pkg_equip = db.query(models.PackageEquipment).filter(
                        models.PackageEquipment.package_id == b.package_id,
                        models.PackageEquipment.equipment_id == eq_id
                    ).all()
                    for pe in pkg_equip:
                        reserved_qty += int(pe.quantity or 1)
                except Exception:
                    pass
                    
            # Check cart_items json if present
            raw_cart = getattr(b, 'cart_items', None)
            if not raw_cart and getattr(b, 'custom_requirements', None) and isinstance(b.custom_requirements, dict):
                raw_cart = b.custom_requirements.get('cart_data') or b.custom_requirements.get('cart_items')
            
            if raw_cart:
                items = raw_cart
                if isinstance(items, str):
                    try:
                        items = json.loads(items)
                    except Exception:
                        items = []
                if isinstance(items, list):
                    for c_item in items:
                        if isinstance(c_item, dict):
                            c_id = str(c_item.get("id", "")).replace("eq_", "").replace("e_", "")
                            if c_id == str(eq_id):
                                reserved_qty += int(c_item.get("qty", c_item.get("quantity", 1)))

        available_qty = max(0, total_inventory - reserved_qty)
        is_available = requested_qty <= available_qty

        item_name = equipment.name if equipment else legacy_item.name
        rental_price = float(equipment.rental_price if equipment else (legacy_item.price or 0.0))
        unit = equipment.unit_type if equipment else getattr(legacy_item, 'pricing_unit', 'piece')
        security_deposit_pct = float(equipment.security_deposit_pct if equipment else 20.0)

        if not is_available:
            msg = f"Only {available_qty} units are available for the selected date." if available_qty > 0 else "No units are available for the selected date."
            return {
                "status": "error",
                "available": False,
                "name": item_name,
                "rental_price": rental_price,
                "unit": unit,
                "security_deposit_pct": security_deposit_pct,
                "total_inventory": total_inventory,
                "reserved_qty": reserved_qty,
                "available_qty": available_qty,
                "requested_qty": requested_qty,
                "message": msg
            }

        return {
            "status": "success",
            "available": True,
            "caterer_id": caterer_id,
            "item_status": getattr(equipment, 'status', None),
            "is_archived": getattr(equipment, 'is_archived', False),
            "is_hidden": getattr(equipment, 'is_hidden', False),
            "usage_type": getattr(equipment, 'usage_type', 'both'),
            "name": item_name,
            "rental_price": rental_price,
            "unit": unit,
            "security_deposit_pct": security_deposit_pct,
            "total_inventory": total_inventory,
            "reserved_qty": reserved_qty,
            "available_qty": available_qty,
            "requested_qty": requested_qty,
            "message": f"{available_qty} units available"
        }
    except Exception as err:
        return {
            "status": "error",
            "available": False,
            "message": f"Server error checking availability: {str(err)}",
            "traceback": traceback.format_exc()
        }
