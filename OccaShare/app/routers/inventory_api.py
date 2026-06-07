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
