from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile, BackgroundTasks
from typing import Optional
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from ..core.templates import templates
from sqlalchemy.orm import Session
import os, secrets, string
from ..db import database, models
from ..core import security as auth
from ..core.utils import is_dummy_email, is_dummy_name, is_dummy_phone, is_dummy_address
from ..services.email import EmailService
from datetime import datetime, timedelta
from sqlalchemy import func
import json, re

router = APIRouter(prefix="/admin", tags=["admin"])

# Standard dependency for admin access
admin_only = auth.RoleChecker(["admin"])

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
        "avg_rating": avg_rating,
        "total_reviews": total_reviews,
        "pending_bookings_count": pending_bookings_count,
        "confirmed_bookings_count": confirmed_bookings_count,
        "completed_bookings_count": completed_bookings_count,
    })

@router.get("/caterers", response_class=HTMLResponse)
async def manage_caterers(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    
    caterers = db.query(models.CatererProfile).join(models.User).filter(models.User.is_archived == False).all()
    
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

@router.get("/customers", response_class=HTMLResponse)
async def manage_customers(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    
    customers = db.query(models.User).filter(models.User.role == 'customer', models.User.is_archived == False).all()
    return templates.TemplateResponse("admin/customers.html", {
        "request": request,
        "user": user,
        "customers": customers,
        "active_page": "customers"
    })

@router.get("/bookings", response_class=HTMLResponse)
async def all_bookings(
    request: Request, 
    page: int = 1,
    limit: int = 5,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    offset = (page - 1) * limit
    
    # Filter out draft and archived bookings
    query = db.query(models.Booking).filter(models.Booking.status != 'draft', models.Booking.is_archived == False)
    
    total_bookings = query.count()
    bookings = query.order_by(models.Booking.created_at.desc()).offset(offset).limit(limit).all()
    
    total_pages = (total_bookings + limit - 1) // limit
    
    return templates.TemplateResponse("admin/bookings.html", {
        "request": request,
        "user": user,
        "bookings": bookings,
        "page": page,
        "total_pages": total_pages,
        "limit": limit,
        "active_page": "bookings"
    })


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
    return RedirectResponse(url="/admin/caterers?success_msg=Caterer+deleted+successfully", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/caterers/check-availability")
async def check_caterer_availability(
    email: Optional[str] = None,
    business_name: Optional[str] = None,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    results = {
        "email_taken": False,
        "business_name_taken": False
    }
    
    if email:
        # Check against non-archived users
        existing_user = db.query(models.User).filter(
            models.User.email == email.strip().lower(),
            models.User.is_archived == False
        ).first()
        if existing_user:
            results["email_taken"] = True
            
    if business_name:
        # Check against all caterer profiles (usually business names are unique/important)
        existing_profile = db.query(models.CatererProfile).filter(
            func.lower(models.CatererProfile.business_name) == business_name.strip().lower()
        ).first()
        if existing_profile:
            results["business_name_taken"] = True
            
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
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    # 1. Server-side Validation
    errors = {}
    
    # Email check
    email_err = is_dummy_email(email)
    if email_err:
        errors['email'] = email_err
    else:
        existing_user = db.query(models.User).filter(models.User.email == email).first()
        if existing_user:
            errors['email'] = "Account with this email already exists."

    # Name check
    name_err = is_dummy_name(full_name)
    if name_err:
        errors['full_name'] = name_err

    # Business Name check
    if not business_name or len(business_name.strip()) < 3:
        errors['business_name'] = "Business name must be at least 3 characters."
    elif is_dummy_name(business_name): # Reuse name check for biz name
        errors['business_name'] = "Please use a real business name."

    # Phone check
    phone_err = is_dummy_phone(phone)
    if phone_err:
        errors['phone'] = phone_err

    # City/Address check
    addr_err = is_dummy_address(city)
    if addr_err:
        errors['city'] = addr_err

    if errors:
        return {"success": False, "errors": errors, "message": "Please correct the errors below."}

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
            city=city,
            verification_status="Verified",
            is_verified=True,
            slug=business_name.lower().replace(" ", "-") + f"-{new_user.id}"
        )
        db.add(new_profile)
        db.commit()

        # 5. Send Email in Background
        background_tasks.add_task(EmailService.send_caterer_account_created_email, email, temp_password, business_name)

        return {"success": True, "message": "Caterer account created! The credentials have been sent to their email."}

    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Error creating account: {str(e)}"}

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
async def view_verification(
    user_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    target_user = db.query(models.User).get(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get identity verification or caterer profile
    verification = target_user.identity_verification
    caterer_profile = target_user.caterer_profile
    
    return templates.TemplateResponse("admin/verification_detail.html", {
        "request": request,
        "user": user,
        "target_user": target_user,
        "verification": verification,
        "caterer_profile": caterer_profile,
        "active_page": target_user.role + "s"
    })

@router.get("/kyc")
async def view_kyc_queue(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    # Fetch all customers who are unverified OR recently verified
    # Limit verified history to recent 50 to keep things fast
    unverified_users = db.query(models.User).filter(
        models.User.role == "customer",
        models.User.is_verified == False,
        models.User.is_archived == False
    ).order_by(models.User.created_at.desc()).all()

    verified_users = db.query(models.User).filter(
        models.User.role == "customer",
        models.User.is_verified == True,
        models.User.is_archived == False
    ).order_by(models.User.updated_at.desc()).limit(50).all()

    # Create a unified customer list
    # Note: We put unverified at top, then verified
    customers = unverified_users + verified_users
    
    # KYC records for status mapping
    kyc_requests = db.query(models.IdentityVerification).filter(
        models.IdentityVerification.is_archived == False
    ).all()
    kyc_map = {k.user_id: k for k in kyc_requests}
    
    # Fetch all caterers (Pending + Recent Verified)
    pending_caterers = db.query(models.CatererProfile).filter(
        models.CatererProfile.verification_status == "Pending"
    ).order_by(models.CatererProfile.created_at.desc()).all()

    verified_caterers = db.query(models.CatererProfile).filter(
        models.CatererProfile.verification_status == "Verified"
    ).order_by(models.CatererProfile.created_at.desc()).limit(50).all()

    caterers = pending_caterers + verified_caterers
    
    return templates.TemplateResponse("admin/kyc_logs.html", {
        "request": request,
        "user": user,
        "customers": customers,
        "kyc_map": kyc_map,
        "caterers": caterers,
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

@router.post("/kyc/{kyc_id}/action")
async def kyc_manual_action(
    kyc_id: int,
    action: str = Form(...),
    notes: str = Form(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    kyc = db.query(models.IdentityVerification).get(kyc_id)
    if not kyc:
        raise HTTPException(status_code=404, detail="KYC record not found")
    
    target_user = db.query(models.User).get(kyc.user_id)
    
    if action == "approve":
        kyc.verification_status = "approved"
        target_user.is_verified = True
        target_user.is_kyc_complete = True
    else:
        kyc.verification_status = "rejected"
        kyc.failure_reason = notes or "Rejected after manual review."
    
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
    
    return RedirectResponse(url="/admin/kyc?success_msg=KYC+action+processed", status_code=303)

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

@router.get("/reviews", response_class=HTMLResponse)
async def admin_reviews(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    reviews = db.query(models.Review).filter(models.Review.is_archived == False).order_by(models.Review.created_at.desc()).all()
    return templates.TemplateResponse("admin/reviews.html", {
        "request": request,
        "user": user,
        "reviews": reviews,
        "active_page": "reviews"
    })

@router.post("/reviews/{review_id}/highlight")
async def toggle_review_highlight(
    review_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    review = db.query(models.Review).get(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.is_highlighted = not review.is_highlighted
    db.commit()
    return RedirectResponse(url="/admin/reviews?success_msg=Review+status+updated", status_code=303)

@router.post("/reviews/{review_id}/delete")
async def delete_review(
    review_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    review = db.query(models.Review).get(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    db.delete(review)
    db.commit()
    return RedirectResponse(url="/admin/reviews?success_msg=Review+deleted", status_code=303)

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

    return templates.TemplateResponse("admin/payments.html", {
        "request": request,
        "user": user,
        "bookings": bookings,
        "commission_rate": commission_rate,
        "active_page": "payments"
    })

@router.get("/payouts", response_class=HTMLResponse)
async def admin_payouts(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    payouts = db.query(models.Payout).filter(models.Payout.is_archived == False).order_by(models.Payout.created_at.desc()).all()
    return templates.TemplateResponse("admin/payouts.html", {
        "request": request,
        "user": user,
        "payouts": payouts,
        "active_page": "payouts"
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
