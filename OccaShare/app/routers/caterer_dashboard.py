from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, UploadFile, File, Body
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from ..core.templates import templates
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..db import database, models, schemas
from ..core import security as auth
import json
import os
import shutil
import uuid
from ..services.realtime import manager
from ..services.payment_verification import payment_verification_service
from ..services.notification import NotificationService

router = APIRouter(prefix="/caterer", tags=["caterer"])

UPLOAD_DIR = "app/static/uploads/caterer"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Standard dependency for caterer access
caterer_only = auth.RoleChecker(["caterer"])

@router.post("/platform-feedback")
async def submit_platform_feedback_caterer(
    rating: int = Form(...),
    comment: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    # Prevent duplicate submissions
    existing_fb = db.query(models.PlatformFeedback).filter_by(user_id=user.id).first()
    if existing_fb:
        error_msg = "You have already submitted feedback. Thank you!"
        return RedirectResponse(url="/caterer/dashboard?error_msg=" + error_msg, status_code=303)

    if rating < 1 or rating > 5:
        return RedirectResponse(url="/caterer/dashboard?error_msg=Invalid+rating", status_code=303)
    if not comment or len(comment.strip()) < 10:
        return RedirectResponse(url="/caterer/dashboard?error_msg=Feedback+too+short", status_code=303)

    fb = models.PlatformFeedback(
        user_id=user.id,
        rating=rating,
        comment=comment.strip(),
        role="caterer"
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)

    # Broadcast real-time update to all connected admins
    await manager.broadcast_to_role("admin", {
        "type": "new_platform_feedback",
        "id": fb.id,
        "rating": fb.rating,
        "comment": fb.comment,
        "role": "caterer",
        "user_name": (user.caterer_profile.business_name if user.caterer_profile else None) or f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
        "user_email": user.email,
        "created_at": fb.created_at.strftime('%b %d, %Y') if fb.created_at else 'Just now'
    })

    return RedirectResponse(url="/caterer/dashboard?success_msg=Thank+you+for+your+feedback!", status_code=303)

@router.post("/api/validate-package-name")
async def validate_package_name(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    data = await request.json()
    name = data.get("name", "").strip()
    exclude_id = data.get("exclude_id")
    
    if not name:
        return {"exists": False}

    query = db.query(models.CateringPackage).filter(
        models.CateringPackage.caterer_id == user.caterer_profile.id,
        func.lower(models.CateringPackage.name) == name.lower(),
        models.CateringPackage.status != "archived"
    )
    
    if exclude_id:
        query = query.filter(models.CateringPackage.id != int(exclude_id))
        
    exists = query.first() is not None
    return {"exists": exists}

@router.post("/api/validate-dish-name")
async def validate_dish_name(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    data = await request.json()
    name = data.get("name", "").strip()
    exclude_id = data.get("exclude_id")
    
    if not name:
        return {"exists": False}

    query = db.query(models.MenuItem).filter(
        models.MenuItem.caterer_id == user.caterer_profile.id,
        func.lower(models.MenuItem.name) == name.lower(),
        models.MenuItem.is_archived == False
    )
    
    if exclude_id:
        query = query.filter(models.MenuItem.id != int(exclude_id))
        
    exists = query.first() is not None
    return {"exists": exists}

@router.post("/api/bookings/manual")
async def create_manual_booking(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    try:
        data = await request.json()
        customer_email = data.get("customer_email", "").strip()
        customer_contact = data.get("customer_contact", "").strip()
        customer_name = data.get("customer_name", "").strip()
        
        if not customer_name:
            raise HTTPException(status_code=400, detail="Customer name is required")

        # 1. Handle User (Customer)
        target_user = None
        if "@" in customer_email:
            target_user = db.query(models.User).filter(models.User.email == customer_email).first()
        
        if not target_user:
            # Create a shadow/guest user
            from ..core import security as auth_utils
            temp_pass = auth_utils.pwd_context.hash(str(uuid.uuid4()))
            target_user = models.User(
                email=customer_email if "@" in customer_email else f"walkin_{uuid.uuid4().hex[:8]}@guest.occashare.com",
                first_name=customer_name,
                phone_number=customer_contact,
                password_hash=temp_pass,
                role="customer",
                status="active"
            )
            db.add(target_user)
            db.flush() 

        # 2. Create Booking
        event_date = datetime.strptime(data.get("event_date")[:10], "%Y-%m-%d").date()
        event_time_str = data.get("event_time")
        if event_time_str:
            try:
                event_time = datetime.strptime(event_time_str[:5], "%H:%M").time()
            except ValueError:
                event_time = None
        else:
            event_time = None

        new_booking = models.Booking(
            user_id=target_user.id,
            caterer_id=user.caterer_profile.id,
            package_id=data.get("package_id") or None,
            event_name=data.get("event_name"),
            event_type=data.get("event_type"),
            event_date=event_date,
            event_time=event_time,
            guest_count=data.get("guest_count", 0),
            total_amount=data.get("total_amount", 0),
            total_price=data.get("total_amount", 0),
            venue_address=data.get("venue_address"),
            status="confirmed", 
            payment_status="paid", 
            payment_method="Cash",
            special_requests="Walk-in Booking"
        )
        db.add(new_booking)
        db.flush()

        # 3. Handle Selected Menu Items (Add-ons or Package items)
        menu_item_ids = data.get("menu_items", [])
        if menu_item_ids:
            for mi_id in menu_item_ids:
                mi = db.query(models.MenuItem).get(mi_id)
                if mi:
                    sel_item = models.SelectedMenuItem(
                        booking_id=new_booking.id,
                        menu_item_id=mi.id,
                        quantity=1, # Default for now
                        price_at_booking=mi.addon_price or mi.price or 0
                    )
                    db.add(sel_item)
        
        # 4. Add History
        history = models.BookingHistory(
            booking_id=new_booking.id,
            status="confirmed",
            notes="Manual walk-in booking created by caterer."
        )
        db.add(history)
        
        db.commit()
        return {"status": "success", "booking_id": new_booking.id}
    except Exception as e:
        db.rollback()
        print(f"[CATERER MANUAL BOOKING ERROR] {e}")
        raise HTTPException(status_code=500, detail=str(e))

class StatusUpdateSchema(BaseModel):
    status: str

@router.post("/bookings/{booking_id}/update-status")
async def update_booking_status(
    booking_id: int,
    data: StatusUpdateSchema,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    new_status = data.status
    allowed_statuses = ["preparing", "ready_for_delivery", "on_the_way", "arrived", "setup_ongoing", "completed", "cancelled"]
    
    if new_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    # Business Logic Checks: Allow completion if plan is FULL or status is PAID
    if new_status == "completed" and booking.payment_status != "paid" and booking.payment_plan != "full":
        raise HTTPException(status_code=400, detail="You can only mark this as Completed once the booking is Fully Paid.")

    old_status = booking.status
    booking.status = new_status
    
    # Log History
    history = models.BookingHistory(
        booking_id=booking.id,
        status=new_status,
        notes=f"Status changed from {old_status} to {new_status} by caterer."
    )
    db.add(history)

    # SECURE PAYOUT: Release Escrowed Funds to 'Ready' status
    if new_status == "completed":
        escrow_items = db.query(models.PayoutItem).filter(
            models.PayoutItem.booking_id == booking.id,
            models.PayoutItem.status == 'escrowed'
        ).all()
        for item in escrow_items:
            item.status = 'ready'
            # Optional: Add history or notification for admin to check payouts
            
    db.commit()

    # Trigger Notifications
    from ..services.notification import NotificationService
    title = ""
    message = ""
    
    if new_status == "preparing":
        title = "Preparation Started! 🍳"
        message = f"The caterer {user.caterer_profile.business_name} has started preparing for your food order '{booking.event_name}'."
    elif new_status == "ready_for_delivery":
        title = "Ready for Delivery! 🍱"
        message = f"Cooking is complete! Your order is packed and ready for dispatch."
    elif new_status == "on_the_way":
        title = "Order is in Transit! 🚚"
        message = f"Our delivery team is on the way to your location for '{booking.event_name}'. Get those tables ready!"
    elif new_status == "arrived":
        title = "Caterer has Arrived! 📍"
        message = f"Our team has arrived at your location. Please coordinate with our staff for turnover."
    elif new_status == "setup_ongoing":
        title = "Dining Setup Ongoing 🍽️"
        message = f"Your food service is currently being set up. We are almost ready to serve!"
    elif new_status == "completed":
        title = "Transaction Completed! ✨"
        message = f"Successfully delivered and served for your event '{booking.event_name}'. Thank you for choosing us!"

    if title and message:
        await NotificationService.notify_status_update(
            db, 
            booking.user_id, 
            title, 
            message, 
            f"/customer/bookings/manage/{booking.id}"
        )

    # 4. WebSocket Update to Caterer
    status_class_map = {
        'pending_quotation': 'ps-badge-draft',
        'awaiting_caterer': 'ps-badge-pending',
        'awaiting_payment': 'ps-badge-payment',
        'pending': 'ps-badge-pending',
        'confirmed': 'ps-badge-confirmed',
        'preparing': 'ps-badge-preparing',
        'ready_for_delivery': 'ps-badge-ready',
        'on_the_way': 'ps-badge-transit',
        'arrived': 'ps-badge-arrived',
        'setup_ongoing': 'ps-badge-ongoing',
        'completed': 'ps-badge-completed',
        'cancelled': 'ps-badge-cancelled'
    }
    status_label_map = {
        'pending_quotation': 'Draft',
        'awaiting_caterer': 'To Sign',
        'awaiting_payment': 'Payment',
        'ready_for_delivery': 'Ready',
        'on_the_way': 'In Transit',
        'arrived': 'Arrived',
        'setup_ongoing': 'Fixing Setup',
    }
    
    await manager.broadcast_to_user(user.id, {
        "type": "booking_update",
        "booking_id": booking.id,
        "new_status": new_status,
        "status_label": status_label_map.get(new_status, new_status.replace('_', ' ').capitalize()),
        "status_class": status_class_map.get(new_status, 'ps-badge-draft'),
        "message": f"Status updated to {new_status}"
    })

    return {"status": "success", "new_status": new_status}

def _get_caterer_stats(profile, bookings, timeframe='month'):
    from datetime import datetime, date, timedelta
    from dateutil.relativedelta import relativedelta
    
    today = date.today()
    
    # 1. Define Timeframe Bounds for TOP STATS
    if timeframe == 'day':
        stats_start = today
        chart_points = [(today - timedelta(days=i)) for i in range(6, -1, -1)] # Last 7 days for trend
        date_format = "%Y-%m-%d"
    elif timeframe == 'week':
        stats_start = today - timedelta(days=today.weekday()) # Current Week start (Monday)
        chart_points = [(today - timedelta(days=i)) for i in range(13, -1, -1)] # Last 14 days for trend
        date_format = "%Y-%m-%d"
    elif timeframe == 'year':
        stats_start = today.replace(month=1, day=1) # Current Year start
        chart_points = [today.replace(month=1, day=1) + relativedelta(months=i) for i in range(12)] # All months of the year
        date_format = "%Y-%m"
    else: # Default: Monthly
        stats_start = today.replace(day=1) # Current Month start
        chart_points = [(today - relativedelta(months=5)).replace(day=1) + relativedelta(months=i) for i in range(6)]
        date_format = "%Y-%m"

    chart_keys = [d.strftime(date_format) for d in chart_points]
    
    # Stats Counters (FOR TOP CARDS - FILTERED)
    total_realized_revenue = 0
    total_projected_revenue = 0
    total_actual_expenses = 0
    total_projected_expenses = 0
    unique_customers = set()
    active_bookings = 0
    
    # Chart Data Pools (FOR TREND)
    period_revenue = {k: 0.0 for k in chart_keys}
    period_expenses = {k: 0.0 for k in chart_keys}
    period_bookings = {k: {'completed': 0, 'pending': 0} for k in chart_keys}
    
    package_stats = {} # {id: {revenue: 0, expenses: 0, orders: 0}}
    
    for b in bookings:
        if not b.event_date: continue
        
        amount = float(b.total_amount or b.total_price or 0)
        
        # Determine Cost Baseline
        base_cost_price = 0
        if b.package and b.package.cost_price:
            if b.package.price_unit == "per_guest":
                base_cost_price = (b.package.cost_price) * (b.guest_count or 1)
            else:
                base_cost_price = b.package.cost_price
        else:
            base_cost_price = amount * 0.60 # Standard 60% fallback
        
        actual_cost = b.actual_cost if b.actual_cost and b.actual_cost > 0 else base_cost_price
        
        # --- A. TOP STATS FILTERING ---
        if b.event_date >= stats_start:
            unique_customers.add(b.user_id)
            
            if b.status in ['confirmed', 'preparing', 'on_the_way', 'in_progress', 'completed']:
                total_projected_revenue += amount
                total_projected_expenses += actual_cost
                if b.status != 'completed': active_bookings += 1

            # Realized Revenue Computation
            cleared_amount = 0
            if b.payment_status == 'paid':
                cleared_amount = amount
            elif b.payment_status == 'deposit_paid':
                dep_pct = 20
                if b.quotation: dep_pct = b.quotation.downpayment_percent
                cleared_amount = amount * (dep_pct / 100)
            
            total_realized_revenue += cleared_amount
            total_actual_expenses += actual_cost if b.status in ['confirmed', 'completed', 'in_progress'] else 0

        # --- B. TREND CHART AGGREGATION ---
        date_key = b.event_date.strftime(date_format)
        if date_key in period_revenue:
            cleared_chart = 0
            if b.payment_status == 'paid': cleared_chart = amount
            elif b.payment_status == 'deposit_paid':
                dep_pct = 20
                if b.quotation: dep_pct = b.quotation.downpayment_percent
                cleared_chart = amount * (dep_pct / 100)
                
            period_revenue[date_key] += cleared_chart
            period_expenses[date_key] += actual_cost
            
            if b.status in ['completed', 'confirmed', 'in_progress']:
                period_bookings[date_key]['completed'] += 1
            elif b.status != 'cancelled':
                period_bookings[date_key]['pending'] += 1

        # --- C. PACKAGE EFFICIENCY ---
        if b.package_id and b.event_date >= stats_start:
            if b.package_id not in package_stats:
                package_stats[b.package_id] = {'revenue': 0, 'expenses': 0, 'orders': 0}
            package_stats[b.package_id]['orders'] += 1
            if b.status in ['confirmed', 'completed']:
                package_stats[b.package_id]['revenue'] += amount
                package_stats[b.package_id]['expenses'] += actual_cost

    # Calculation Summary
    projected_net_profit = total_projected_revenue - total_projected_expenses
    projected_roi = ((projected_net_profit / total_projected_expenses) * 100) if total_projected_expenses > 0 else 0
    
    realized_net_profit = total_realized_revenue - total_actual_expenses
    realized_roi = ((realized_net_profit / total_actual_expenses) * 100) if total_actual_expenses > 0 else 0

    # Format Chart Data
    chart_data = []
    roi_trend_data = []
    bookings_chart_data = []
    
    for k in chart_keys:
        rev = period_revenue[k]
        exp = period_expenses[k]
        roi = ((rev - exp) / exp * 100) if exp > 0 else 0
        
        try:
            if date_format == "%Y-%m-%d":
                label = datetime.strptime(k, date_format).strftime("%b %d")
            else:
                label = datetime.strptime(k, date_format).strftime("%b %Y")
        except:
            label = k

        chart_data.append({"date": k, "revenue": rev, "label": label})
        roi_trend_data.append({"date": k, "roi": round(roi, 1), "label": label})
        bookings_chart_data.append({
            "date": k, "completed": period_bookings[k]['completed'], "pending": period_bookings[k]['pending'], "label": label
        })
    
    upcoming_events = sorted([b for b in bookings if b.status == 'confirmed' and b.event_date and b.event_date >= today], key=lambda x: x.event_date)[:4]
    
    popular_packages = []
    for pkg in profile.packages:
        if pkg.id in package_stats:
            stats = package_stats[pkg.id]
            pkg_roi = ((stats['revenue'] - stats['expenses']) / stats['expenses'] * 100) if stats['expenses'] > 0 else 0
            popular_packages.append({
                "id": pkg.id, "name": pkg.name, "price": float(pkg.price_per_head or pkg.price or 0), 
                "orders": stats['orders'], "roi": round(pkg_roi, 1)
            })
    popular_packages.sort(key=lambda x: x['orders'], reverse=True)

    return {
        "total_revenue": total_realized_revenue, 
        "projected_revenue": total_projected_revenue,
        "net_profit": realized_net_profit,
        "projected_profit": projected_net_profit,
        "estimated_expenses": total_projected_expenses,
        "actual_expenses": total_actual_expenses,
        "roi_percentage": round(realized_roi, 1),
        "projected_roi": round(projected_roi, 1),
        "total_customers": len(unique_customers),
        "chart_data": chart_data,
        "roi_trend_data": roi_trend_data,
        "bookings_chart_data": bookings_chart_data,
        "upcoming_events": upcoming_events,
        "popular_packages": popular_packages[:4],
        "recent_orders": sorted([b for b in bookings if b.event_date and b.event_date >= stats_start], key=lambda x: x.id, reverse=True)[:5],
        "timeframe": timeframe
    }

@router.get("/dashboard", response_class=HTMLResponse)
async def caterer_dashboard(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    bookings = [b for b in profile.bookings if b.status != 'draft' and not b.is_archived]
    
    timeframe = request.query_params.get('timeframe', 'month')
    stats = _get_caterer_stats(profile, bookings, timeframe=timeframe)
    
    
    return templates.TemplateResponse("caterer/index.html", {
        "request": request,
        "user": user,
        "profile": profile,
        **stats,
        "active_page": "dashboard"
    })

@router.get("/api/dashboard-overview")
async def dashboard_overview_api(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    from fastapi.responses import JSONResponse
    profile = user.caterer_profile
    bookings = [b for b in profile.bookings if b.status != 'draft' and not b.is_archived]
    
    timeframe = request.query_params.get('timeframe', 'month')
    stats = _get_caterer_stats(profile, bookings, timeframe=timeframe)
    
    # Process complex objects for JSON
    serializable_upcoming = []
    for e in stats['upcoming_events']:
        serializable_upcoming.append({
            "id": e.id,
            "event_name": e.event_name,
            "event_type": e.event_type,
            "status": e.status,
            "package_name": e.package.name if e.package else e.event_type,
            "event_date": e.event_date.strftime('%Y-%m-%d') if e.event_date else None,
            "event_time": e.event_time.strftime('%I:%M %p') if e.event_time else None,
            "month_short": e.event_date.strftime('%b') if e.event_date else '???',
            "day": e.event_date.strftime('%d') if e.event_date else '??',
            "venue_address": e.venue_address,
            "guest_count": e.guest_count
        })

    serializable_recent = []
    for b in stats['recent_orders']:
        serializable_recent.append({
            "id": b.id,
            "customer_name": f"{b.user.first_name} {b.user.last_name}" if b.user else "Walk-in Customer",
            "customer_initials": f"{b.user.first_name[0]}{b.user.last_name[0]}" if b.user else "WI",
            "event_type": b.event_type,
            "total_amount": float(b.total_amount or 0),
            "event_date": b.event_date.strftime('%b %d, %Y') if b.event_date else '',
            "status": b.status
        })

    return JSONResponse({
        "total_revenue": stats['total_revenue'],
        "projected_revenue": stats['projected_revenue'],
        "net_profit": stats['net_profit'],
        "projected_profit": stats['projected_profit'],
        "estimated_expenses": stats['estimated_expenses'],
        "actual_expenses": stats['actual_expenses'],
        "roi_percentage": stats['roi_percentage'],
        "roi_trend_data": stats['roi_trend_data'],
        "total_customers": stats['total_customers'],
        "chart_data": stats['chart_data'],
        "bookings_chart_data": stats['bookings_chart_data'],
        "upcoming_events": serializable_upcoming,
        "popular_packages": stats['popular_packages'],
        "recent_orders": serializable_recent
    })

@router.get("/bookings", response_class=HTMLResponse)
async def manage_bookings(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    all_bookings = [b for b in user.caterer_profile.bookings if b.status != 'draft' and not b.is_archived]
    all_bookings.sort(key=lambda x: x.id, reverse=True)
    
    total_bookings = len(all_bookings)
    confirmed_count = sum(1 for b in all_bookings if b.status in ['confirmed', 'completed'])
    pending_count = sum(1 for b in all_bookings if b.status in ['pending', 'pending_quotation', 'awaiting_caterer', 'awaiting_payment'])
    cancelled_count = sum(1 for b in all_bookings if b.status == 'cancelled')
    
    packages = db.query(models.CateringPackage).filter(
        models.CateringPackage.caterer_id == user.caterer_profile.id,
        models.CateringPackage.status == 'active'
    ).all()
    
    return templates.TemplateResponse("caterer/bookings.html", {
        "request": request,
        "user": user,
        "bookings": all_bookings,
        "packages": packages,
        "total_bookings": total_bookings,
        "confirmed_count": confirmed_count,
        "pending_count": pending_count,
        "cancelled_count": cancelled_count,
        "active_page": "bookings"
    })

@router.get("/bookings/{booking_id}/contract", response_class=HTMLResponse)
async def view_contract_caterer(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
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

@router.get("/bookings/{booking_id}/sign", response_class=HTMLResponse)
async def sign_contract_caterer(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    quotation = booking.quotation
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found for this booking")

    return templates.TemplateResponse("caterer/sign_contract.html", {
        "request": request,
        "user": user,
        "booking": booking,
        "quotation": quotation,
        "active_page": "bookings"
    })

@router.get("/archives", response_class=HTMLResponse)
async def caterer_archives(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    """Render the archives view for the caterer, showing all archived items."""
    profile = user.caterer_profile
    if not profile:
        return RedirectResponse(url="/caterer/setup")

    # Fetch archived items
    archived_menu_items = [item for item in profile.menu_items if item.is_archived]
    archived_packages = [pkg for pkg in profile.packages if pkg.status == 'archived']
    archived_gallery_items = [item for item in profile.gallery_items if item.is_archived]
    archived_bookings = [b for b in profile.bookings if b.is_archived]
    archived_ingredients = [ing for ing in profile.ingredients if ing.is_archived]

    return templates.TemplateResponse("caterer/archives.html", {
        "request": request,
        "user": user,
        "archived_menu_items": archived_menu_items,
        "archived_packages": archived_packages,
        "archived_gallery_items": archived_gallery_items,
        "archived_bookings": archived_bookings,
        "archived_ingredients": archived_ingredients,
        "active_page": "archives"
    })

@router.get("/payments", response_class=HTMLResponse)
async def caterer_payments(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    from datetime import datetime, timezone
    profile = user.caterer_profile
    bookings = [b for b in profile.bookings if b.status != 'draft' and not b.is_archived]

    # ── Payout-table totals (formal system values) ──────────────────────────
    released_payout = db.query(func.sum(models.PayoutItem.amount)).join(models.Payout).filter(
        models.Payout.caterer_id == profile.id,
        models.PayoutItem.status == 'released'
    ).scalar() or 0.0

    ready_payout = db.query(func.sum(models.PayoutItem.amount)).join(models.Payout).filter(
        models.Payout.caterer_id == profile.id,
        models.PayoutItem.status == 'ready'
    ).scalar() or 0.0

    escrow_payout = db.query(func.sum(models.PayoutItem.amount)).join(models.Payout).filter(
        models.Payout.caterer_id == profile.id,
        models.PayoutItem.status == 'escrowed'
    ).scalar() or 0.0

    # ── Booking-based fallback (always accurate even without payout records) ─
    # Compute directly from booking payment_status for accuracy
    booking_released = 0.0   # fully paid + completed
    booking_escrow   = 0.0   # deposit_paid — balance held until event
    booking_pending  = 0.0   # not yet paid

    now = datetime.now(timezone.utc)
    active_count = 0

    for b in bookings:
        if b.status in ('cancelled', 'rejected'):
            continue
        active_count += 1
        amount = float(b.total_amount or b.total_price or 0)

        if b.payment_status == 'paid' and b.status == 'completed':
            booking_released += amount
        elif b.payment_status == 'paid':
            # Paid but not yet completed — treat as escrow pending release
            booking_escrow += amount
        elif b.payment_status == 'deposit_paid':
            # Partial: deposit released, balance escrowed
            dp_pct = 0.20
            if b.quotation and b.quotation.downpayment_percent:
                dp_pct = b.quotation.downpayment_percent / 100.0
            deposit = amount * dp_pct
            booking_released += deposit
            booking_escrow   += (amount - deposit)
        else:
            booking_pending += amount

    # Use payout table if it has real data, otherwise use booking-based values
    has_payout_data = (released_payout + ready_payout + escrow_payout) > 0
    if has_payout_data:
        released_total = released_payout
        ready_total    = ready_payout
        escrow_total   = escrow_payout
    else:
        released_total = booking_released
        ready_total    = booking_pending   # pending = ready-to-collect
        escrow_total   = booking_escrow

    return templates.TemplateResponse("caterer/payments.html", {
        "request": request,
        "user": user,
        "bookings": bookings,
        "released_total": released_total,
        "ready_total": ready_total,
        "escrow_total": escrow_total,
        "capital_total": released_total + ready_total,
        "active_count": active_count,
        "active_page": "payments"
    })


@router.get("/payments/{booking_id}/confirm")
async def confirm_caterer_payment_get(booking_id: int):
    # This specifically handles cases where old cached JS or browser redirects 
    # might attempt a GET request on this state-changing endpoint.
    # We redirect back to payments with an instruction to retry.
    return RedirectResponse(
        url="/caterer/payments?error_msg=Manual+refresh+required.+Please+click+Verify+again.", 
        status_code=303
    )

async def _confirm_booking_logic(db: Session, booking: models.Booking, caterer_user: models.User, is_manual_accept: bool = False):
    """Shared logic for confirming a booking via payment verification or manual acceptance."""
    from ..services.notification import NotificationService
    import asyncio
    
    old_payment_status = booking.payment_status
    history_note = "Booking confirmed by caterer."
    
    # CASE 1: Downpayment Verification or Initial Acceptance
    if booking.payment_status in ['proof_submitted', 'reupload_requested', 'pending'] or booking.status == 'pending':
        if booking.payment_plan == 'full':
            booking.payment_status = 'paid'
        else:
            booking.payment_status = 'deposit_paid'
        booking.status = 'confirmed'
        
        # Calculate Initial Actual Cost (Baseline)
        total_cost = 0
        if booking.package:
            if booking.package.price_unit == "per_guest":
                total_cost += (booking.package.cost_price or 0) * (booking.guest_count or 0)
            else:
                total_cost += (booking.package.cost_price or 0)
        
        # Add selected items cost
        from sqlalchemy import text
        # Using a join or subquery might be better but let's stick to the existing approach safely
        for item in booking.selected_items:
            if hasattr(item, 'menu_item') and item.menu_item:
                total_cost += (item.menu_item.cost_price or 0)
        
        booking.actual_cost = total_cost
        
        if is_manual_accept:
            history_note = "Booking manually ACCEPTED and CONFIRMED by caterer."
        else:
            history_note = "Downpayment verified and confirmed. Booking is now officially CONFIRMED."
            
        # Notification to Customer
        await NotificationService.notify_status_update(
            db, booking.user_id, 
            "Booking Confirmed! ✅", 
            f"Ang iyong booking para sa '{booking.event_name}' ay CONFIRMED na! Naka-verify na ang iyong reservation.", 
            f"/customer/bookings/manage/{booking.id}"
        )

    # CASE 2: Final Balance Verification
    elif booking.payment_status in ['balance_proof_submitted', 'balance_reupload_requested']:
        booking.payment_status = 'paid'
        history_note = "Final balance verified. Booking is now FULLY PAID."
        
        await NotificationService.notify_status_update(
            db, booking.user_id, 
            "Payment Fully Verified! 💰", 
            f"Natanggap at na-verify na ang iyong full payment para sa '{booking.event_name}'. Maraming salamat!", 
            f"/customer/bookings/manage/{booking.id}"
        )
    
    # CASE 3: Fallback / Manual Override to Paid
    else:
        booking.payment_status = 'paid'
        history_note = "Booking/Payment marked as fully received manually."

    # Log History
    history = models.BookingHistory(
        booking_id=booking.id,
        status=booking.status,
        notes=history_note
    )
    db.add(history)
    db.commit()

    # WebSocket Updates
    # 1. To Customer
    asyncio.create_task(manager.broadcast_to_user(booking.user_id, {
        "type": "payment_update",
        "message": f"Status updated for {booking.event_name}",
        "booking_id": booking.id,
        "status": booking.status,
        "payment_status": booking.payment_status
    }))

    # 2. To Caterer
    status_class_map = {
        'deposit_paid': 'ps-badge-confirmed',
        'paid': 'ps-badge-completed',
        'proof_submitted': 'ps-badge-payment',
        'balance_proof_submitted': 'ps-badge-payment'
    }
    
    await manager.broadcast_to_user(caterer_user.id, {
        "type": "booking_update",
        "booking_id": booking.id,
        "new_status": booking.status,
        "new_payment_status": booking.payment_status,
        "payment_status_class": status_class_map.get(booking.payment_status, 'ps-badge-payment'),
        "message": history_note
    })

    await manager.broadcast_to_user(caterer_user.id, {
        "type": "dashboard_update",
        "message": "Stats updated: Booking confirmed."
    })

    return {"status": "success", "message": history_note}

@router.post("/bookings/{booking_id}/accept")
async def accept_booking_manual(
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    """Allows a caterer to manually accept a booking, bypassing digital proof verification."""
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    result = await _confirm_booking_logic(db, booking, user, is_manual_accept=True)
    return result

@router.post("/payments/{booking_id}/confirm")
async def confirm_caterer_payment(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    # [Rest of AI verification logic remains before calling logic]

    # [NEW] Automated Proof Verification Detection
    proof_path = None
    if booking.payment_proof_url:
        # Resolve path handling both root-relative and app-relative structures
        raw_url = booking.payment_proof_url.lstrip("/")
        proof_path = os.path.join(os.getcwd(), raw_url)
        if not os.path.exists(proof_path):
            # Fallback for when the file is inside the 'app/' directory but DB path is web-relative
            proof_path = os.path.join(os.getcwd(), "app", raw_url)

        if os.path.exists(proof_path):
            verify_results = payment_verification_service.check_for_fraud(db, booking, proof_path)
            booking.payment_verification_data = verify_results
            booking.proof_image_hash = payment_verification_service.get_image_hash(proof_path)
            if verify_results["confidence"] > 80:
                booking.ocr_verified = True
            
            # [NEW] Automated Fraud Flagging
            if verify_results["is_duplicate_ref"] or verify_results["confidence"] < 40 or not verify_results.get("amount_match", True):
                for flag_desc in verify_results["flags"]:
                    # Check if flag already exists to avoid duplicates
                    exists = db.query(models.FraudFlag).filter(
                        models.FraudFlag.booking_id == booking.id,
                        models.FraudFlag.description == flag_desc
                    ).first()
                    if not exists:
                        db.add(models.FraudFlag(
                            booking_id=booking.id, 
                            flag_type="high_risk_detected", 
                            description=flag_desc
                        ))
                
                # WebSocket Alert to Caterer
                await manager.broadcast_to_user(user.id, {
                    "type": "risk_alert",
                    "booking_id": booking_id,
                    "message": "⚠️ High Risk Payment Detected! Check AI Scan details."
                })

        
    # Call shared confirmation logic
    result = await _confirm_booking_logic(db, booking, user, is_manual_accept=False)
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({
            "status": "success", 
            "message": result["message"], 
            "new_status": booking.status,
            "new_payment_status": booking.payment_status
        })
        
    return RedirectResponse(url="/caterer/payments?success_msg=Payment+confirmed+successfully", status_code=303)

@router.post("/bookings/{booking_id}/request-new-proof")
async def request_new_proof(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    data = await request.json()
    reason = data.get("reason", "The submitted proof was unreadable or incorrect.")

    # 1. Reset proof fields and status based on current state
    if booking.payment_status == 'proof_submitted':
        booking.payment_status = 'reupload_requested'
        booking.payment_proof_url = None
    elif booking.payment_status == 'balance_proof_submitted':
        booking.payment_status = 'balance_reupload_requested'
        booking.balance_proof_url = None

    # 2. Add History
    history = models.BookingHistory(
        booking_id=booking.id,
        status=booking.status,
        notes=f"Payment proof rejected. Reason: {reason}"
    )
    db.add(history)
    
    # 3. Add Fraud Flag if it was rejected for suspicious reasons
    if "fake" in reason.lower() or "suspicious" in reason.lower() or "duplicate" in reason.lower():
        db.add(models.FraudFlag(
            booking_id=booking.id,
            flag_type="manual_rejection",
            description=f"Caterer rejected proof as suspicious: {reason}"
        ))

    db.commit()

    # 4. Notify Customer
    from ..services.notification import NotificationService
    await NotificationService.notify_proof_rejected(db, booking, reason)

    # 5. Broadcast real-time update to both parties
    await manager.broadcast_to_user(booking.user_id, {
        "type": "payment_rejected",
        "booking_id": booking.id,
        "reason": reason,
        "message": f"Ay naku! Ang iyong payment proof sa {booking.event_name} ay tinanggihan. Silipin sa dashboard para sa detalye."
    })
    
    await manager.broadcast_to_user(user.id, {
        "type": "booking_update",
        "booking_id": booking.id,
        "new_payment_status": booking.payment_status,
        "message": "Proof rejected. Waiting for re-upload."
    })

    return {"status": "success", "message": "Customer notified to re-upload proof."}

class DueDateRequest(BaseModel):
    due_date: str

@router.post("/api/bookings/{booking_id}/set-due-date")
async def set_balance_due_date(
    booking_id: int,
    req: DueDateRequest,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or (user.caterer_profile and booking.caterer_id != user.caterer_profile.id):
        raise HTTPException(status_code=404, detail="Booking not found")

    try:
        from datetime import datetime
        # Validate format
        new_date = datetime.strptime(req.due_date, '%Y-%m-%d').date()
        booking.balance_due_date = new_date
        
        # Add History
        history = models.BookingHistory(
            booking_id=booking.id,
            status=booking.status,
            notes=f"Balance Due Date set to {req.due_date} by Caterer."
        )
        db.add(history)
        db.commit()

        # [NEW] Notify Customer
        from ..services.notification import NotificationService
        await NotificationService.notify_status_update(
            db, 
            booking.user_id, 
            "Balance Payment Deadline Set", 
            f"The caterer has set the final payment deadline for '{booking.event_name}' to {req.due_date}. Please ensure payment is settled by this date.", 
            f"/customer/bookings/manage/{booking.id}"
        )
        
        return {"status": "success", "message": "Due date updated and customer notified"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

@router.post("/api/bookings/{booking_id}/verify-proof")
async def verify_booking_proof(
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    if not booking.payment_proof_url and not booking.balance_proof_url:
        return {"status": "error", "message": "No proof uploaded yet."}

    proof_url = (booking.balance_proof_url or booking.payment_proof_url).lstrip("/")
    proof_path = os.path.join(os.getcwd(), proof_url)
    
    if not os.path.exists(proof_path):
        # Fallback for 'app/' directory structure
        proof_path = os.path.join(os.getcwd(), "app", proof_url)

    if not os.path.exists(proof_path):
        return {"status": "error", "message": f"Proof file missing on server. Looking at: {proof_path}"}

    verify_results = payment_verification_service.check_for_fraud(db, booking, proof_path)
    booking.payment_verification_data = verify_results
    booking.proof_image_hash = payment_verification_service.get_image_hash(proof_path)
    db.commit()

    return {"status": "success", "data": verify_results}

@router.get("/api/bookings/{booking_id}/details")
async def get_booking_details_api(
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Fetch commission settings
    config = db.query(models.WebsiteConfig).first()
    comm_rate = config.commission_rate if config else 10.0
    comm_fixed = config.commission_fixed_amount if config else 20.0
    
    total = float(booking.total_amount or 0)
    commission = (total * (comm_rate / 100.0)) + comm_fixed
    net_amount = total - commission

    return {
        "id": booking.id,
        "event_name": booking.event_name,
        "event_type": booking.event_type,
        "total_amount": total,
        "commission": round(commission, 2),
        "net_amount": round(net_amount, 2),
        "commission_rate": comm_rate,
        "payment_status": booking.payment_status,
        "payment_method": booking.payment_method,
        "payment_proof_url": booking.payment_proof_url,
        "balance_proof_url": booking.balance_proof_url,
        "payment_verification_data": booking.payment_verification_data,
        "quotation_id": booking.quotation.id if booking.quotation else None,
        "contract_url": booking.quotation.contract_url if booking.quotation else None,
        "user": {
            "first_name": booking.user.first_name if booking.user else "Walk-in",
            "last_name": booking.user.last_name if booking.user else "Customer",
            "email": booking.user.email if booking.user else "N/A"
        },
        "is_package": booking.package_id is not None
    }


@router.get("/bookings/{booking_id}/quotation")
async def view_booking_quotation(
    request: Request,
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    """View the detailed quotation/invoice for a booking."""
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    
    quotation = booking.quotation
    if not quotation:
        # Fallback if no quotation record exists
        quotation = {
            "total_amount": booking.total_amount,
            "package_details": {"name": booking.event_type},
            "addons": [],
            "status": "confirmed"
        }

    return templates.TemplateResponse("caterer/quotation_view.html", {
        "request": request,
        "booking": booking,
        "quotation": quotation,
        "user": user
    })


@router.post("/bookings/{booking_id}/complete")
async def complete_booking(
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    """Mark a confirmed booking as completed."""
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status not in ['confirmed', 'paid']:
        raise HTTPException(status_code=400, detail="Only confirmed bookings can be marked as completed")

    booking.status = 'completed'
    booking.payment_status = 'paid'  # Mark as fully settled when event is completed

    history = models.BookingHistory(
        booking_id=booking.id,
        status='completed',
        notes="Event completed. Booking marked as completed by caterer."
    )
    db.add(history)
    db.commit()

    # Real-time alert to customer
    import asyncio
    asyncio.create_task(manager.broadcast_to_user(booking.user_id, {
        "type": "booking_update",
        "message": f"Your event '{booking.event_name}' has been marked as completed!",
        "booking_id": booking.id,
        "status": "completed"
    }))

    return RedirectResponse(url=f"/caterer/bookings?success_msg=Booking+marked+as+completed", status_code=303)


@router.post("/bookings/{booking_id}/actual-cost")
async def update_actual_cost(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.caterer_id == user.caterer_profile.id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    data = await request.json()
    actual_cost = data.get("actual_cost", 0)
    actual_cost_breakdown = data.get("actual_cost_breakdown", [])

    booking.actual_cost = actual_cost
    booking.actual_cost_breakdown = actual_cost_breakdown
    db.commit()

    return {"status": "success", "message": "Actual cost updated"}
@router.get("/reviews", response_class=HTMLResponse)
async def caterer_reviews(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    all_reviews = user.caterer_profile.reviews
    total_reviews = len(all_reviews)
    avg_rating = sum(r.rating for r in all_reviews) / total_reviews if total_reviews > 0 else 0
    
    # Rating categories (5 to 1 stars)
    rating_stats = {i: 0 for i in range(5, 0, -1)}
    for r in all_reviews:
        if r.rating in rating_stats:
            rating_stats[r.rating] += 1
            
    return templates.TemplateResponse("caterer/reviews.html", {
        "request": request,
        "user": user,
        "reviews": sorted(all_reviews, key=lambda x: x.created_at, reverse=True),
        "avg_rating": round(float(avg_rating), 1),
        "total_reviews": total_reviews,
        "rating_stats": rating_stats,
        "active_page": "reviews"
    })
@router.post("/reviews/{review_id}/reply")
async def post_review_reply(
    review_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    data = await request.json()
    reply_text = data.get("reply")
    
    review = db.query(models.Review).filter(
        models.Review.id == review_id,
        models.Review.caterer_id == user.caterer_profile.id
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    

@router.post("/reviews/{review_id}/helpful")
async def toggle_review_helpful(
    review_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    review = db.query(models.Review).filter(
        models.Review.id == review_id,
        models.Review.caterer_id == user.caterer_profile.id
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.is_helpful = not review.is_helpful
    db.commit()
    return {"status": "success", "is_helpful": review.is_helpful}

@router.get("/customers", response_class=HTMLResponse)
async def caterer_customers(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    
    # Get unique customers and their stats
    customer_ids = {b.user_id for b in user.caterer_profile.bookings if b.user and not b.user.email.startswith("walkin@")}
    customers = []
    
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    first_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    
    total_customers_count = len(customer_ids)
    vip_customers_count = 0
    new_customers_this_month_count = 0
    repeat_customers_count = 0
    
    if customer_ids:
        raw_customers = db.query(models.User).filter(
            models.User.id.in_(customer_ids)
        ).all()
        
        for c in raw_customers:
            # Stats for this customer relative to THIS caterer
            all_bookings = db.query(models.Booking).filter(
                models.Booking.user_id == c.id,
                models.Booking.caterer_id == user.caterer_profile.id
            ).order_by(models.Booking.event_date.desc()).all()
            
            bookings_count = len(all_bookings)
            total_spent = sum(b.total_price for b in all_bookings if b.status == 'completed')
            last_booking = all_bookings[0] if all_bookings else None
            first_booking = all_bookings[-1] if all_bookings else None
            
            # Status Logic
            status = "REGULAR"
            if bookings_count >= 3:
                status = "VIP"
                vip_customers_count += 1
            
            if first_booking and first_booking.created_at >= first_of_month:
                status = "NEW"
                new_customers_this_month_count += 1
            
            if bookings_count > 1:
                repeat_customers_count += 1
            
            # Attach attributes for template
            c.total_bookings = bookings_count
            c.total_spent = total_spent
            c.last_booking_date = last_booking.event_date if last_booking else None
            c.status = status
            customers.append(c)

    repeat_rate = round((repeat_customers_count / total_customers_count * 100), 1) if total_customers_count > 0 else 0
    
    return templates.TemplateResponse("caterer/customers.html", {
        "request": request,
        "user": user,
        "customers": customers,
        "stats": {
            "total": total_customers_count,
            "vip": vip_customers_count,
            "new": new_customers_this_month_count,
            "repeat": f"{repeat_rate}%"
        },
        "active_page": "customers"
    })

@router.get("/api/payments/summary")
async def payments_summary_api(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    """Real-time summary of payment card totals — used by JS polling."""
    from datetime import datetime, timezone
    profile = user.caterer_profile
    bookings = [b for b in profile.bookings if b.status != 'draft' and not b.is_archived]

    released_payout = db.query(func.sum(models.PayoutItem.amount)).join(models.Payout).filter(
        models.Payout.caterer_id == profile.id,
        models.PayoutItem.status == 'released'
    ).scalar() or 0.0

    ready_payout = db.query(func.sum(models.PayoutItem.amount)).join(models.Payout).filter(
        models.Payout.caterer_id == profile.id,
        models.PayoutItem.status == 'ready'
    ).scalar() or 0.0

    escrow_payout = db.query(func.sum(models.PayoutItem.amount)).join(models.Payout).filter(
        models.Payout.caterer_id == profile.id,
        models.PayoutItem.status == 'escrowed'
    ).scalar() or 0.0

    booking_released = 0.0
    booking_escrow   = 0.0
    booking_pending  = 0.0
    active_count     = 0

    for b in bookings:
        if b.status in ('cancelled', 'rejected'):
            continue
        active_count += 1
        amount = float(b.total_amount or b.total_price or 0)

        if b.payment_status == 'paid' and b.status == 'completed':
            booking_released += amount
        elif b.payment_status == 'paid':
            booking_escrow += amount
        elif b.payment_status == 'deposit_paid':
            dp_pct = 0.20
            if b.quotation and b.quotation.downpayment_percent:
                dp_pct = b.quotation.downpayment_percent / 100.0
            deposit = amount * dp_pct
            booking_released += deposit
            booking_escrow   += (amount - deposit)
        else:
            booking_pending += amount

    has_payout_data = (released_payout + ready_payout + escrow_payout) > 0
    if has_payout_data:
        released_total = released_payout
        ready_total    = ready_payout
        escrow_total   = escrow_payout
    else:
        released_total = booking_released
        ready_total    = booking_pending
        escrow_total   = booking_escrow

    # Per-booking payment status counts
    status_counts = {"completed": 0, "partial": 0, "pending": 0}
    for b in bookings:
        if b.status in ('cancelled', 'rejected'):
            continue
        if b.payment_status == 'paid':
            status_counts["completed"] += 1
        elif b.payment_status == 'deposit_paid':
            status_counts["partial"] += 1
        else:
            status_counts["pending"] += 1

    return JSONResponse({
        "released_total": round(released_total, 2),
        "ready_total":    round(ready_total, 2),
        "escrow_total":   round(escrow_total, 2),
        "active_count":   active_count,
        "status_counts":  status_counts,
        "last_updated":   datetime.now(timezone.utc).isoformat()
    })

@router.get("/api/roi-analytics")

async def caterer_roi_analytics(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    from datetime import datetime
    import calendar
    from dateutil.relativedelta import relativedelta

    # Get last 6 months list
    now = datetime.now()
    months_labels = []
    projected_revenue = []
    actual_costs = []
    projected_costs = []

    for i in range(5, -1, -1):
        target_month = now - relativedelta(months=i)
        month_label = target_month.strftime("%b %Y")
        months_labels.append(month_label)
        
        # Calculate stats for this month
        month_bookings = db.query(models.Booking).filter(
            models.Booking.caterer_id == user.caterer_profile.id,
            models.Booking.status == 'completed',
            func.extract('month', models.Booking.event_date) == target_month.month,
            func.extract('year', models.Booking.event_date) == target_month.year
        ).all()
        
        rev = sum(b.total_price or 0 for b in month_bookings)
        act_cost = sum(b.actual_cost or 0 for b in month_bookings)
        
        proj_cost = 0
        for b in month_bookings:
            c = 0
            if b.package:
                c += (b.package.cost_price or 0) * (b.guest_count if b.package.price_unit == 'per_guest' else 1)
            for item in b.selected_items:
                c += (item.menu_item.cost_price or 0)
            proj_cost += c
            
        projected_revenue.append(float(rev))
        actual_costs.append(float(act_cost))
        projected_costs.append(float(proj_cost))

    return {
        "labels": months_labels,
        "revenue": projected_revenue,
        "actual_costs": actual_costs,
        "projected_costs": projected_costs
    }

@router.get("/calendar", response_class=HTMLResponse)
async def caterer_calendar(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    from datetime import date
    current_date = date.today()
    
    # For the list view on the side
    # For the list view on the side (Status Tracker) - Show active non-completed bookings first
    tracker_bookings = db.query(models.Booking).filter(
        models.Booking.caterer_id == user.caterer_profile.id,
        models.Booking.status.in_(['confirmed', 'preparing', 'ready_for_delivery', 'on_the_way', 'arrived', 'setup_ongoing']),
        models.Booking.is_archived == False
    ).order_by(models.Booking.event_date.asc()).all()
    # For the walk-in form options
    packages = db.query(models.CateringPackage).filter(
        models.CateringPackage.caterer_id == user.caterer_profile.id,
        models.CateringPackage.is_active == True,
        models.CateringPackage.status != 'archived'
    ).all()
    
    menu_items = db.query(models.MenuItem).filter(
        models.MenuItem.caterer_id == user.caterer_profile.id,
        models.MenuItem.is_archived == False
    ).all()
    
    return templates.TemplateResponse("caterer/calendar.html", {
        "request": request,
        "user": user,
        "bookings": tracker_bookings,
        "current_date": current_date,
        "packages": packages,
        "menu_items": menu_items,
        "active_page": "calendar"
    })

@router.get("/packages", response_class=HTMLResponse)
async def manage_packages(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    active_packages = [p for p in profile.packages if p.status != 'archived']
    active_menu = [m for m in profile.menu_items if not m.is_archived]
    
    return templates.TemplateResponse("caterer/packages.html", {
        "request": request,
        "user": user,
        "packages": active_packages,
        "menu_items": active_menu,
        "active_page": "packages"
    })

@router.get("/menu", response_class=HTMLResponse)
async def manage_menu(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    active_menu = [m for m in user.caterer_profile.menu_items if not m.is_archived]
    return templates.TemplateResponse("caterer/menu.html", {
        "request": request,
        "user": user,
        "menu_items": active_menu,
        "active_page": "menu"
    })

@router.get("/profile", response_class=HTMLResponse)
async def edit_profile(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    return templates.TemplateResponse("caterer/profile_edit.html", {
        "request": request,
        "user": user,
        "profile": user.caterer_profile,
        "active_page": "profile"
    })

@router.post("/packages/add")
async def add_package(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    service_type: str = Form("General"),
    service_duration: int = Form(8),
    price_per_head: float = Form(0.0),
    cost_price: float = Form(0.0),
    cost_breakdown: Optional[str] = Form(None),
    markup_type: str = Form("percentage"),
    markup_value: float = Form(0.0),
    min_contract_amount: float = Form(0.0),
    min_guests: int = Form(1),
    max_guests: Optional[int] = Form(None),
    inclusions: Optional[List[str]] = Form(None),
    linked_menu_ids: Optional[List[int]] = Form(None),
    image: Optional[UploadFile] = File(None),
    base_pax: int = Form(50),
    labor_cost: float = Form(0.0),
    utility_cost: float = Form(0.0),
    equipment_cost: float = Form(0.0),
    internal_cost_per_pax: float = Form(0.0),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    image_url = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1]
        filename = f"pkg_{uuid.uuid4()}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = f"/static/uploads/caterer/{filename}"

    new_pkg = models.CateringPackage(
        caterer_id=user.caterer_profile.id,
        name=name,
        description=description,
        service_type=service_type,
        service_duration=service_duration,
        price_per_head=price_per_head,
        price=price_per_head, # Sync for compatibility
        cost_price=cost_price,
        cost_breakdown=json.loads(cost_breakdown) if cost_breakdown else [],
        markup_type=markup_type,
        markup_value=markup_value,
        min_contract_amount=min_contract_amount,
        min_guests=min_guests,
        max_guests=max_guests,
        image_url=image_url,
        inclusions={inc: True for inc in inclusions} if inclusions else {},
        base_pax=base_pax,
        labor_cost=labor_cost,
        utility_cost=utility_cost,
        equipment_cost=equipment_cost,
        internal_cost_per_pax=internal_cost_per_pax,
        is_active=True,
        status='active'
    )
    
    # Handle linked menu items
    if linked_menu_ids:
        items = db.query(models.MenuItem).filter(
            models.MenuItem.id.in_(linked_menu_ids),
            models.MenuItem.caterer_id == user.caterer_profile.id
        ).all()
        new_pkg.menu_items = items

    db.add(new_pkg)
    db.commit()
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({
            "status": "success", 
            "message": "Package added successfully", 
            "package_id": new_pkg.id,
            "package_name": new_pkg.name
        })

    return RedirectResponse(url="/caterer/packages?success_msg=Package+added+successfully", status_code=303)

@router.post("/packages/{package_id}/toggle")
async def toggle_package_status(
    package_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    package.is_active = not package.is_active
    db.commit()
    return {"status": "success", "is_active": package.is_active}

@router.post("/menu/add")
async def add_menu_item(
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(0.0),
    cost_price: float = Form(0.0),
    cost_breakdown: Optional[str] = Form(None),
    serving_size: Optional[str] = Form(None),
    is_addon: bool = Form(False),
    addon_price: float = Form(0.0),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    image_url = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1]
        filename = f"menu_{uuid.uuid4()}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = f"/static/uploads/caterer/{filename}"

    new_item = models.MenuItem(
        caterer_id=user.caterer_profile.id,
        name=name,
        category=category,
        description=description,
        price=price,
        cost_price=cost_price,
        cost_breakdown=json.loads(cost_breakdown) if cost_breakdown else None,
        serving_size=serving_size,
        is_addon=is_addon,
        addon_price=addon_price,
        image_url=image_url,
        is_archived=False
    )
    db.add(new_item)
    db.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({
            "status": "success", 
            "message": "Menu item added successfully", 
            "item_id": new_item.id,
            "item_name": new_item.name
        })

    return RedirectResponse(url="/caterer/menu?success_msg=Menu+item+added+successfully", status_code=303)

@router.post("/profile")
async def update_profile(
    request: Request,
    business_name: str = Form(...),
    description: str = Form(...),
    city: str = Form(...),
    contact_phone: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    personal_address: Optional[str] = Form(None),
    logo: Optional[UploadFile] = File(None),
    cover_image: Optional[UploadFile] = File(None),
    gcash_number: Optional[str] = Form(None),
    gcash_qr: Optional[UploadFile] = File(None),
    maya_number: Optional[str] = Form(None),
    maya_qr: Optional[UploadFile] = File(None),
    bank_name: Optional[str] = Form(None),
    bank_account_name: Optional[str] = Form(None),
    bank_account_number: Optional[str] = Form(None),
    bank_qr: Optional[UploadFile] = File(None),
    card_bank: Optional[str] = Form(None),
    card_holder_name: Optional[str] = Form(None),
    card_number: Optional[str] = Form(None),
    cash_instructions: Optional[str] = Form(None),
    booking_policy: Optional[str] = Form(None),
    payment_policy: Optional[str] = Form(None),
    cancellation_policy: Optional[str] = Form(None),
    primary_color: Optional[str] = Form(None),
    secondary_color: Optional[str] = Form(None),
    accent_color: Optional[str] = Form(None),
    highlight_color: Optional[str] = Form(None),
    font_family: Optional[str] = Form(None),
    border_radius: Optional[int] = Form(None),
    sidebar_mode: Optional[str] = Form("full"),
    show_platform_logo: bool = Form(False),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    contact_address: Optional[str] = Form(None),
    gallery: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    
    # Update User Info
    user.first_name = first_name
    user.last_name = last_name
    user.address = personal_address
    
    # Update Profile Info
    profile.business_name = business_name
    profile.description = description
    profile.city = city
    if contact_address:
        profile.contact_address = contact_address
    profile.contact_phone = contact_phone
    profile.gcash_number = gcash_number
    profile.maya_number = maya_number
    profile.bank_name = bank_name
    profile.bank_account_name = bank_account_name
    profile.bank_account_number = bank_account_number
    profile.card_bank = card_bank
    profile.card_holder_name = card_holder_name
    profile.card_number = card_number
    profile.cash_instructions = cash_instructions
    profile.booking_policy = booking_policy
    profile.payment_policy = payment_policy
    profile.cancellation_policy = cancellation_policy
    profile.primary_color = primary_color
    profile.secondary_color = secondary_color
    profile.accent_color = accent_color
    profile.highlight_color = highlight_color
    profile.font_family = font_family
    profile.border_radius = border_radius
    profile.sidebar_mode = sidebar_mode
    profile.show_platform_logo = show_platform_logo
    
    if latitude is not None:
        profile.latitude = latitude
    if longitude is not None:
        profile.longitude = longitude

    # Handle Single File Uploads
    for field_name, file_obj in [("logo", logo), ("cover_image", cover_image), ("gcash_qr", gcash_qr), ("maya_qr", maya_qr), ("bank_qr", bank_qr)]:
        if file_obj and file_obj.filename:
            ext = os.path.splitext(file_obj.filename)[1]
            filename = f"{field_name}_{uuid.uuid4()}{ext}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(file_obj.file, buffer)
            setattr(profile, f"{field_name}_url" if field_name != 'logo' else 'logo_url', f"/static/uploads/caterer/{filename}")

    # Handle Gallery Uploads (Multiple)
    if gallery:
        for file_obj in gallery:
            if file_obj.filename:
                ext = os.path.splitext(file_obj.filename)[1]
                filename = f"gallery_{uuid.uuid4()}{ext}"
                filepath = os.path.join(UPLOAD_DIR, filename)
                with open(filepath, "wb") as buffer:
                    shutil.copyfileobj(file_obj.file, buffer)
                
                new_gallery_item = models.CatererGallery(
                    caterer_id=profile.id,
                    media_url=f"/static/uploads/caterer/{filename}",
                    media_type="image"
                )
                db.add(new_gallery_item)

    db.commit()
    return RedirectResponse(url="/caterer/profile?success_msg=Business+profile+updated+successfully", status_code=303)

@router.get("/packages/{package_id}/details")
async def get_package_details_api(
    package_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    return {
        "id": package.id,
        "name": package.name,
        "description": package.description,
        "service_type": package.service_type,
        "price_per_head": package.price_per_head,
        "cost_price": package.cost_price,
        "cost_breakdown": package.cost_breakdown or [],
        "markup_type": package.markup_type or 'percentage',
        "markup_value": package.markup_value or 0,
        "min_contract_amount": package.min_contract_amount,
        "min_guests": package.min_guests,
        "max_guests": package.max_guests,
        "service_duration": package.service_duration,
        "image_url": package.image_url,
        "inclusions": package.inclusions or {},
        "is_active": package.is_active,
        "base_pax": package.base_pax,
        "labor_cost": package.labor_cost,
        "utility_cost": package.utility_cost,
        "equipment_cost": package.equipment_cost,
        "ingredient_total_cost": package.ingredient_total_cost,
        "internal_cost_per_pax": package.internal_cost_per_pax
    }

@router.post("/packages/{package_id}/update")
async def update_package(
    request: Request,
    package_id: int,
    name: str = Form(...),
    description: str = Form(...),
    service_type: str = Form("General"),
    service_duration: int = Form(8),
    price_per_head: float = Form(0.0),
    cost_price: float = Form(0.0),
    cost_breakdown: Optional[str] = Form(None),
    markup_type: str = Form("percentage"),
    markup_value: float = Form(0.0),
    min_contract_amount: float = Form(0.0),
    min_guests: int = Form(1),
    max_guests: Optional[int] = Form(None),
    inclusions: Optional[List[str]] = Form(None),
    linked_menu_ids: Optional[List[int]] = Form(None),
    image: Optional[UploadFile] = File(None),
    base_pax: int = Form(50),
    labor_cost: float = Form(0.0),
    utility_cost: float = Form(0.0),
    equipment_cost: float = Form(0.0),
    internal_cost_per_pax: float = Form(0.0),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    package.name = name
    package.description = description
    package.service_type = service_type
    package.service_duration = service_duration
    package.price_per_head = price_per_head
    package.price = price_per_head # Sync for compatibility
    package.cost_price = cost_price
    if cost_breakdown is not None:
        package.cost_breakdown = json.loads(cost_breakdown) if cost_breakdown else None
    package.min_contract_amount = min_contract_amount
    package.min_guests = min_guests
    package.max_guests = max_guests
    package.base_pax = base_pax
    package.labor_cost = labor_cost
    package.utility_cost = utility_cost
    package.equipment_cost = equipment_cost
    package.internal_cost_per_pax = internal_cost_per_pax
    package.markup_type = markup_type
    package.markup_value = markup_value
    
    # Process inclusions into a dict for storage
    if inclusions:
        package.inclusions = {inc: True for inc in inclusions}
    else:
        package.inclusions = {}

    # Handle linked menu items
    if linked_menu_ids is not None:
        items = db.query(models.MenuItem).filter(
            models.MenuItem.id.in_(linked_menu_ids),
            models.MenuItem.caterer_id == user.caterer_profile.id
        ).all()
        package.menu_items = items


    if image and image.filename:
        ext = os.path.splitext(image.filename)[1]
        filename = f"pkg_{uuid.uuid4()}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        package.image_url = f"/static/uploads/caterer/{filename}"

    db.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({
            "status": "success", 
            "message": "Package updated successfully", 
            "package_id": package.id,
            "package_name": package.name
        })

    return RedirectResponse(url="/caterer/packages", status_code=303)

@router.post("/packages/{package_id}/archive")
async def archive_package_caterer(
    package_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    package.status = 'archived'
    package.is_active = False
    db.commit()

    # Broadcast update
    await manager.broadcast_to_user(user.id, {
        "type": "package_archived",
        "package_id": package_id,
        "message": f"Package '{package.name}' archived."
    })
    
    return JSONResponse({"status": "success", "message": "Package archived successfully", "package_id": package_id})

@router.post("/packages/{package_id}/toggle-status")
async def toggle_package_status(
    package_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    package.is_active = not package.is_active
    db.commit()
    
    return JSONResponse({
        "status": "success", 
        "is_active": package.is_active,
        "message": f"Package '{package.name}' is now {'active' if package.is_active else 'hidden'}."
    })

@router.get("/packages/{package_id}/menu")
async def get_package_menu(
    package_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "image_url": item.image_url,
            "is_addon": item.is_addon
        }
        for item in package.menu_items
    ]

@router.post("/packages/{package_id}/menu/add")
async def add_menu_to_package(
    package_id: int,
    name: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    cost_price: float = Form(0.0),
    cost_breakdown: Optional[str] = Form(None),
    is_addon: bool = Form(False),
    addon_price: float = Form(0.0),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    # First check package
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    image_url = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1]
        filename = f"menu_{uuid.uuid4()}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = f"/static/uploads/caterer/{filename}"

    new_item = models.MenuItem(
        caterer_id=user.caterer_profile.id,
        name=name,
        category=category,
        description=description,
        cost_price=cost_price,
        cost_breakdown=json.loads(cost_breakdown) if cost_breakdown else None,
        is_addon=is_addon,
        addon_price=addon_price,
        image_url=image_url,
        is_archived=False
    )
    db.add(new_item)
    db.flush() # Get ID
    
    # Link to package
    package.menu_items.append(new_item)
    db.commit()
    return {"status": "success", "item_id": new_item.id}

@router.post("/packages/{package_id}/menu/{item_id}/unlink")
async def unlink_menu_from_package(
    package_id: int,
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    item = next((i for i in package.menu_items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not linked to this package")
    
    package.menu_items.remove(item)
    db.commit()
    return {"status": "success"}

@router.get("/api/menu")
async def get_all_menu_items_api(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    items = db.query(models.MenuItem).filter(
        models.MenuItem.caterer_id == user.caterer_profile.id,
        models.MenuItem.is_archived == False
    ).all()
    return [
        {
            "id": i.id,
            "name": i.name,
            "category": i.category,
            "image_url": i.image_url
        }
        for i in items
    ]

@router.post("/packages/{package_id}/menu/link")
async def link_menu_to_package(
    package_id: int,
    item_id: int = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    item = db.query(models.MenuItem).filter(
        models.MenuItem.id == item_id,
        models.MenuItem.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item not in package.menu_items:
        package.menu_items.append(item)
        db.commit()
    
    return {"status": "success"}

@router.post("/menu/{item_id}/update")
async def update_menu_item(
    request: Request,
    item_id: int,
    name: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(0.0),
    cost_price: float = Form(0.0),
    cost_breakdown: Optional[str] = Form(None),
    serving_size: Optional[str] = Form(None),
    is_addon: bool = Form(False),
    addon_price: float = Form(0.0),
    base_pax: int = Form(50),
    labor_cost: float = Form(0.0),
    utility_cost: float = Form(0.0),
    equipment_cost: float = Form(0.0),
    internal_cost_per_pax: float = Form(0.0),
    dietary_tags: Optional[list[str]] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.MenuItem).filter(
        models.MenuItem.id == item_id,
        models.MenuItem.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    item.name = name
    item.category = category
    item.description = description
    item.price = price
    item.cost_price = cost_price
    if cost_breakdown is not None:
        item.cost_breakdown = json.loads(cost_breakdown) if cost_breakdown else None
    item.serving_size = serving_size
    item.is_addon = is_addon
    item.addon_price = addon_price
    item.dietary_tags = dietary_tags
    
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1]
        filename = f"menu_{uuid.uuid4()}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        item.image_url = f"/static/uploads/caterer/{filename}"

    db.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({
            "status": "success", 
            "message": "Menu item updated successfully", 
            "item_id": item.id,
            "item_name": item.name
        })

    return RedirectResponse(url="/caterer/menu?success_msg=Menu+item+updated+successfully", status_code=303)

@router.post("/menu/{item_id}/archive")
async def archive_menu_item_caterer(
    request: Request,
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.MenuItem).filter(
        models.MenuItem.id == item_id,
        models.MenuItem.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    item.is_archived = True
    db.commit()

    # Broadcast update
    await manager.broadcast_to_user(user.id, {
        "type": "menu_archived",
        "item_id": item_id,
        "message": f"Dish '{item.name}' archived."
    })
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Menu item archived successfully", "item_id": item_id})

    return RedirectResponse(url="/caterer/menu?success_msg=Menu+item+archived+successfully", status_code=303)

@router.post("/profile/change-password")
async def change_password_caterer(
    current_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    if not auth.verify_password(current_password, user.password_hash):
        return {"success": False, "message": "Incorrect current password"}
    
    user.password_hash = auth.get_password_hash(new_password)
    db.commit()
    return {"success": True}

@router.post("/api/availability/toggle")
async def toggle_availability(
    data: dict,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(auth.get_current_user) # Using current user instead of caterer_only to be safer with dict parsing
):
    if user.role != "caterer":
        raise HTTPException(status_code=403, detail="Caterer only")
        
    date_str = data.get("date")
    is_available = data.get("is_available", False)
    reason = data.get("reason", "")
    
    from datetime import datetime
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    # Check if entry already exists
    existing = db.query(models.Availability).filter(
        models.Availability.caterer_id == user.caterer_profile.id,
        models.Availability.date == target_date
    ).first()
    
    if existing:
        existing.is_available = is_available
        existing.reason = reason
    else:
        new_avail = models.Availability(
            caterer_id=user.caterer_profile.id,
            date=target_date,
            is_available=is_available,
            reason=reason
        )
        db.add(new_avail)
    
    db.commit()
    return {"status": "success"}
@router.post("/api/sidebar-mode")
async def toggle_sidebar_mode(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    try:
        data = await request.json()
    except:
        data = {}
        
    mode = data.get("mode", "full")
    if mode not in ["full", "icons"]:
        mode = "full"
    
    user.caterer_profile.sidebar_mode = mode
    db.commit()
    return {"status": "success", "mode": mode}

@router.get("/api/events")
async def get_calendar_events(
    caterer_id: Optional[int] = None,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(auth.get_current_user_optional)
):
    # Use provided caterer_id (for customers) or user's caterer profile (for caterers themselves)
    target_caterer_id = caterer_id
    if not target_caterer_id and user and user.role == 'caterer':
        target_caterer_id = user.caterer_profile.id
    
    if not target_caterer_id:
        return []

    bookings = db.query(models.Booking).filter(
        models.Booking.caterer_id == target_caterer_id,
        models.Booking.status.in_(['confirmed', 'preparing', 'ready_for_delivery', 'on_the_way', 'arrived', 'setup_ongoing', 'completed']),
        models.Booking.is_archived == False
    ).all()
    
    events = []
    colors = {
        "Wedding": "#ec4899", # Pink
        "Birthday": "#3b82f6", # Blue
        "Corporate": "#10b981", # Green
        "Private Party": "#f59e0b" # Orange
    }
    
    # Check if we should show full details (only for the caterer owner)
    is_owner = user and user.role == 'caterer' and user.caterer_profile.id == target_caterer_id

    for b in bookings:
        start_dt = str(b.event_date)
        if b.event_time:
            start_dt += f"T{b.event_time}"
            
        event_data = {
            "id": b.id,
            "start": start_dt,
            "backgroundColor": colors.get(b.event_type, "#6366f1"),
            "borderColor": colors.get(b.event_type, "#6366f1"),
        }

        if is_owner:
            customer_name = f"{b.user.first_name} {b.user.last_name}" if b.user else "Unknown Customer"
            customer_first_name = b.user.first_name if b.user else "Customer"
            event_data["title"] = f"{b.event_type or 'Event'} - {b.event_name or customer_first_name}"
            event_data["extendedProps"] = {
                "customer": customer_name,
                "type": b.event_type or "N/A",
                "guests": b.guest_count,
                "venue": b.venue_address or "TBD",
                "package": b.package.name if b.package else "Custom",
                "time": str(b.event_time) if b.event_time else "TBD"
            }
        else:
            event_data["title"] = "BOOKED"
            event_data["display"] = "background"
            event_data["overlap"] = False

        events.append(event_data)
        
    # Add blocked dates from availability
    availabilities = db.query(models.Availability).filter(
        models.Availability.caterer_id == target_caterer_id,
        models.Availability.is_available == False
    ).all()
    
    for a in availabilities:
        events.append({
            "title": "BLOCKED",
            "start": str(a.date),
            "allDay": True,
            "backgroundColor": "#f43f5e",
            "borderColor": "#e11d48",
            "textColor": "#ffffff",
            "extendedProps": {
                "type": "BLOCKED",
                "reason": a.reason or "No reason provided",
                "customer": "N/A"
            }
        })
        
    return events

@router.post("/api/bookings/{booking_id}/reminders")
async def set_booking_reminder(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Simple logic: create a notification for the caterer
    new_notif = models.Notification(
        user_id=user.id,
        title=f"Reminder: {booking.event_name or 'Event'}",
        message=f"Preparation reminder for {booking.event_name} on {booking.event_date}.",
        type="reminder"
    )
    db.add(new_notif)
    db.commit()

    # Real-time WebSocket Alert to Caterer
    import asyncio
    asyncio.create_task(manager.broadcast_to_user(user.id, {
        "type": "new_notification",
        "message": f"Reminder set: {booking.event_name}",
        "count": db.query(models.Notification).filter(models.Notification.user_id == user.id, models.Notification.is_read == False).count()
    }))

    return {"status": "success", "message": "Reminder set successfully"}


@router.get("/notifications", response_class=HTMLResponse)
async def caterer_notifications(
    request: Request, 
    page: int = 1,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
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
    
    return templates.TemplateResponse("caterer/notifications.html", {
        "request": request,
        "user": user,
        "notifications": notifications,
        "active_page": "notifications",
        "current_page": page,
        "total_pages": total_pages,
        "total_notifications": total_notifications
    })

@router.post("/bookings/{booking_id}/cancel")
async def cancel_booking(
    request: Request,
    booking_id: int,
    reason: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking.status = "cancelled"
    
    history = models.BookingHistory(
        booking_id=booking.id,
        status="cancelled",
        notes=f"Booking cancelled by caterer. Reason: {reason}"
    )
    db.add(history)
    db.commit()
    
    # Broadcast update to sync other caterer tabs
    await manager.broadcast_to_user(user.id, {
        "type": "dashboard_update",
        "message": "Stats updated: Booking cancelled."
    })
    await manager.broadcast_to_user(user.id, {
        "type": "booking_update",
        "booking_id": booking_id,
        "new_status": "cancelled",
        "message": f"Booking #{booking_id} has been cancelled."
    })
    
    # Notify Customer
    from ..services.notification import NotificationService
    import asyncio
    asyncio.create_task(NotificationService.notify_status_update(
        db, 
        booking.user_id, 
        "Booking Cancelled ❌", 
        f"Ang iyong booking para sa '{booking.event_name}' ay kinansela ni {user.caterer_profile.business_name}. Reason: {reason}", 
        f"/customer/bookings"
    ))
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Booking cancelled successfully", "new_status": "cancelled"})

    return RedirectResponse(url="/caterer/bookings?success_msg=Booking+cancelled+successfully", status_code=303)

@router.post("/bookings/{booking_id}/accept")
async def accept_booking(
    request: Request,
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking.status = 'confirmed'
    history = models.BookingHistory(booking_id=booking.id, status='confirmed', notes="Booking accepted by caterer manually.")
    db.add(history)
    db.commit()

    
    return JSONResponse({"status": "success", "message": "Booking accepted", "new_status": "confirmed"})

@router.post("/bookings/{booking_id}/reject")
async def reject_booking(
    request: Request,
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking.status = 'cancelled'
    history = models.BookingHistory(booking_id=booking.id, status='cancelled', notes="Booking rejected by caterer.")
    db.add(history)
    db.commit()

    await manager.broadcast_to_user(user.id, {
        "type": "booking_update",
        "booking_id": booking_id,
        "new_status": "cancelled",
        "message": "Booking rejected."
    })
    
    # Notify Customer
    from ..services.notification import NotificationService
    import asyncio
    asyncio.create_task(NotificationService.notify_status_update(
        db, 
        booking.user_id, 
        "Booking Rejected ❌", 
        f"Pasensya na, hindi tinanggap ni {user.caterer_profile.business_name} ang iyong booking request para sa '{booking.event_name}'.", 
        f"/customer/bookings"
    ))
    
    return JSONResponse({"status": "success", "message": "Booking rejected", "new_status": "cancelled"})

@router.post("/bookings/{booking_id}/complete")
async def complete_booking(
    request: Request,
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking.status = 'completed'
    history = models.BookingHistory(booking_id=booking.id, status='completed', notes="Event marked as completed by caterer.")
    db.add(history)
    db.commit()

    await manager.broadcast_to_user(user.id, {
        "type": "booking_update",
        "booking_id": booking_id,
        "new_status": "completed",
        "message": "Booking completed."
    })
    
    # Notify Customer
    from ..services.notification import NotificationService
    import asyncio
    asyncio.create_task(NotificationService.notify_status_update(
        db, 
        booking.user_id, 
        "Event Service Completed 🌟", 
        f"Salamat! Ang iyong event '{booking.event_name}' ay itinalaga bilang COMPLETED ni {user.caterer_profile.business_name}. Huwag kalimutang i-rate ang kanilang serbisyo!", 
        f"/customer/reviews"
    ))
    
    return JSONResponse({"status": "success", "message": "Booking completed", "new_status": "completed"})

@router.post("/bookings/{booking_id}/archive")
async def archive_booking(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.caterer_id == user.caterer_profile.id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking.is_archived = True
    db.commit()
    
    # WebSocket Broadcast for real-time removal from dashboard & stats refresh
    await manager.broadcast_to_user(user.id, {
        "type": "dashboard_update",
        "message": "Stats updated: Booking archived."
    })
    await manager.broadcast_to_user(user.id, {
        "type": "booking_archived",
        "booking_id": booking_id,
        "message": "Booking has been archived successfully."
    })
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Booking archived successfully", "booking_id": booking_id})

    # Allow redirecting back to where the request came from (e.g., payments page)
    next_url = request.query_params.get("next", "/caterer/bookings")
    if "?" in next_url:
        next_url += "&success_msg=Booking+archived+successfully"
    else:
        next_url += "?success_msg=Booking+archived+successfully"
    return RedirectResponse(url=next_url, status_code=303)

@router.post("/bookings/{booking_id}/restore")
async def restore_booking(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.caterer_id == user.caterer_profile.id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking.is_archived = False
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Booking+restored+successfully", status_code=303)

@router.post("/gallery/{item_id}/restore")
async def restore_gallery_item(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.CatererGallery).filter(
        models.CatererGallery.id == item_id,
        models.CatererGallery.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Gallery item not found")
    
    item.is_archived = False
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Gallery+item+restored+successfully", status_code=303)

@router.post("/packages/{package_id}/restore")
async def restore_package(
    package_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    package.status = 'active'
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Package+restored+successfully", status_code=303)

@router.post("/menu/{item_id}/restore")
async def restore_menu_item(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.MenuItem).filter(
        models.MenuItem.id == item_id,
        models.MenuItem.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    item.is_archived = False
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Menu+item+restored+successfully", status_code=303)

@router.post("/bookings/{booking_id}/delete")
async def delete_booking_permanent(
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.caterer_id == user.caterer_profile.id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(booking)
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Booking+permanently+deleted", status_code=303)

@router.post("/packages/{package_id}/delete")
async def delete_package_permanent(
    package_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    db.delete(package)
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Package+permanently+deleted", status_code=303)

@router.post("/menu/{item_id}/delete")
async def delete_menu_item_permanent(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.MenuItem).filter(
        models.MenuItem.id == item_id,
        models.MenuItem.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    db.delete(item)
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Menu+item+permanently+deleted", status_code=303)

@router.post("/gallery/{item_id}/delete")
async def delete_gallery_item_permanent(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.CatererGallery).filter(
        models.CatererGallery.id == item_id,
        models.CatererGallery.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Gallery item not found")
    db.delete(item)
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Gallery+photo+permanently+deleted", status_code=303)

@router.post("/ingredients/{item_id}/restore")
async def restore_ingredient(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.Ingredient).filter(
        models.Ingredient.id == item_id,
        models.Ingredient.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    item.is_archived = False
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Ingredient+restored+successfully", status_code=303)

@router.post("/ingredients/{item_id}/delete")
async def delete_ingredient_permanent(
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    item = db.query(models.Ingredient).filter(
        models.Ingredient.id == item_id,
        models.Ingredient.caterer_id == user.caterer_profile.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    db.delete(item)
    db.commit()
    return RedirectResponse(url="/caterer/archives?success_msg=Ingredient+permanently+deleted", status_code=303)

@router.get("/messages", response_class=HTMLResponse)
async def caterer_messages(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    """Render the chat messaging interface for the caterer."""
    return templates.TemplateResponse("caterer/messages.html", {
        "request": request,
        "user": user,
        "active_page": "messages"
    })

@router.post("/api/check-customer")
async def check_customer(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    data = await request.json()
    email = data.get("email", "").strip()
    name = data.get("name", "").strip()

    query = db.query(models.User).filter(models.User.role == 'customer')
    
    target = None
    if email and "@" in email:
        target = query.filter(models.User.email.ilike(email)).first()

    # Then by name using ilike if email is missing or not found
    if not target and name and len(name) > 2:
        parts = name.split()
        if len(parts) >= 2:
            target = query.filter(
                models.User.first_name.ilike(f"%{parts[0]}%"),
                models.User.last_name.ilike(f"%{parts[-1]}%")
            ).first()
        else:
            target = query.filter(
                models.User.first_name.ilike(f"%{name}%") |
                models.User.last_name.ilike(f"%{name}%")
            ).first()

    if target:
        full_name = f"{target.first_name or ''} {target.last_name or ''}".strip()
        email_taken = False
        if email and target.email and email.lower() == target.email.lower():
            email_taken = True
            
        return {
            "exists": True, 
            "is_taken": email_taken,
            "match_type": "email" if email_taken else "name",
            "name": full_name or target.email, 
            "email": target.email, 
            "contact": target.phone_number,
            "message": "Existing customer found." if email_taken else "Similar name found."
        }
        
    return {"exists": False}

@router.get("/reviews", response_class=HTMLResponse)
async def manage_reviews_page(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    reviews = db.query(models.Review).filter(models.Review.caterer_id == profile.id).order_by(models.Review.created_at.desc()).all()
    
    return templates.TemplateResponse("caterer/manage_reviews.html", {
        "request": request,
        "user": user,
        "profile": profile,
        "reviews": reviews,
        "active_page": "reviews"
    })

@router.post("/reviews/{review_id}/highlight")
async def toggle_review_highlight(
    review_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    review = db.query(models.Review).filter(models.Review.id == review_id, models.Review.caterer_id == profile.id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.is_highlighted = not review.is_highlighted
    db.commit()
    
    return {"success": True, "is_highlighted": review.is_highlighted}

@router.post("/reviews/{review_id}/reply")
async def reply_to_review(
    review_id: int,
    reply_text: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    review = db.query(models.Review).filter(models.Review.id == review_id, models.Review.caterer_id == profile.id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.caterer_reply = reply_text.strip()
    db.commit()
    
    return RedirectResponse(url="/caterer/reviews?success_msg=Reply+submitted!", status_code=303)

@router.get("/compliance", response_class=HTMLResponse)
async def view_compliance_queue(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    # Fetch all customers who have booked with this caterer
    customers = db.query(models.User).join(models.Booking).filter(
        models.Booking.caterer_id == profile.id,
        models.User.role == "customer",
        models.User.is_archived == False
    ).distinct().all()

    # KYC records & Bookings mapping
    user_ids = [c.id for c in customers]
    kyc_requests = db.query(models.IdentityVerification).filter(
        models.IdentityVerification.user_id.in_(user_ids) if user_ids else False,
        models.IdentityVerification.is_archived == False
    ).all()
    kyc_map = {k.user_id: k for k in kyc_requests}

    # Categorization and Labels
    package_customers = []
    package_map = {}

    for customer in customers:
        # Get all relevant package bookings for this customer with this caterer
        user_bookings = db.query(models.Booking).filter(
            models.Booking.user_id == customer.id, 
            models.Booking.caterer_id == profile.id,
            models.Booking.event_type != "Ala Carte Order"
        ).order_by(models.Booking.created_at.desc()).all()
        
        if not user_bookings:
            continue

        package_customers.append(customer)
        latest = user_bookings[0]
        package_map[customer.id] = latest.event_type if len(user_bookings) == 1 else f"{latest.event_type} (+{len(user_bookings)-1} more)"
            
        # Flag for the Multi-Order badge UI
        customer.has_multiple_orders = (len(user_bookings) > 1)

    return templates.TemplateResponse("caterer/compliance.html", {
        "request": request,
        "user": user,
        "package_customers": package_customers,
        "kyc_map": kyc_map,
        "package_map": package_map,
        "active_page": "compliance"
    })



@router.get("/compliance/view/{user_id}", response_class=HTMLResponse)
async def view_customer_verification(
    user_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    # Verify this customer has a booking with this caterer
    booking = db.query(models.Booking).filter(
        models.Booking.caterer_id == profile.id,
        models.Booking.user_id == user_id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=403, detail="You do not have access to this user's verification data.")

    target_user = db.query(models.User).get(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    verification = target_user.identity_verification
    if not verification:
        return RedirectResponse(url="/caterer/compliance?error_msg=No+verification+data+found+for+this+user.")

    # Fetch relevant bookings for historical context
    bookings = db.query(models.Booking).filter(
        models.Booking.caterer_id == profile.id,
        models.Booking.user_id == user_id
    ).order_by(models.Booking.created_at.desc()).all()

    return templates.TemplateResponse("caterer/compliance_verify.html", {
        "request": request,
        "user": user,
        "target_user": target_user,
        "verification": verification,
        "bookings": bookings,
        "active_page": "compliance"
    })

@router.post("/compliance/{user_id}/verify")
async def verify_customer_compliance(
    user_id: int,
    action: str = Form(...),
    reason: Optional[str] = Form(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    # Verify this customer has a booking with this caterer
    booking = db.query(models.Booking).filter(
        models.Booking.caterer_id == profile.id,
        models.Booking.user_id == user_id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=403, detail="Unauthorized")

    target_user = db.query(models.User).get(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    kyc_record = target_user.identity_verification
    
    if action == "approve":
        target_user.is_verified = True
        target_user.is_kyc_complete = True
        if kyc_record:
            kyc_record.verification_status = "approved"
            kyc_record.verified_at = func.now()
        
        # Also update all bookings for this user with this caterer
        db.query(models.Booking).filter(
            models.Booking.user_id == user_id,
            models.Booking.caterer_id == profile.id
        ).update({"ocr_verified": True, "liveness_verified": True})

        # NOTIFY: Real-time update for customer
        await NotificationService.notify_status_update(
            db, user_id, 
            "Identity Approved!", 
            f"Your identity has been verified by {profile.business_name}. You may now proceed with your booking.",
            f"/bookings/step/quotation/{booking.id}",
            "kyc_update"
        )
            
    elif action == "reject":
        if kyc_record:
            kyc_record.verification_status = "rejected"
            kyc_record.failure_reason = reason
        target_user.is_verified = False

        # NOTIFY: Failure alert for customer
        await NotificationService.notify_status_update(
            db, user_id, 
            "Identity Action Required", 
            f"Your identity verification was rejected by {profile.business_name}. Reason: {reason}",
            f"/bookings/step/kyc/{booking.id}",
            "kyc_update"
        )
        
    db.commit()

    # --- Real-time WebSocket Notification ---
    # Notify the customer that their verification state has changed
    try:
        await manager.broadcast_to_user(target_user.id, {
            "type": "kyc_update",
            "status": "approved" if action == "approve" else "rejected",
            "reason": reason if action == "reject" else None
        })
    except Exception as e:
        print(f"[KYC WS] Failed to notify user {user_id}: {e}")

    return RedirectResponse(url=f"/caterer/compliance/view/{user_id}?success_msg=Identity+{action}d+successfully", status_code=303)


# --- SMART PRICING & QUICK BOOK SYSTEM ---
from ..services.pricing_service import PricingService

@router.get("/ingredients", response_class=HTMLResponse)
async def manage_ingredients(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    ingredients = db.query(models.Ingredient).filter(
        models.Ingredient.caterer_id == user.caterer_profile.id,
        models.Ingredient.is_archived == False
    ).order_by(models.Ingredient.name).all()
    
    return templates.TemplateResponse("caterer/ingredients.html", {
        "request": request,
        "user": user,
        "ingredients": ingredients,
        "active_page": "ingredients" # Corrected active page to highlight the sidebar link
    })

@router.get("/api/ingredients/list")
async def list_ingredients_api(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    ingredients = db.query(models.Ingredient).filter(
        models.Ingredient.caterer_id == user.caterer_profile.id,
        models.Ingredient.is_archived == False
    ).order_by(models.Ingredient.name).all()
    
    return [{"id": i.id, "name": i.name, "unit": i.unit, "unit_price": i.unit_price} for i in ingredients]

@router.post("/api/ingredients")
async def save_ingredient(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    data = await request.json()
    ing_id = data.get("id")
    name = data.get("name")
    unit = data.get("unit")
    unit_price = float(data.get("unit_price") or 0)

    if ing_id:
        ingredient = db.query(models.Ingredient).get(ing_id)
        if not ingredient or ingredient.caterer_id != user.caterer_profile.id:
            raise HTTPException(status_code=404, detail="Ingredient not found")
        
        ingredient.name = name
        ingredient.unit = unit
        ingredient.unit_price = unit_price
    else:
        ingredient = models.Ingredient(
            caterer_id=user.caterer_profile.id,
            name=name,
            unit=unit,
            unit_price=unit_price
        )
        db.add(ingredient)
    
    db.commit()
    db.refresh(ingredient)
    
    # Cascade updates if price changed
    if ing_id:
        PricingService.cascade_update_from_ingredient(db, ingredient.id)
    
    return {"status": "success", "ingredient_id": ingredient.id}

@router.delete("/api/ingredients/{ingredient_id}")
async def delete_ingredient(
    ingredient_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    ingredient = db.query(models.Ingredient).get(ingredient_id)
    if not ingredient or ingredient.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    ingredient.is_archived = True
    db.commit()
    return {"status": "success"}

@router.get("/api/menu-items/{menu_item_id}/ingredients")
async def get_menu_item_ingredients(
    menu_item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    menu_item = db.query(models.MenuItem).get(menu_item_id)
    if not menu_item or menu_item.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    ingredients = []
    for mii in menu_item.ingredients:
        ingredients.append({
            "id": mii.ingredient_id,
            "name": mii.ingredient.name,
            "unit": mii.ingredient.unit,
            "unit_price": mii.ingredient.unit_price,
            "quantity": mii.quantity
        })
    
    return {
        "menu_item_id": menu_item_id,
        "name": menu_item.name,
        "ingredients": ingredients,
        "total_cost": menu_item.cost_price
    }

@router.post("/api/menu-items/{menu_item_id}/ingredients")
async def save_menu_item_ingredients(
    menu_item_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    data = await request.json()
    mapping = data.get("ingredients", []) # List of {id, quantity}

    menu_item = db.query(models.MenuItem).get(menu_item_id)
    if not menu_item or menu_item.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    # Remove existing mappings
    db.query(models.MenuItemIngredient).filter_by(menu_item_id=menu_item_id).delete()
    
    # Add new mappings
    for item in mapping:
        mii = models.MenuItemIngredient(
            menu_item_id=menu_item_id,
            ingredient_id=item['id'],
            quantity=item['quantity']
        )
        db.add(mii)
    
    db.commit()
    
    # Recalculate cost
    PricingService.calculate_menu_item_cost(db, menu_item_id)
    
    # Cascade to packages
    for pkg in menu_item.packages:
        PricingService.calculate_package_cost(db, pkg.id)
        
    return {"status": "success"}

@router.post("/api/packages/{package_id}/roi")
async def save_package_roi(
    package_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    data = await request.json()
    markup_type = data.get("markup_type", "percentage")
    markup_value = float(data.get("markup_value") or 0)

    package = db.query(models.CateringPackage).get(package_id)
    if not package or package.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Package not found")
    
    package.markup_type = markup_type
    package.markup_value = markup_value
    
    db.commit()
    
    # Recalculate package selling price
    PricingService.calculate_package_cost(db, package_id)
    
    return {"status": "success", "new_price": package.price}

@router.get("/api/quick-quotation/{package_id}")
async def get_quick_quotation(
    package_id: int,
    pax: int = 10,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).get(package_id)
    if not package or package.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Package not found")
    
    PricingService.calculate_package_cost(db, package_id)
    
    cost_per_pax = package.cost_price
    total_cost = cost_per_pax * pax
    total_price = package.price * pax
    roi = total_price - total_cost
    
    breakdown = []
    for item in package.menu_items:
        breakdown.append({
            "name": item.name,
            "cost_per_pax": item.cost_price,
            "ingredients": [{
                "name": mi.ingredient.name,
                "qty": mi.quantity,
                "unit": mi.ingredient.unit,
                "cost": mi.ingredient.unit_price * mi.quantity
            } for mi in item.ingredients]
        })

    return {
        "package_name": package.name,
        "pax": pax,
        "cost_per_pax": cost_per_pax,
        "total_cost": total_cost,
        "total_price": total_price,
        "roi": roi,
        "markup_label": f"{package.markup_value}%" if package.markup_type == 'percentage' else f"₱{package.markup_value}",
        "breakdown": breakdown
    }

@router.get("/api/validate-customer-email")
async def validate_customer_email(
    email: str, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    """Detects if a customer email is already registered in the system."""
    target_user = db.query(models.User).filter(models.User.email == email).first()
    if target_user:
        return {
            "exists": True, 
            "name": f"{target_user.first_name} {target_user.last_name}",
            "role": target_user.role
        }
    return {"exists": False}
