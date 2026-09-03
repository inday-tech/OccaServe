import re

with open('app/routers/caterer_dashboard.py', 'r', encoding='utf-8') as f:
    backend_code = f.read()

new_routes = """
@router.post("/api/bookings/{booking_id}/edit")
async def edit_booking_details(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    caterer = db.query(models.CatererProfile).filter(models.CatererProfile.user_id == user.id).first()
    if not caterer:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.caterer_id == caterer.id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    data = await request.json()
    reason = data.get("reason", "").strip()
    
    # If booking is confirmed or beyond, require a reason
    if booking.status in ["confirmed", "preparing", "ready_for_pickup", "ready_for_delivery", "on_the_way", "in_progress", "setup_ongoing"]:
        if not reason:
            raise HTTPException(status_code=400, detail="Reason for modification is required for confirmed bookings.")
            
    # Audit log creation
    changes = []
    
    if data.get("customer_name") and data.get("customer_name") != booking.customer_name:
        changes.append(f"Customer Name changed to {data.get('customer_name')}")
        booking.customer_name = data.get("customer_name")
        
    if data.get("event_date"):
        import datetime
        try:
            new_date = datetime.datetime.strptime(data.get("event_date"), "%Y-%m-%d").date()
            if new_date != booking.event_date:
                changes.append(f"Event Date changed to {new_date}")
                booking.event_date = new_date
        except:
            pass
            
    if data.get("event_time"):
        import datetime
        try:
            new_time = datetime.datetime.strptime(data.get("event_time", "00:00"), "%H:%M").time()
            if new_time != booking.event_time:
                changes.append(f"Event Time changed to {new_time}")
                booking.event_time = new_time
        except:
            pass
            
    if data.get("venue_address") and data.get("venue_address") != booking.venue_address:
        changes.append(f"Venue changed")
        booking.venue_address = data.get("venue_address")
        
    if data.get("guest_count") and int(data.get("guest_count")) != booking.guest_count:
        changes.append(f"Guest Count changed to {data.get('guest_count')}")
        booking.guest_count = int(data.get("guest_count"))
        
    if changes:
        history_note = "Booking details updated: " + ", ".join(changes)
        if reason:
            history_note += f" | Reason: {reason}"
            
        history = models.BookingHistory(
            booking_id=booking.id,
            status=booking.status,
            notes=history_note,
            entry_type="system"
        )
        db.add(history)
        
    db.commit()
    return {"success": True}

@router.post("/api/bookings/{booking_id}/prep-date")
async def set_preparation_date(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    caterer = db.query(models.CatererProfile).filter(models.CatererProfile.user_id == user.id).first()
    if not caterer:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.caterer_id == caterer.id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    data = await request.json()
    prep_date = data.get("preparation_date")
    
    if prep_date:
        import datetime
        try:
            booking.preparation_date = datetime.datetime.strptime(prep_date, "%Y-%m-%d").date()
            if booking.preparation_status == "not_started":
                booking.preparation_status = "scheduled"
                
            history = models.BookingHistory(
                booking_id=booking.id,
                status=booking.status,
                notes=f"Preparation lead time scheduled for {prep_date}",
                entry_type="system"
            )
            db.add(history)
            db.commit()
            return {"success": True}
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid date format")
    raise HTTPException(status_code=400, detail="Date required")
"""

if "@router.post(\"/api/bookings/{booking_id}/edit\")" not in backend_code:
    with open('app/routers/caterer_dashboard.py', 'a', encoding='utf-8') as f:
        f.write("\n" + new_routes)
    print("Injected Phase 2 routes into caterer_dashboard.py")
else:
    print("Phase 2 routes already exist in caterer_dashboard.py")
