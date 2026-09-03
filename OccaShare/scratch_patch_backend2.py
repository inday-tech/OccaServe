import re
from datetime import datetime

with open("app/routers/caterer_dashboard.py", "r", encoding="utf-8") as f:
    content = f.read()

endpoint_code = """
@router.post("/api/bookings/external")
async def create_external_booking(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    try:
        data = await request.json()
        caterer = db.query(models.CatererProfile).filter(models.CatererProfile.user_id == user.id).first()
        if not caterer:
            raise HTTPException(status_code=403, detail="Caterer profile not found")
            
        import datetime
        try:
            event_date = datetime.datetime.strptime(data.get("event_date"), "%Y-%m-%d").date()
        except:
            raise HTTPException(status_code=400, detail="Invalid event date format")
            
        try:
            event_time = datetime.datetime.strptime(data.get("event_time", "00:00"), "%H:%M").time()
        except:
            event_time = None

        new_booking = models.Booking(
            caterer_id=caterer.id,
            booking_source=data.get("booking_source", "Walk-in"),
            customer_name=data.get("customer_name"),
            customer_contact=data.get("customer_contact"),
            customer_email=data.get("customer_email"),
            event_type=data.get("event_type"),
            event_name=data.get("event_name"),
            event_date=event_date,
            event_time=event_time,
            guest_count=data.get("guest_count", 1),
            venue_address=data.get("venue_address"),
            total_amount=data.get("total_amount", 0.0),
            total_price=data.get("total_amount", 0.0),
            status=data.get("status", "inquiry")
        )
        
        if data.get("package_id") and str(data.get("package_id")).isdigit():
            new_booking.package_id = int(data.get("package_id"))
            
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)
        
        # Add Custom Add-ons
        addons = data.get("addons", [])
        for addon in addons:
            if addon.get("name") and float(addon.get("price", 0)) > 0:
                item = models.BookingMenuItem(
                    booking_id=new_booking.id,
                    custom_name=addon.get("name"),
                    price=float(addon.get("price")),
                    quantity=1,
                    is_add_on=True
                )
                db.add(item)
                
        # Communication Note
        note = data.get("notes", "").strip()
        if note:
            hist = models.BookingHistory(
                booking_id=new_booking.id,
                status=new_booking.status,
                notes=note,
                entry_type="communication",
                communication_channel=new_booking.booking_source
            )
            db.add(hist)
            
        db.commit()
        return {"success": True, "booking_id": new_booking.id}
        
    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        print("External Booking Error:", e)
        raise HTTPException(status_code=500, detail="Failed to save external booking")
"""

if "@router.post(\"/api/bookings/external\")" not in content:
    # Insert right before @router.post("/api/bookings/manual")
    target = '@router.post("/api/bookings/manual")'
    if target in content:
        content = content.replace(target, endpoint_code + "\n\n" + target)
        with open("app/routers/caterer_dashboard.py", "w", encoding="utf-8") as fw:
            fw.write(content)
        print("Backend route added.")
    else:
        print("Target not found.")
else:
    print("Backend route already exists.")
