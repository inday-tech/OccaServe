from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile, BackgroundTasks
from typing import Optional
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from ..core.templates import templates
from sqlalchemy.orm import Session
import os, secrets, string, logging
from ..db import database, models
from ..core import security as auth
from ..core.utils import is_dummy_email, is_dummy_name, is_dummy_phone, is_dummy_address, is_valid_person_name, is_valid_business_name
from ..services.email import EmailService
from datetime import datetime, timedelta
from sqlalchemy import func
import json, re
from ..services.realtime import manager
from ..services.verification import verification_service

router = APIRouter(prefix="/admin", tags=["admin"])

# Standard dependency for admin access
admin_only = auth.RoleChecker(["admin"])

logger = logging.getLogger(__name__)


def _send_caterer_welcome_email(email: str, temp_password: str, business_name: str) -> None:
    """Send the caterer account-created email, logging any failure without raising."""
    print(f"[CATERER EMAIL] Starting to send welcome email to {email}")
    try:
        EmailService.send_caterer_account_created_email(email, temp_password, business_name)
        print(f"[CATERER EMAIL] Successfully sent welcome email to {email}")
    except Exception as exc:
        print(f"[CATERER EMAIL] FAILED to send welcome email to {email}: {exc}")
        logger.error(
            "[admin] Failed to send caterer account-created email to %s (%s): %s",
            email, business_name, exc, exc_info=True
        )

UPLOAD_DIR_SITE = "app/static/uploads/website"
os.makedirs(UPLOAD_DIR_SITE, exist_ok=True)

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):

    # Platform Metrics
    user_count = db.query(models.User).filter(models.User.is_archived == False).count()
    customer_count = db.query(models.User).filter(models.User.role == 'customer', models.User.is_archived == False).count()
    
    # Caterer Metrics
    total_caterers = db.query(models.CatererProfile).join(models.User).filter(models.User.is_archived == False).count()
    pending_caterers = db.query(models.CatererProfile).join(models.User).filter(models.CatererProfile.verification_status == "Pending", models.User.is_archived == False).all()
    approved_caterers_count = db.query(models.CatererProfile).join(models.User).filter(models.CatererProfile.verification_status == "Verified", models.User.is_archived == False).count()
    rejected_caterers_count = db.query(models.CatererProfile).join(models.User).filter(models.CatererProfile.verification_status == "Rejected", models.User.is_archived == False).count()
    
    all_bookings = db.query(models.Booking).all()
    booking_count = len(all_bookings)
    
    # Ensure we get proper floats for currency logic
    total_sales = float(sum(b.total_amount for b in all_bookings if b.status != 'cancelled') or 0.0)
    
    # Platform earnings only based on completed/paid bookings effectively
    paid_bookings = [b for b in all_bookings if b.payment_status == 'paid']
    total_revenue = float(sum(b.total_amount for b in paid_bookings) or 0.0)
    
    # Dynamic commission check 
    config = db.query(models.WebsiteConfig).first()
    commission_rate = (config.commission_rate / 100.0) if config and config.commission_rate else 0.10
    
    platform_earnings = total_revenue * commission_rate

    pending_customers = db.query(models.User).filter(
        models.User.role == "customer",
        models.User.is_verified == False
    ).all()

    # --- Analytics Chart Data (Last 6 Months) ---
    chart_data = {"months": [], "sales": [], "earnings": [], "bookings": [], "new_users": []}
    for i in range(5, -1, -1):
        target_date = datetime.now() - timedelta(days=i*30)
        month_name = target_date.strftime("%b")
        first_day_of_month = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i == 0:
            last_day_of_month = datetime.now()
        else:
            next_month = first_day_of_month + timedelta(days=32)
            last_day_of_month = next_month.replace(day=1) - timedelta(seconds=1)

        month_bookings = db.query(models.Booking).filter(
            models.Booking.created_at >= first_day_of_month,
            models.Booking.created_at <= last_day_of_month,
            models.Booking.status != 'cancelled'
        ).all()

        month_new_users = db.query(models.User).filter(
            models.User.created_at >= first_day_of_month,
            models.User.created_at <= last_day_of_month
        ).count()
        
        month_sales = float(sum(b.total_amount for b in month_bookings) or 0.0)
        month_paid_bookings = [b for b in month_bookings if b.payment_status == 'paid']
        month_paid_total = float(sum(b.total_amount for b in month_paid_bookings) or 0.0)
        month_earnings = month_paid_total * commission_rate

        chart_data["months"].append(month_name)
        chart_data["sales"].append(month_sales)
        chart_data["earnings"].append(month_earnings)
        chart_data["bookings"].append(len(month_bookings))
        chart_data["new_users"].append(month_new_users)

    # --- Extra Stats for Analytics Cards ---
    avg_rating_result = db.query(func.avg(models.Review.rating)).filter(models.Review.is_archived == False).scalar()
    avg_rating = round(float(avg_rating_result), 1) if avg_rating_result else 0.0
    total_reviews = db.query(models.Review).filter(models.Review.is_archived == False).count()

    pending_bookings_count = db.query(models.Booking).filter(
        models.Booking.is_archived == False,
        models.Booking.status == 'pending'
    ).count()
    confirmed_bookings_count = db.query(models.Booking).filter(
        models.Booking.is_archived == False,
        models.Booking.status == 'confirmed'
    ).count()
    completed_bookings_count = db.query(models.Booking).filter(
        models.Booking.is_archived == False,
        models.Booking.status == 'completed'
    ).count()

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": user,
        "metrics": {
            "user_count": user_count,
            "customer_count": customer_count,
            "approved_caterers_count": approved_caterers_count,
            "booking_count": booking_count,
            "total_sales": total_sales,
            "platform_earnings": platform_earnings
        },
        "pending_caterers": pending_caterers,
        "active_page": "dashboard",
        "chart_data": chart_data,
        "recent_notifications": db.query(models.Notification).filter(models.Notification.user_id == user.id).order_by(models.Notification.created_at.desc()).limit(5).all(),
        "avg_rating": avg_rating,
        "total_reviews": total_reviews,
        "pending_bookings_count": pending_bookings_count,
        "confirmed_bookings_count": confirmed_bookings_count,
        "completed_bookings_count": completed_bookings_count,
        "pending_customers": pending_customers
    })

@router.get("/caterers", response_class=HTMLResponse)
async def manage_caterers(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    
    # ONLY show Verified Caterers here. Pending/Rejected go to Compliance Queue.
    caterers = db.query(models.CatererProfile).join(models.User).filter(
        models.User.is_archived == False,
        models.CatererProfile.verification_status == "Verified"
    ).all()
    
    # Caterer Metrics for Summary
    metrics = {
        "total_caterers": db.query(models.CatererProfile).join(models.User).filter(models.User.is_archived == False).count(),
        "pending_caterers_count": db.query(models.CatererProfile).join(models.User).filter(models.CatererProfile.verification_status == "Pending", models.User.is_archived == False).count(),
        "approved_caterers_count": db.query(models.CatererProfile).join(models.User).filter(models.CatererProfile.verification_status == "Verified", models.User.is_archived == False).count(),
        "rejected_caterers_count": db.query(models.CatererProfile).join(models.User).filter(models.CatererProfile.verification_status == "Rejected", models.User.is_archived == False).count(),
    }

    return templates.TemplateResponse("admin/caterers.html", {
        "request": request,
        "user": user,
        "caterers": caterers,
        "metrics": metrics,
        "active_page": "caterers"
    })


@router.get("/payouts", response_class=HTMLResponse)
async def manage_payouts(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    # 1. Fetch formal Withdrawal Requests (Grouped Payouts)
    pending_requests = db.query(models.Payout).filter(
        models.Payout.status == 'pending'
    ).order_by(models.Payout.requested_at.desc()).all()

    # 2. Fetch payout items that are 'ready' but NOT yet linked to a formal request
    # This allows admin to be proactive if needed
    ready_items = db.query(models.PayoutItem).filter(
        models.PayoutItem.status == 'ready',
        models.PayoutItem.payout_id == None
    ).order_by(models.PayoutItem.id.desc()).all()

    # 3. Fetch recently completed payouts
    recent_completed = db.query(models.Payout).filter(
        models.Payout.status == 'completed'
    ).order_by(models.Payout.completed_at.desc()).limit(15).all()

    # Calculate metrics
    pending_request_total = float(sum(p.total_amount for p in pending_requests) or 0.0)
    ready_funds_total = float(sum(p.amount for p in ready_items) or 0.0)

    return templates.TemplateResponse("admin/payouts.html", {
        "request": request,
        "user": user,
        "pending_requests": pending_requests,
        "ready_items": ready_items,
        "recent_completed": recent_completed,
        "pending_request_total": pending_request_total,
        "ready_funds_total": ready_funds_total,
        "active_page": "payouts"
    })

@router.post("/payouts/{payout_id}/approve")
async def approve_withdrawal_request(
    payout_id: int,
    reference: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    payout = db.query(models.Payout).get(payout_id)
    if not payout:
        raise HTTPException(status_code=404, detail="Withdrawal request not found")
    
    # 1. Update Payout Status
    payout.status = "completed"
    payout.completed_at = datetime.now()
    payout.admin_notes = f"Approved by {user.first_name}. Ref: {reference}"
    
    # 2. Update all linked items to 'released'
    for item in payout.items:
        item.status = "released"
    
    db.commit()

    # 3. Notify Caterer
    from ..services.notification import NotificationService
    import asyncio
    asyncio.create_task(NotificationService.notify_payout_completed(payout.id, db))

    return RedirectResponse(url="/admin/payouts?success_msg=Withdrawal+request+approved+successfully", status_code=303)

@router.post("/payouts/items/{item_id}/release")
async def release_individual_item(
    item_id: int,
    reference: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    item = db.query(models.PayoutItem).get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Payout item not found")
    
    item.status = "released"
    db.commit()
    return RedirectResponse(url="/admin/payouts?success_msg=Individual+payout+item+released", status_code=303)


@router.get("/settings", response_class=HTMLResponse)
async def website_settings(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    config = db.query(models.WebsiteConfig).first()
    if not config:
        # Create default config if none exists
        config = models.WebsiteConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
        
    return templates.TemplateResponse("admin/settings.html", {
        "request": request,
        "user": user,
        "config": config,
        "active_page": "settings"
    })

@router.post("/settings/update")
async def update_website_settings(
    request: Request,
    site_name: str = Form(...),
    support_email: str = Form(...),
    seo_desc: str = Form(...),
    fb_link: Optional[str] = Form(None),
    ig_link: Optional[str] = Form(None),
    tw_link: Optional[str] = Form(None),
    commission: Optional[float] = Form(None),
    commission_fixed: Optional[float] = Form(None),
    max_upload: Optional[int] = Form(None),
    maintenance_mode: str = Form("off"),
    maint_msg: str = Form(...),
    logo: Optional[UploadFile] = File(None),
    favicon: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    config = db.query(models.WebsiteConfig).first()
    if not config:
        config = models.WebsiteConfig()
        db.add(config)

    config.site_name = site_name
    config.support_email = support_email
    config.seo_description = seo_desc
    config.facebook_link = fb_link
    config.instagram_link = ig_link
    config.twitter_link = tw_link
    if commission is not None:
        config.commission_rate = commission
    if max_upload is not None:
        config.max_file_size_mb = max_upload
    config.maintenance_mode = True if maintenance_mode == "on" else False
    config.maintenance_message = maint_msg

    import time
    timestamp = int(time.time())

    # Handle Logo Upload
    if logo and logo.filename:
        import shutil
        file_ext = os.path.splitext(logo.filename)[1]
        new_filename = f"logo_{timestamp}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR_SITE, new_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(logo.file, buffer)
            
        # Clean up old logo
        if config.logo_url:
            old_logo_path = os.path.join(UPLOAD_DIR_SITE, os.path.basename(config.logo_url))
            if os.path.exists(old_logo_path):
                try: os.remove(old_logo_path)
                except: pass
                
        config.logo_url = f"/static/uploads/website/{new_filename}"

    # Handle Favicon Upload
    if favicon and favicon.filename:
        import shutil
        file_ext = os.path.splitext(favicon.filename)[1]
        new_filename = f"favicon_{timestamp}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR_SITE, new_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(favicon.file, buffer)
            
        # Clean up old favicon
        if config.favicon_url:
            old_favicon_path = os.path.join(UPLOAD_DIR_SITE, os.path.basename(config.favicon_url))
            if os.path.exists(old_favicon_path):
                try: os.remove(old_favicon_path)
                except: pass
                
        config.favicon_url = f"/static/uploads/website/{new_filename}"

    db.commit()
    return RedirectResponse(url="/admin/settings?success_msg=Website+settings+updated+successfully", status_code=303)

@router.post("/profile/change-password")
async def admin_change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
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
    db.commit()
    
    return {"success": True, "message": "Password updated successfully."}

# --- Inquiries Management ---
@router.get("/inquiries", response_class=HTMLResponse)
async def list_inquiries(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    all_inquiries = db.query(models.Inquiry).order_by(models.Inquiry.created_at.desc()).all()
    
    # Group by email
    grouped = {}
    for i in all_inquiries:
        if i.email not in grouped:
            grouped[i.email] = {
                "name": i.name,
                "email": i.email,
                "messages": [],
                "latest_date": i.created_at,
                "status": "responded" # Default, will be overridden if any is 'new'
            }
        
        msg_data = {
            "id": i.id,
            "message": i.message,
            "status": i.status,
            "created_at": i.created_at.strftime("%b %d, %Y %I:%M %p")
        }
        grouped[i.email]["messages"].append(msg_data)
        
        # If any message in thread is 'new', the thread status is 'new'
        if i.status == "new":
            grouped[i.email]["status"] = "new"
    
    # Sort grouped list by latest message date
    senders_list = sorted(grouped.values(), key=lambda x: x["latest_date"], reverse=True)
    
    return templates.TemplateResponse("admin/inquiries.html", {
        "request": request,
        "senders": senders_list,
        "senders_json": json.dumps(senders_list, default=str), # default=str to handle datetime if any
        "active_page": "inquiries",
        "user": user
    })

@router.post("/inquiries/thread/{email}/status")
async def update_thread_status(
    email: str, 
    status: str, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    db.query(models.Inquiry).filter(models.Inquiry.email == email).update({"status": status})
    db.commit()
    return RedirectResponse(url="/admin/inquiries?success_msg=Thread+status+updated", status_code=303)

@router.post("/inquiries/{inquiry_id}/status")
async def update_inquiry_status(
    inquiry_id: int, 
    status: str, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    inquiry = db.query(models.Inquiry).filter(models.Inquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    
    inquiry.status = status
    db.commit()
    return RedirectResponse(url="/admin/inquiries?success_msg=Inquiry+status+updated", status_code=303)

@router.post("/inquiries/{inquiry_id}/delete")
async def delete_inquiry(
    inquiry_id: int, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    inquiry = db.query(models.Inquiry).filter(models.Inquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    
    db.delete(inquiry)
    db.commit()
    return RedirectResponse(url="/admin/inquiries?success_msg=Inquiry+deleted+successfully", status_code=303)


@router.post("/caterers/{caterer_id}/verify")
def verify_caterer(
    caterer_id: int, 
    action: str = Form(...), 
    reason: Optional[str] = Form(None),
    db: Session = Depends(database.get_db), 
    user: models.User = Depends(admin_only)
):
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer:
        raise HTTPException(status_code=404, detail="Caterer not found")
    
    if action == "approve":
        caterer.verification_status = "Verified"
        caterer.is_verified = True
        # Explicitly activate the associated user account and clear all barriers
        if caterer.user_id:
            caterer_user = db.query(models.User).get(caterer.user_id)
            if caterer_user:
                caterer_user.status = "active"
                caterer_user.is_email_verified = True
                caterer_user.is_verified = True
    elif action == "reject":
        caterer.verification_status = "Rejected"
        caterer.is_verified = False
        # Optional: Store rejection reason if we added a field for it, 
        # or send a notification/email to the caterer.
    elif action == "revision":
        caterer.verification_status = "Revision Requested"
        caterer.is_verified = False
    
    db.commit()
    
    # Real-time update
    asyncio.create_task(manager.broadcast({
        "type": "caterer_update",
        "caterer_id": caterer_id,
        "action": action,
        "status": caterer.verification_status
    }))
    
    return RedirectResponse(url=f"/admin/caterers?success_msg=Caterer+{action}+successfully", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/caterers/{caterer_id}/status")
def toggle_caterer_status(caterer_id: int, db: Session = Depends(database.get_db), user: models.User = Depends(admin_only)):
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer:
        raise HTTPException(status_code=404, detail="Caterer not found")
    
    # Toggle status of the associated user account using direct lookup
    if caterer.user_id:
        caterer_user = db.query(models.User).get(caterer.user_id)
        if caterer_user:
            if caterer_user.status == "active":
                caterer_user.status = "suspended"
            else:
                # Activate and clear barriers if coming from suspended or pending
                caterer_user.status = "active"
                caterer_user.is_email_verified = True
                caterer_user.is_verified = True
    
    db.commit()
    
    # Real-time update
    asyncio.create_task(manager.broadcast({
        "type": "caterer_update",
        "caterer_id": caterer_id,
        "action": "status_toggle",
        "status": caterer_user.status if caterer.user_id else "unknown"
    }))
    
    return RedirectResponse(url="/admin/caterers?success_msg=Caterer+status+updated", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/caterers/{caterer_id}/delete")
def delete_caterer(caterer_id: int, db: Session = Depends(database.get_db), user: models.User = Depends(admin_only)):
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer:
        raise HTTPException(status_code=404, detail="Caterer not found")
        
    user_id = caterer.user_id
    
    # Manually delete related data that doesn't have cascade-delete or might cause issues
    if user_id:
        db.query(models.RefreshToken).filter(models.RefreshToken.user_id == user_id).delete()
        db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == user_id).delete()
        db.query(models.AuditLog).filter(models.AuditLog.user_id == user_id).delete()
        db.query(models.Notification).filter(models.Notification.user_id == user_id).delete()
        db.query(models.VerificationAttempt).filter(models.VerificationAttempt.user_id == user_id).delete()
        db.query(models.Review).filter(models.Review.user_id == user_id).delete()
        db.query(models.Inquiry).filter(models.Inquiry.user_id == user_id).delete()
        db.query(models.OCRVerification).filter(models.OCRVerification.user_id == user_id).delete()
        
    # Delete Caterer specific tables
    # Delete Caterer specific tables (Packages, Menu Items, Bookings, Gallery)
    packages = db.query(models.CateringPackage).filter(models.CateringPackage.caterer_id == caterer_id).all()
    package_ids = [p.id for p in packages]
    if package_ids:
        db.query(models.MenuItem).filter(models.MenuItem.package_id.in_(package_ids)).delete(synchronize_session=False)
    
    db.query(models.CateringPackage).filter(models.CateringPackage.caterer_id == caterer_id).delete(synchronize_session=False)
    db.query(models.CatererGallery).filter(models.CatererGallery.caterer_id == caterer_id).delete(synchronize_session=False)
    
    # Bookings and payouts
    db.query(models.Payout).filter(models.Payout.caterer_id == caterer_id).delete(synchronize_session=False)
    db.query(models.Booking).filter(models.Booking.caterer_id == caterer_id).delete(synchronize_session=False)

    # Finally delete the user and profile
    db.delete(caterer)
    if user_id:
        associated_user = db.query(models.User).get(user_id)
        if associated_user:
            db.delete(associated_user)
            
    db.commit()
    
    # Real-time update
    asyncio.create_task(manager.broadcast({
        "type": "user_archived",
        "user_id": user_id,
        "role": "caterer"
    }))
    
    return RedirectResponse(url="/admin/caterers?success_msg=Caterer+deleted+successfully", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/api/caterers/{caterer_id}/edit")
async def edit_caterer(
    caterer_id: int,
    business_name: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    city: str = Form(...),
    contact_address: str = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer:
         return {"success": False, "message": "Caterer not found."}
    
    parts = full_name.strip().split(None, 1)
    if len(parts) > 1:
        first_name, last_name = parts[0], parts[1]
    else:
        first_name, last_name = parts[0], ""
        
    existing_user = db.query(models.User).filter(models.User.email == email.strip().lower(), models.User.id != caterer.user_id).first()
    if existing_user:
        return {"success": False, "message": "This email is already in use by another account."}
        
    caterer.business_name = business_name
    caterer.city = city
    caterer.contact_address = contact_address
    caterer.contact_phone = phone
    caterer.latitude = latitude
    caterer.longitude = longitude
    
    if caterer.user:
        caterer.user.first_name = first_name
        caterer.user.last_name = last_name
        caterer.user.email = email.strip().lower()
        caterer.user.phone_number = phone
        
    db.commit()
    
    # Real-time update
    asyncio.create_task(manager.broadcast({
        "type": "caterer_update",
        "caterer_id": caterer_id,
        "action": "edit"
    }))
    
    return {"success": True, "message": "Caterer details updated successfully."}

@router.get("/caterers/check-availability")
async def check_caterer_availability(
    email: Optional[str] = None,
    business_name: Optional[str] = None,
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    results = {
        "email_taken": False,
        "business_name_taken": False,
        "name_taken": False,
        "phone_taken": False
    }
    
    if email:
        existing_user = db.query(models.User).filter(
            models.User.email == email.strip().lower(),
            models.User.is_archived == False
        ).first()
        results["email_taken"] = existing_user is not None
            
    if business_name:
        existing_profile = db.query(models.CatererProfile).filter(
            func.lower(models.CatererProfile.business_name) == business_name.strip().lower()
        ).first()
        results["business_name_taken"] = existing_profile is not None

    if full_name:
        # Split and check against first_name + last_name
        parts = full_name.strip().split(None, 1)
        f_name = parts[0] if len(parts) > 0 else ""
        l_name = parts[1] if len(parts) > 1 else ""
        
        existing_name = db.query(models.User).filter(
            func.lower(models.User.first_name) == f_name.lower(),
            func.lower(models.User.last_name) == l_name.lower(),
            models.User.is_archived == False
        ).first()
        results["name_taken"] = existing_name is not None

    if phone:
        # Check both User table and CatererProfile table
        existing_phone_user = db.query(models.User).filter(models.User.phone_number == phone.strip()).first()
        existing_phone_profile = db.query(models.CatererProfile).filter(models.CatererProfile.contact_phone == phone.strip()).first()
        results["phone_taken"] = (existing_phone_user is not None or existing_phone_profile is not None)
            
    return results

@router.post("/caterers/add")
async def add_caterer(
    request: Request,
    background_tasks: BackgroundTasks,
    business_name: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    phone: str = Form(...),
    city: str = Form(...),
    contact_address: str = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    # 1. Server-side Validation (High Fidelity Adjudication)
    errors = {}
    
    # Email check
    email_err = is_dummy_email(email)
    if email_err:
        errors['email'] = email_err
    else:
        existing_user = db.query(models.User).filter(models.User.email == email).first()
        if existing_user:
            errors['email'] = "This email identity is already registered."

    # Name check (Signatory)
    parts = full_name.strip().split(None, 1)
    f_name = parts[0] if len(parts) > 0 else ""
    l_name = parts[1] if len(parts) > 1 else ""

    f_err = is_valid_person_name(f_name)
    if f_err: errors['full_name'] = f_err
    
    l_err = is_valid_person_name(l_name)
    if l_err: errors['full_name'] = l_err

    # Duplicate Signatory Check
    existing_name = db.query(models.User).filter(
        func.lower(models.User.first_name) == f_name.lower(),
        func.lower(models.User.last_name) == l_name.lower(),
        models.User.is_archived == False
    ).first()
    if existing_name:
        errors['full_name'] = "This signatory is already registered as a partner."

    # Business Name check
    biz_err = is_valid_business_name(business_name)
    if biz_err:
        errors['business_name'] = biz_err
    else:
        existing_profile = db.query(models.CatererProfile).filter(
            func.lower(models.CatererProfile.business_name) == business_name.strip().lower()
        ).first()
        if existing_profile:
            errors['business_name'] = "Business name already exists in our registry."

    # Phone check
    phone_err = is_dummy_phone(phone)
    if phone_err:
        errors['phone'] = phone_err
    else:
        existing_phone = db.query(models.User).filter(models.User.phone_number == phone.strip()).first()
        if existing_phone:
            errors['phone'] = "This mobile number is already linked to another account."

    # Operational Domain Check (Laguna Enforcement)
    if not city or "Laguna" not in city:
        errors['city'] = "Operational domain must be within the Laguna jurisdiction."

    if errors:
        return {"success": False, "errors": errors, "message": "Identity verification failed."}


    # Split full_name into first and last
    parts = full_name.strip().split(None, 1)
    if len(parts) > 1:
        first_name, last_name = parts[0], parts[1]
    else:
        first_name, last_name = parts[0], ""

    # password logic
    alphabet = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(alphabet) for i in range(10))
    hashed_password = auth.get_password_hash(temp_password)

    try:
        # 3. Create User record
        new_user = models.User(
            email=email,
            password_hash=hashed_password,
            role="caterer",
            first_name=first_name,
            last_name=last_name,
            phone_number=phone,
            status="active",
            is_verified=True,
            is_email_verified=True,
            is_kyc_complete=True,
            must_change_password=True
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # 4. Create Caterer Profile
        new_profile = models.CatererProfile(
            user_id=new_user.id,
            business_name=business_name,
            contact_phone=phone,
            contact_address=contact_address,
            city=city,
            latitude=latitude,
            longitude=longitude,
            verification_status="Verified",
            is_verified=True,
            slug=business_name.lower().replace(" ", "-") + f"-{new_user.id}"
        )
        db.add(new_profile)
        db.commit()

        # 5. Send welcome email
        background_tasks.add_task(_send_caterer_welcome_email, email, temp_password, business_name)

        # Real-time update
        asyncio.create_task(manager.broadcast({
            "type": "new_signup",
            "role": "caterer",
            "name": business_name
        }))

        return {"success": True, "message": "Caterer account created! The credentials have been sent to their email."}

    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Error creating account: {str(e)}"}

@router.post("/api/customers/{customer_id}/edit")
async def edit_customer(
    customer_id: int,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    customer = db.query(models.User).filter(
        models.User.id == customer_id,
        models.User.role == "customer"
    ).first()
    if not customer:
        return {"success": False, "message": "Customer not found."}

    # Check email not taken by someone else
    existing = db.query(models.User).filter(
        models.User.email == email.strip().lower(),
        models.User.id != customer_id
    ).first()
    if existing:
        return {"success": False, "message": "This email is already in use by another account."}

    customer.first_name = first_name.strip()
    customer.last_name = last_name.strip()
    customer.email = email.strip().lower()
    if phone:
        customer.phone_number = phone.strip()
    if address:
        customer.address = address.strip()

    db.commit()
    
    # Real-time update
    asyncio.create_task(manager.broadcast({
        "type": "customer_update",
        "customer_id": customer_id,
        "action": "edit"
    }))
    
    return {"success": True, "message": "Customer details updated successfully."}

@router.post("/customers/{customer_id}/status")
def toggle_customer_status(customer_id: int, db: Session = Depends(database.get_db), user: models.User = Depends(admin_only)):
    customer = db.query(models.User).filter(models.User.id == customer_id, models.User.role == "customer").first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    if customer.status == "active":
        customer.status = "suspended"
    else:
        customer.status = "active"
        customer.is_email_verified = True
        customer.is_verified = True
        
    db.commit()
    
    # Real-time update
    asyncio.create_task(manager.broadcast({
        "type": "customer_update",
        "customer_id": customer_id,
        "action": "status_toggle",
        "status": customer.status
    }))
    
    return RedirectResponse(url="/admin/customers?success_msg=Customer+status+updated", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/customers/{customer_id}/delete")
def delete_customer(customer_id: int, db: Session = Depends(database.get_db), user: models.User = Depends(admin_only)):
    # Find the user as a customer only to be safe
    customer = db.query(models.User).filter(models.User.id == customer_id, models.User.role == "customer").first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Manually delete related data that doesn't have cascade-delete or might cause issues
    db.query(models.RefreshToken).filter(models.RefreshToken.user_id == customer_id).delete()
    db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == customer_id).delete()
    db.query(models.AuditLog).filter(models.AuditLog.user_id == customer_id).delete()
    db.query(models.Notification).filter(models.Notification.user_id == customer_id).delete()
    db.query(models.VerificationAttempt).filter(models.VerificationAttempt.user_id == customer_id).delete()
    db.query(models.Review).filter(models.Review.user_id == customer_id).delete()
    db.query(models.Inquiry).filter(models.Inquiry.user_id == customer_id).delete()
    db.query(models.OCRVerification).filter(models.OCRVerification.user_id == customer_id).delete()
    
    # Finally delete the user
    db.delete(customer)
    db.commit()
    
    # Real-time update
    asyncio.create_task(manager.broadcast({
        "type": "user_archived",
        "user_id": customer_id,
        "role": "customer"
    }))
    
    return RedirectResponse(url="/admin/customers?success_msg=Customer+deleted+successfully", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/customers/{customer_id}/verify")
def verify_customer(customer_id: int, action: str = Form(...), db: Session = Depends(database.get_db), user: models.User = Depends(admin_only)):
    customer = db.query(models.User).filter(models.User.id == customer_id, models.User.role == "customer").first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    if action == "approve":
        customer.is_verified = True
        customer.is_email_verified = True
        customer.status = "active"
    else:
        customer.is_verified = False
    
    db.commit()
    return RedirectResponse(url=f"/admin/customers?success_msg=Customer+{action}+successfully", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/verify/{user_id}", response_class=HTMLResponse)
async def review_verification(
    user_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    target_user = db.query(models.User).get(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    verification = target_user.identity_verification
    if not verification:
        # Create a blank record if it doesn't exist but is requested for audit
        verification = models.IdentityVerification(user_id=user_id)
        db.add(verification)
        db.commit()
        db.refresh(verification)

    return templates.TemplateResponse("admin/verification_detail.html", {
        "request": request,
        "user": user,
        "target_user": target_user,
        "verification": verification,
        "active_page": "compliance"
    })

@router.get("/kyc")
async def view_kyc_queue(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    # 1. Fetch Pending Caterers (Always Action Required)
    pending_caterers = db.query(models.CatererProfile).filter(
        models.CatererProfile.verification_status == "Pending"
    ).all()

    # 2. Fetch Pending Customers (Role is customer and not verified)
    # We look for users who HAVE an IdentityVerification record that is not approved, 
    # OR customers who haven't been verified yet.
    pending_customers = db.query(models.User).filter(
        models.User.role == "customer",
        models.User.is_verified == False
    ).all()

    # 3. Fetch Verified History (Last 20 for history tab)
    recent_history = db.query(models.IdentityVerification).filter(
        models.IdentityVerification.verification_status.in_(["approved", "rejected"])
    ).order_by(models.IdentityVerification.created_at.desc()).limit(20).all()

    return templates.TemplateResponse("admin/kyc_logs.html", {
        "request": request,
        "user": user,
        "pending_caterers": pending_caterers,
        "pending_customers": pending_customers,
        "recent_history": recent_history,
        "active_page": "kyc"
    })

# --- New KYC & Fraud Admin Endpoints ---

@router.get("/api/bookings")
async def api_list_bookings(
    status: Optional[str] = None,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    query = db.query(models.Booking)
    if status:
        query = query.filter(models.Booking.status == status)
    return query.all()

@router.get("/bookings/{booking_id}/kyc")
async def view_booking_kyc(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    kyc = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == booking.user_id).first()
    audit_trail = db.query(models.AuditLog).filter(models.AuditLog.user_id == booking.user_id).order_by(models.AuditLog.timestamp.desc()).all()
    
    return templates.TemplateResponse("admin/booking_kyc.html", {
        "request": request,
        "user": user,
        "booking": booking,
        "kyc": kyc,
        "audit_trail": audit_trail,
        "active_page": "bookings"
    })

@router.post("/kyc/user/{user_id}/action")
async def kyc_manual_action(
    user_id: int,
    action: str = Form(...),
    notes: str = Form(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    target_user = db.query(models.User).get(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
        
    kyc = target_user.identity_verification
    if not kyc:
        # Create a placeholder if not exists to store the decision
        kyc = models.IdentityVerification(user_id=user_id, verification_status="pending")
        db.add(kyc)
        db.flush()
    
    target_user = db.query(models.User).get(kyc.user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    full_name = f"{target_user.first_name} {target_user.last_name}"
    
    if action == "approve":
        kyc.verification_status = "approved"
        kyc.failure_reason = None
        target_user.is_verified = True
        target_user.is_kyc_complete = True
        target_user.status = "active"
        
        # If caterer, also update profile status
        if target_user.role == "caterer" and target_user.caterer_profile:
            target_user.caterer_profile.verification_status = "Verified"
            
        # Send Approval Email
        EmailService.send_kyc_approval_email(target_user.email, full_name)
    else:
        kyc.verification_status = "rejected"
        kyc.failure_reason = notes or "Identity verification failed security audit."
        target_user.is_verified = False
        target_user.status = "suspended" # Prevents login
        
        if target_user.role == "caterer" and target_user.caterer_profile:
            target_user.caterer_profile.verification_status = "Rejected"
            
        # Send Rejection Email
        EmailService.send_kyc_rejection_email(target_user.email, full_name, kyc.failure_reason)
    
    # Audit Log
    audit = models.AuditLog(
        user_id=target_user.id,
        action="manual_kyc_decision",
        old_status="manual_review",
        new_status=kyc.verification_status,
        notes=f"Admin {user.email}: {notes}"
    )
    db.add(audit)
    db.commit()

    # Real-time update for all connected admins
    from ..services.realtime import manager
    import asyncio
    asyncio.create_task(manager.broadcast({
        "type": "kyc_update",
        "user_id": target_user.id,
        "status": kyc.verification_status,
        "message": f"KYC for {full_name} has been {action}d."
    }))
    
    return RedirectResponse(url=f"/admin/verify/{target_user.id}?success_msg=Action+processed+successfully", status_code=303)

@router.post("/bookings/{booking_id}/flag")
async def flag_booking(
    booking_id: int,
    flag_type: str = Form(...),
    description: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    flag = models.FraudFlag(
        booking_id=booking_id,
        flag_type=flag_type,
        description=description
    )
    db.add(flag)
    db.commit()
    return RedirectResponse(url=f"/admin/bookings/{booking_id}/kyc?success_msg=Booking+flagged+successfully", status_code=303)

# Redirect old /reviews URL to the new /feedback page for backward compatibility
@router.get("/reviews")
async def redirect_reviews_to_feedback():
    return RedirectResponse(url="/admin/feedback", status_code=301)

@router.get("/feedback", response_class=HTMLResponse)
async def admin_feedback(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    feedbacks = db.query(models.PlatformFeedback).filter(
        models.PlatformFeedback.is_archived == False
    ).order_by(models.PlatformFeedback.created_at.desc()).all()

    total_count = len(feedbacks)
    highlighted_count = sum(1 for f in feedbacks if f.is_highlighted)
    high_rated_count = sum(1 for f in feedbacks if f.rating and f.rating >= 4)
    avg_rating = round(sum(f.rating for f in feedbacks if f.rating) / total_count, 1) if total_count else 0.0

    return templates.TemplateResponse("admin/feedback.html", {
        "request": request,
        "user": user,
        "feedbacks": feedbacks,
        "total_count": total_count,
        "highlighted_count": highlighted_count,
        "high_rated_count": high_rated_count,
        "avg_rating": avg_rating,
        "active_page": "feedback"
    })

@router.post("/feedback/{feedback_id}/highlight")
async def toggle_feedback_highlight(
    feedback_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    fb = db.query(models.PlatformFeedback).get(feedback_id)
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
    fb.is_highlighted = not fb.is_highlighted
    db.commit()
    return RedirectResponse(url="/admin/feedback?success_msg=Feedback+updated", status_code=303)

@router.post("/feedback/{feedback_id}/archive")
async def archive_feedback(
    feedback_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    fb = db.query(models.PlatformFeedback).get(feedback_id)
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
    fb.is_archived = True
    db.commit()
    return RedirectResponse(url="/admin/feedback?success_msg=Feedback+archived", status_code=303)

@router.get("/payments", response_class=HTMLResponse)
async def admin_payments(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    # Get all bookings with payment records or history
    bookings = db.query(models.Booking).filter(models.Booking.payment_status == 'paid', models.Booking.is_archived == False).order_by(models.Booking.created_at.desc()).all()
    
    # Get dynamic commission rate from site configuration
    config = db.query(models.WebsiteConfig).first()
    commission_rate = (config.commission_rate / 100.0) if config and config.commission_rate else 0.10

    total_gross = sum((b.total_amount or 0.0) for b in bookings)
    total_commission = total_gross * commission_rate

    return templates.TemplateResponse("admin/payments.html", {
        "request": request,
        "user": user,
        "bookings": bookings,
        "commission_rate": commission_rate,
        "total_gross": total_gross,
        "total_commission": total_commission,
        "active_page": "payments"
    })

# --- REPORTS / ANALYTICS ---

@router.get("/reports", response_class=HTMLResponse)
async def admin_reports(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    from calendar import month_abbr
    now = datetime.utcnow()
    
    # --- Monthly Growth ---
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)

    new_users_this_month = db.query(models.User).filter(models.User.created_at >= this_month_start).count()
    new_users_last_month = db.query(models.User).filter(
        models.User.created_at >= last_month_start,
        models.User.created_at < this_month_start
    ).count()

    if new_users_last_month > 0:
        monthly_growth_pct = round(((new_users_this_month - new_users_last_month) / new_users_last_month) * 100, 1)
    else:
        monthly_growth_pct = 100.0 if new_users_this_month > 0 else 0.0

    # --- User Satisfaction (Average Review Rating) ---
    avg_rating_result = db.query(func.avg(models.Review.rating)).filter(models.Review.is_archived == False).scalar()
    avg_rating = round(float(avg_rating_result), 1) if avg_rating_result else 0.0
    total_reviews = db.query(models.Review).filter(models.Review.is_archived == False).count()

    # --- Booking Summary ---
    total_bookings = db.query(models.Booking).filter(models.Booking.is_archived == False).count()
    paid_bookings = db.query(models.Booking).filter(
        models.Booking.is_archived == False,
        models.Booking.payment_status == 'paid'
    ).count()
    total_revenue = db.query(func.sum(models.Booking.total_amount)).filter(
        models.Booking.payment_status == 'paid',
        models.Booking.is_archived == False
    ).scalar() or 0.0
    
    # --- Monthly Bookings Trend (last 6 months) ---
    monthly_bookings = []
    monthly_labels = []
    for i in range(5, -1, -1):
        month_start = (now.replace(day=1) - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        count = db.query(models.Booking).filter(
            models.Booking.created_at >= month_start,
            models.Booking.created_at < month_end
        ).count()
        monthly_bookings.append(count)
        monthly_labels.append(month_abbr[month_start.month])
    
    # --- Top Caterers (by booking count) ---
    top_caterers_raw = (
        db.query(models.CatererProfile, func.count(models.Booking.id).label("booking_count"))
        .join(models.Booking, models.Booking.caterer_id == models.CatererProfile.id)
        .filter(models.Booking.is_archived == False)
        .group_by(models.CatererProfile.id)
        .order_by(func.count(models.Booking.id).desc())
        .limit(5)
        .all()
    )
    top_caterers = [{"name": c.business_name, "bookings": b} for c, b in top_caterers_raw]
    
    return templates.TemplateResponse("admin/reports.html", {
        "request": request,
        "user": user,
        "active_page": "reports",
        "monthly_growth_pct": monthly_growth_pct,
        "new_users_this_month": new_users_this_month,
        "avg_rating": avg_rating,
        "total_reviews": total_reviews,
        "total_bookings": total_bookings,
        "paid_bookings": paid_bookings,
        "total_revenue": total_revenue,
        "monthly_labels": json.dumps(monthly_labels),
        "monthly_bookings": json.dumps(monthly_bookings),
        "top_caterers": top_caterers,
    })

# --- ARCHIVE SYSTEM ---

@router.get("/archives", response_class=HTMLResponse)
async def view_archives(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    archived_caterers = db.query(models.CatererProfile).join(models.User).filter(models.User.is_archived == True).all()
    archived_customers = db.query(models.User).filter(models.User.role == 'customer', models.User.is_archived == True).all()
    archived_bookings = db.query(models.Booking).filter(models.Booking.is_archived == True).all()
    archived_reviews = db.query(models.Review).filter(models.Review.is_archived == True).all()
    archived_payouts = db.query(models.Payout).filter(models.Payout.is_archived == True).all()
    
    return templates.TemplateResponse("admin/archives.html", {
        "request": request,
        "user": user,
        "caterers": archived_caterers,
        "customers": archived_customers,
        "bookings": archived_bookings,
        "reviews": archived_reviews,
        "payouts": archived_payouts,
        "active_page": "archives"
    })

@router.post("/{item_type}/{item_id}/archive")
async def archive_item(
    item_type: str,
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    model_map = {
        "caterers": models.User, # Archive the user for caterers
        "customers": models.User,
        "bookings": models.Booking,
        "reviews": models.Review,
        "payouts": models.Payout,
        "kyc": models.IdentityVerification
    }
    
    if item_type not in model_map:
        raise HTTPException(status_code=400, detail="Invalid item type")
        
    model = model_map[item_type]
    
    # For caterers, we need to find the user associated with the caterer profile ID
    if item_type == "caterers":
        profile = db.query(models.CatererProfile).get(item_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Caterer not found")
        item = db.query(models.User).get(profile.user_id)
    else:
        item = db.query(model).get(item_id)
        
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    item.is_archived = True
    db.commit()
    
    # Redirect back to where they came from or a default
    return RedirectResponse(url=f"/admin/{item_type if item_type != 'caterers' else 'caterers'}?success_msg=Item+archived+successfully", status_code=303)

@router.post("/{item_type}/{item_id}/restore")
async def restore_item(
    item_type: str,
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    model_map = {
        "caterers": models.User,
        "customers": models.User,
        "bookings": models.Booking,
        "reviews": models.Review,
        "payouts": models.Payout,
        "kyc": models.IdentityVerification
    }
    
    if item_type not in model_map:
        raise HTTPException(status_code=400, detail="Invalid item type")
        
    model = model_map[item_type]
    
    # Handle caterer user restoration
    if item_type == "caterers":
        # item_id here is the Profile ID from the template
        profile = db.query(models.CatererProfile).get(item_id)
        if profile:
            item = db.query(models.User).get(profile.user_id)
        else:
            item = db.query(models.User).get(item_id)
    else:
        item = db.query(model).get(item_id)
        
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    item.is_archived = False
    db.commit()
    
    return RedirectResponse(url="/admin/archives?success_msg=Item+restored+successfully", status_code=303)

@router.post("/{item_type}/{item_id}/delete_permanent")
async def delete_item_permanent(
    item_type: str,
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    model_map = {
        "caterers": models.User,
        "customers": models.User,
        "bookings": models.Booking,
        "reviews": models.Review,
        "payouts": models.Payout,
        "kyc": models.IdentityVerification
    }
    
    if item_type not in model_map:
        raise HTTPException(status_code=400, detail="Invalid item type")
        
    model = model_map[item_type]
    
    if item_type == "caterers":
        profile = db.query(models.CatererProfile).get(item_id)
        if profile:
            item = db.query(models.User).get(profile.user_id)
            # Delete profile first due to FK if necessary, or just delete user if cascade is set
            db.delete(profile)
        else:
            item = db.query(models.User).get(item_id)
    else:
        item = db.query(model).get(item_id)
        
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    db.delete(item)
    db.commit()
    
    return RedirectResponse(url="/admin/archives?success_msg=Item+deleted+permanently", status_code=303)


# ─── Notifications ────────────────────────────────────────────────────────────

@router.get("/notifications", response_class=HTMLResponse)
async def admin_notifications(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    notifications = db.query(models.Notification).filter(
        models.Notification.user_id == user.id
    ).order_by(models.Notification.created_at.desc()).all()
    
    return templates.TemplateResponse("admin/notifications.html", {
        "request": request,
        "user": user,
        "active_page": "notifications",
        "notifications": notifications
    })

@router.get("/api/notifications/unread")
async def get_unread_notifications(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    count = db.query(models.Notification).filter(
        models.Notification.user_id == user.id,
        models.Notification.is_read == False
    ).count()
    return {"success": True, "unread_count": count}

@router.post("/api/notifications/{notif_id}/mark-read")
async def mark_notification_read(
    notif_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    notif = db.query(models.Notification).filter(
        models.Notification.id == notif_id,
        models.Notification.user_id == user.id
    ).first()
    
    if notif and not notif.is_read:
        notif.is_read = True
        db.commit()
        
    return {"success": True}

@router.post("/api/notifications/{notif_id}/delete")
async def delete_notification(
    notif_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    notif = db.query(models.Notification).filter(
        models.Notification.id == notif_id,
        models.Notification.user_id == user.id
    ).first()
    
    if notif:
        db.delete(notif)
        db.commit()
        
    return {"success": True}

# ─── Booking Management ────────────────────────────────────────────────────────

@router.get("/bookings", response_class=HTMLResponse)
async def admin_bookings(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    bookings = db.query(models.Booking).filter(models.Booking.is_archived == False).order_by(models.Booking.created_at.desc()).all()
    
    # Calculate metrics
    total_revenue = sum((b.total_amount or 0.0) for b in bookings if b.status != 'cancelled')
    pending_bookings = sum(1 for b in bookings if b.status == 'pending')
    
    metrics = {
        "total_revenue": total_revenue,
        "pending_bookings": pending_bookings,
        "total_bookings": len(bookings)
    }

    return templates.TemplateResponse("admin/bookings.html", {
        "request": request,
        "user": user,
        "bookings": bookings,
        "metrics": metrics,
        "active_page": "bookings"
    })

@router.get("/api/bookings/{booking_id}/details")
async def api_booking_details(
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        return {"success": False, "message": "Booking not found"}
        
    customer_data = None
    if booking.user:
        v = booking.user.identity_verification
        customer_data = {
            "name": f"{booking.user.first_name} {booking.user.last_name}",
            "email": booking.user.email,
            "kyc": {
                "status": v.verification_status if v else "Not Started",
                "id_url": v.document_url if v else None,
                "selfie_url": v.selfie_url if v else None,
                # Defensive check for match_score to prevent AttributeError
                "match_score": int(getattr(v, 'match_score', 0.0) * 100) if v else 0,
                "liveness": getattr(v, 'liveness_status', "N/A") if v else "N/A",
                "ocr_name": v.ocr_data.get("full_name") if v and v.ocr_data else "N/A"
            } if v else None
        }

    return {
        "success": True,
        "booking": {
            "id": booking.id,
            "event_name": booking.event_name,
            "event_type": booking.event_type,
            "event_date": booking.event_date.strftime('%b %d, %Y') if booking.event_date else "TBD",
            "event_time": booking.event_time.strftime('%I:%M %p') if booking.event_time else "TBD",
            "venue_address": booking.venue_address,
            "guest_count": booking.guest_count,
            "status": booking.status,
            "payment_status": booking.payment_status,
            "payment_method": booking.payment_method,
            "total_amount": float(booking.total_amount or 0),
            "customer": customer_data,
            "selected_items": [
                {
                    "name": item.menu_item.name if item.menu_item else "Deleted Item",
                    "price": float(item.price or 0),
                    "quantity": 1 # For now
                } for item in (booking.selected_items or [])
            ]
        }
    }

# ─── Customer Management ───────────────────────────────────────────────────────

@router.get("/customers", response_class=HTMLResponse)
async def admin_customers(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    # ONLY show Verified & KYC-Completed Customers here. 
    # Unverified/Pending go to Compliance Queue.
    customers = db.query(models.User).filter(
        models.User.role == "customer",
        models.User.is_archived == False,
        models.User.is_verified == True,
        models.User.is_kyc_complete == True
    ).order_by(models.User.created_at.desc()).all()
    
    # Metrics should reflect the entire database for a complete overview
    total_customers_all = db.query(models.User).filter(models.User.role == "customer", models.User.is_archived == False).count()
    verified_customers_all = db.query(models.User).filter(models.User.role == "customer", models.User.is_archived == False, models.User.is_verified == True).count()
    
    now = datetime.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    metrics = {
        "total_customers": total_customers_all,
        "verified_customers": verified_customers_all,
        "active_customers": verified_customers_all, # Mapping for template
        "new_this_month": db.query(models.User).filter(
            models.User.role == "customer",
            models.User.is_archived == False,
            models.User.created_at >= start_of_month
        ).count()
    }

    return templates.TemplateResponse("admin/customers.html", {
        "request": request,
        "user": user,
        "customers": customers,
        "metrics": metrics,
        "active_page": "customers"
    })

# ─── KYC Verification Terminal ────────────────────────────────────────────────

@router.post("/api/kyc/{kyc_id}/re-scan")
async def rescan_kyc_document(
    kyc_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    kyc = db.query(models.IdentityVerification).get(kyc_id)
    if not kyc or not kyc.document_url:
        return {"success": False, "message": "Verification record or document not found."}
    
    target_user = db.query(models.User).get(kyc.user_id)
    full_name = f"{target_user.first_name} {target_user.last_name}"
    
    try:
        # Re-run OCR using the improved extraction service
        result = verification_service.verify_id_document(
            kyc.document_url, 
            full_name, 
            kyc.id_number or "", 
            kyc.verification_type or "Passport",
            db,
            target_user.id
        )
        
        if result["status"] == "error":
            return {"success": False, "message": result["failure_reason"]}
            
        # Update KYC record with new findings
        kyc.ocr_data = result.get("ocr_data", {})
        kyc.id_detected = result.get("is_likely_id", False)
        kyc.id_number = result.get("ocr_data", {}).get("id_number") or kyc.id_number
        
        # Update fraud and pattern status if available
        if "pattern_valid" in result:
            # We don't have a direct field for pattern_valid, but we can store it in notes or ocr_data
            pass
            
        db.commit()
        db.refresh(kyc)
        
        return {"success": True, "ocr_data": kyc.ocr_data}
    except Exception as e:
        print(f"[RE-SCAN ERROR] {e}")
        return {"success": False, "message": str(e)}

@router.post("/verify/manual-action")
async def kyc_manual_action(
    target_user_id: int = Form(...),
    action: str = Form(...),
    reason: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    target_user = db.query(models.User).get(target_user_id)
    if not target_user:
        return {"success": False, "message": "User not found"}
        
    kyc = target_user.identity_verification
    if not kyc:
        return {"success": False, "message": "KYC record not found"}
        
    if action == "approve":
        kyc.verification_status = "approved"
        target_user.is_verified = True
        target_user.status = "active"
        
        # Log action
        audit = models.AuditLog(
            user_id=user.id,
            action="KYC_APPROVE",
            notes=f"Approved KYC for User ID {target_user_id}. Reason: {reason}"
        )
        db.add(audit)
        
        # Send Email notification
        background_tasks.add_task(
            EmailService.send_kyc_approval_email, 
            target_user.email, 
            target_user.first_name
        )
    else:
        kyc.verification_status = "rejected"
        kyc.failure_reason = reason
        target_user.status = "suspended" # Terminate application usually means suspension
        
        # Log action
        audit = models.AuditLog(
            user_id=user.id,
            action="KYC_REJECT",
            notes=f"Rejected KYC for User ID {target_user_id}. Reason: {reason}"
        )
        db.add(audit)
        
        # Send Rejection Email
        background_tasks.add_task(
            EmailService.send_kyc_rejection_email,
            target_user.email,
            target_user.first_name,
            reason
        )
        
    db.commit()
    return RedirectResponse(url="/admin/dashboard?success_msg=Action+completed+successfully", status_code=303)
