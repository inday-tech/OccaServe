from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, File, UploadFile
from jose import JWTError, jwt
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from ..core.templates import templates
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import EmailStr, ValidationError

from ..db import database, schemas, models
from ..core import security as security_auth, utils
from ..core.encryption import encrypt_data
from ..services.verification import verification_service
from ..services.email import EmailService

# Router instance
router = APIRouter(prefix="/auth", tags=["auth"])

UPLOAD_DIR = "app/static/uploads/verification"
os.makedirs(UPLOAD_DIR, exist_ok=True)

from ..core.utils import (
    is_gibberish, calculate_entropy, is_keyboard_walk, 
    is_dummy_email, is_dummy_name, is_dummy_phone, is_dummy_address,
    validate_file_type_and_size
)

@router.get("/check-phone")
async def check_phone(phone: str, db: Session = Depends(database.get_db)):
    """Check if phone number is already registered."""
    phone = phone.strip().replace(" ", "")
    existing = db.query(models.User).filter(models.User.phone_number == phone).first()
    if existing:
        return {"available": False, "message": "This mobile number is already registered to another account."}
    return {"available": True}

@router.get("/check-business-name")
async def check_business_name(name: str, db: Session = Depends(database.get_db)):
    """Check if business name is already taken (case-insensitively)."""
    stripped_name = name.strip()
    existing = db.query(models.CatererProfile).filter(
        func.lower(models.CatererProfile.business_name) == func.lower(stripped_name)
    ).first()
    return {"available": existing is None}

@router.post("/scan-document")
async def scan_document(
    document: List[UploadFile] = File(...),
    doc_type: str = Form("id"), # "id" or "permit"
    user_name: str = Form(...), # Business Name or Full Name
    owner_name: Optional[str] = Form(None), # Added for Permit owners
    id_type: Optional[str] = Form(None),
    id_number: Optional[str] = Form(None), # New: ID number for verification
    reference_doc: Optional[str] = Form(None), # URL of previously uploaded ID for comparison
    db: Session = Depends(database.get_db)
):
    """AJAX endpoint for real-time document scanning."""
    try:
        results = []
        doc_urls = []
        
        for doc in document:
            content = await doc.read()
            
            # --- SECURITY: File Validation ---
            file_error = validate_file_type_and_size(content, doc.filename)
            if file_error:
                return {"status": "rejected", "failure_reason": f"File Security: {file_error}"}

            temp_id = str(uuid.uuid4())
            filename = f"temp_{temp_id}_{doc.filename}"
            path = os.path.join(UPLOAD_DIR, filename)
            
            encrypted_content = encrypt_data(content)
            with open(path, "wb") as f:
                f.write(encrypted_content)
            
            doc_urls.append(f"/static/uploads/verification/{filename}")
        
        doc_url = doc_urls[0]
        
        if doc_type == "permit":
            result = await verification_service.verify_business_permit(
                doc_url, user_name, owner_name=owner_name or user_name, db=db
            )
        elif doc_type == "menu":
            result = await verification_service.verify_menu_document(doc_url)
        elif doc_type == "selfie":
            imgs = [verification_service._prepare_image(u) for u in doc_urls]
            liveness = verification_service._check_liveness_mediapipe(imgs)
            img = imgs[0] # Use first image for face comparison
            
            if liveness.get("occlusion_detected"):
                return {
                    "status": "rejected",
                    "failure_reason": f"Face Occluded: {liveness['failure_reason']}",
                    "occlusion": True
                }

            # If reference ID provided, compare faces
            comparison = {"match": True, "confidence": 1.0}
            if reference_doc:
                try:
                    id_img = verification_service._prepare_image(reference_doc)
                    comparison = verification_service.compare_faces(id_img, img)
                except Exception as comp_err:
                    print(f"[KYC DEBUG] Comparison error: {comp_err}")

            # Liveness threshold: 0.4 for sequence (requires blink/move), 0.15 for single frame (just face detection)
            threshold = 0.4 if len(doc_urls) > 1 else 0.15
            
            if liveness["score"] >= threshold and comparison["match"]:
                result = {
                    "status": "approved",
                    "confidence": comparison["confidence"],
                    "ocr_match": True
                }
            else:
                reason = "Face mismatch or poor quality."
                if not comparison["match"]:
                    reason = "Face does not match the provided ID."
                elif liveness["score"] < threshold:
                    reason = "Liveness check failed. Please blink or move slightly."
                
                result = {
                    "status": "rejected",
                    "failure_reason": reason,
                    "ocr_match": False
                }
        else:
            result = await verification_service.verify_id_document(doc_url, user_name, id_number or "", id_type or "Passport")
            # Return path to be used as reference for selfie comparison
            result["doc_path"] = doc_url
            # Ensure ocr_data is always in the response for frontend display
            if "ocr_data" not in result:
                result["ocr_data"] = {}
            
        return result
    except Exception as e:
        print(f"[AUTH OCR ERROR] {e}")
        return {"status": "error", "failure_reason": str(e)}

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, next: Optional[str] = None, db: Session = Depends(database.get_db)):
    user = None
    token = request.cookies.get("access_token")
    if token and token.startswith("Bearer "):
        token = token.split(" ")[1]
        user = security_auth.verify_token(token, db)
        
    return templates.TemplateResponse("auth/register.html", {
        "request": request, 
        "next_url": next,
        "user": user
    })

@router.get("/register/caterer", response_class=HTMLResponse)
def register_caterer_page(request: Request, next: Optional[str] = None, db: Session = Depends(database.get_db)):
    user = None
    token = request.cookies.get("access_token")
    if token and token.startswith("Bearer "):
        token = token.split(" ")[1]
        user = security_auth.verify_token(token, db)
    
    return templates.TemplateResponse("auth/register_caterer.html", {
        "request": request, 
        "next_url": next,
        "user": user
    })

from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, File, UploadFile, BackgroundTasks

@router.post("/register")
async def register(
    request: Request,
    background_tasks: BackgroundTasks,
    role: str = Form("customer"),
    full_name: str = Form(""),
    email: str = Form(...),
    mobile_number: str = Form(...),
    address: Optional[str] = Form(""),
    password: str = Form(...),
    confirm_password: str = Form(...),
    # Separate name fields (caterer form)
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    middle_name: Optional[str] = Form(None),
    # Caterer fields
    business_name: str = Form(None),
    business_type: str = Form(None),
    years_of_operation: Optional[int] = Form(0),

    business_description: str = Form(None),
    coverage_area: str = Form(None),
    payout_method: str = Form(None),
    payout_account_name: Optional[str] = Form(None),
    account_number: Optional[str] = Form(None),
    event_types: Optional[str] = Form(None), # RESTORED
    pax_range: Optional[str] = Form(None),
    city: Optional[str] = Form(None), # RESTORED
    min_pax: Optional[int] = Form(None),
    team_size: Optional[int] = Form(None),
    sample_menu: Optional[UploadFile] = File(None),
    logo: Optional[UploadFile] = File(None), # RESTORED
    permit: Optional[UploadFile] = File(None),
    gov_id: Optional[UploadFile] = File(None),
    selfie: Optional[UploadFile] = File(None), # NEW: Added Selfie
    id_type: Optional[str] = Form(None),
    id_number: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    next_url: Optional[str] = Form(None),
    db: Session = Depends(database.get_db)
):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or \
              "application/json" in request.headers.get("Accept", "")
    
    # Always initialize mn to prevent UnboundLocalError
    mn = (middle_name or "").strip()

    # Compose full_name from separate fields if provided, otherwise split existing full_name
    if first_name and last_name:
        # Separate fields provided (caterer form)
        first_name = first_name.strip()
        last_name = last_name.strip()
        full_name = f"{first_name} {mn + ' ' if mn else ''}{last_name}".strip()
    elif full_name and full_name.strip():
        # Legacy: single full_name field — split into first and last
        parts = full_name.strip().split(None, 1)
        if len(parts) > 1:
            first_name, last_name = parts[0], parts[1]
        else:
            first_name, last_name = parts[0], ""
    else:
        first_name = first_name or ""
        last_name = last_name or ""
        full_name = f"{first_name} {last_name}".strip()
        
    otp = None # Initialize OTP to prevent NameError later

    # server‑side validation
    errors = {}
    import re
    if not re.match(r'^[a-zA-Z0-9._%+-]+@gmail\.com$', email):
        errors["email"] = "Gmail only (@gmail.com)"
    else:
        dummy_error = is_dummy_email(email)
        if dummy_error:
            errors["email"] = dummy_error

    if not full_name.strip():
        errors["full_name"] = "Full name is required"
    else:
        name_error = is_dummy_name(full_name)
        if name_error: 
            errors["full_name"] = name_error
            
        if first_name and last_name and first_name.lower() == last_name.lower():
            errors["full_name"] = "First Name and Last Name cannot be identical"
            
        name_parts = full_name.lower().split()
        if len(name_parts) > 1 and len(set(name_parts)) < len(name_parts):
            errors["full_name"] = "Name contains repetitive parts (e.g., John John)"

    if not mobile_number.isdigit():
        errors["mobile_number"] = "Mobile number must contain only digits"
    else:
        phone_error = is_dummy_phone(mobile_number)
        if phone_error: 
            errors["mobile_number"] = phone_error
        else:
            # Uniqueness Check
            existing_phone = db.query(models.User).filter(models.User.phone_number == mobile_number).first()
            if existing_phone:
                errors["mobile_number"] = "This mobile number is already registered."

    password_msgs = []
    if len(password) < 8:
        password_msgs.append("at least 8 chars")
    
    import re
    if not re.search(r"[A-Z]", password):
        password_msgs.append("uppercase")
    if not re.search(r"[a-z]", password):
        password_msgs.append("lowercase")
    if not re.search(r"[0-9]", password):
        password_msgs.append("number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        password_msgs.append("symbol")

    if password_msgs:
        errors["password"] = "Password must include: " + ", ".join(password_msgs)

    if password != confirm_password:
        errors["confirm_password"] = "Passwords do not match"

    if role == "caterer":
        if not address or not address.strip():
            errors["address"] = "Business Address is required"
        else:
            addr_error = is_dummy_address(address)
            if addr_error:
                errors["address"] = addr_error

        if not business_name or not business_name.strip():
            errors["business_name"] = "Business name is required for caterers"
        else:
            # Use is_valid_business_name (allows apostrophes, ampersands, numbers, commas)
            # NOT is_dummy_name which calls is_valid_person_name and rejects these chars
            from ..core.utils import is_valid_business_name
            bn_error = is_valid_business_name(business_name)
            if bn_error:
                errors["business_name"] = bn_error

            # Uniqueness Check (case-insensitive)
            existing_biz = db.query(models.CatererProfile).filter(
                func.lower(models.CatererProfile.business_name) == func.lower(business_name.strip())
            ).first()
            if existing_biz:
                errors["business_name"] = "This business name is already registered."

        if years_of_operation is not None and (years_of_operation < 0 or years_of_operation > 100):
            errors["years_of_operation"] = "Years of operation must be between 0 and 100"

        # Default min_pax to 1 if not provided (for backward compat with older form versions)
        if min_pax is None:
            min_pax = 1
        if min_pax < 1 or min_pax > 5000:
            errors["min_pax"] = "Minimum Pax must be between 1 and 5,000"

    # Only return error if there ARE validation errors
    if errors:
        if is_ajax:
            return JSONResponse(status_code=400, content={"success": False, "message": "Please correct the highlighted fields.", "field_errors": errors})
        template = "auth/register_caterer.html" if role == "caterer" else "auth/register.html"
        return templates.TemplateResponse(template, {
            "request": request,
            "error": "Please correct the highlighted fields.",
            "field_errors": errors,
            "next_url": next_url,
            "role": role
        })

    user = db.query(models.User).filter(models.User.email == email).first()
    
    # Check if this is a social user upgrading to caterer
    is_upgrade = False
    if user and user.auth_provider != 'email' and user.role == "pending":
        is_upgrade = True
    elif user:
        if not user.is_email_verified:
            # If user exists but not verified, generate new OTP and redirect
            otp = utils.get_random_digits(6)
            user.verification_code = otp
            from datetime import datetime, timedelta, timezone
            user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
            db.commit()
            
            try:
                EmailService.send_verification_email(email, otp)
            except Exception as e:
                print(f"[AUTH ERROR] Failed to resend verification email: {e}")
                
            verify_url = f"/auth/verify?email={email}"
            if next_url: verify_url += f"&next={next_url}"
            return RedirectResponse(url=verify_url, status_code=status.HTTP_303_SEE_OTHER)

        if user.is_email_verified:
            if is_ajax:
                return JSONResponse(status_code=400, content={"success": False, "message": "Email already registered and verified. Please login."})
            template = "auth/register_caterer.html" if role == "caterer" else "auth/register.html"
            return templates.TemplateResponse(template, {
                "request": request,
                "error": "Email already registered and verified. Please login.",
                "next_url": next_url,
                "role": role
            })
    
    if is_upgrade:
        # Update existing social user
        user.first_name = first_name
        user.middle_name = mn
        user.last_name = last_name
        user.phone_number = mobile_number
        user.address = address
        user.role = role
        user.status = "pending_approval" if role == "caterer" else "active"
        db.commit()
    else:
        # Buffer new email/password user in session instead of DB
        hashed_password = security_auth.get_password_hash(password)
        otp = utils.get_random_digits(6)
        
        # Save files if caterer
        logo_url = "/static/images/default_caterer.png"
        gov_id_url = ""
        permit_url = ""
        sample_menu_url = ""
        
        if role == "caterer":
            # --- ENHANCED SECURITY: Check if registration is from a blocked dummy ---
            if is_gibberish(full_name) or is_dummy_name(full_name):
                return templates.TemplateResponse("auth/register_caterer.html", {
                    "request": request, "error": "Please provide a valid legal name."
                })

            # Process Selfie Upload (saved as plain file for reliable viewing)
            selfie_url = None
            if selfie:
                content = await selfie.read()
                filename = f"selfie_{uuid.uuid4().hex}_{selfie.filename}"
                path = os.path.join(UPLOAD_DIR, filename)
                with open(path, "wb") as f:
                    f.write(content)
                selfie_url = f"/static/uploads/verification/{filename}"

            temp_id = str(uuid.uuid4())
            
            # Ensure upload directory for profiles
            PROFILE_DIR = "app/static/uploads/profiles"
            os.makedirs(PROFILE_DIR, exist_ok=True)

            if logo and logo.filename:
                file_ext = os.path.splitext(logo.filename)[1]
                file_name = f"{temp_id}_logo{file_ext}"
                file_path = os.path.join(PROFILE_DIR, file_name)
                with open(file_path, "wb") as buffer:
                    buffer.write(await logo.read())
                logo_url = f"/static/uploads/profiles/{file_name}"

            if gov_id and gov_id.filename:
                content = await gov_id.read()
                file_path = os.path.join(UPLOAD_DIR, f"{temp_id}_gov_id_{gov_id.filename}")
                with open(file_path, "wb") as buffer:
                    buffer.write(content)
                gov_id_url = f"/static/uploads/verification/{temp_id}_gov_id_{gov_id.filename}"
                
            if permit and permit.filename:
                content = await permit.read()
                
                # --- SECURITY: File Validation ---
                file_error = validate_file_type_and_size(content, permit.filename)
                if file_error:
                    return templates.TemplateResponse("auth/register_caterer.html", {
                        "request": request, "error": f"Permit File: {file_error}", "role": role
                    })

                file_path = os.path.join(UPLOAD_DIR, f"{temp_id}_permit_{permit.filename}")
                with open(file_path, "wb") as buffer:
                    buffer.write(content)
                permit_url = f"/static/uploads/verification/{temp_id}_permit_{permit.filename}"

            if sample_menu and sample_menu.filename:
                content = await sample_menu.read()
                
                # --- SECURITY: File Validation ---
                file_error = validate_file_type_and_size(content, sample_menu.filename, max_size_mb=10) # Menus can be larger
                if file_error:
                    return templates.TemplateResponse("auth/register_caterer.html", {
                        "request": request, "error": f"Menu File: {file_error}", "role": role
                    })

                file_path = os.path.join(UPLOAD_DIR, f"{temp_id}_menu_{sample_menu.filename}")
                with open(file_path, "wb") as buffer:
                    buffer.write(content)
                sample_menu_url = f"/static/uploads/verification/{temp_id}_menu_{sample_menu.filename}"

        event_list = []
        if event_types:
            event_list = [e.strip() for e in event_types.split(",") if e.strip()]

        from datetime import datetime, timedelta, timezone
        
        new_user = models.User(
            email=email, 
            password_hash=hashed_password,
            role=role, 
            first_name=first_name,
            middle_name=mn,
            last_name=last_name,
            phone_number=mobile_number,
            address=address,
            status="pending_verification",
            is_verified=False,
            is_email_verified=False,
            verification_code=otp,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            profile_image_url=selfie_url if role == "caterer" else None
        )
        db.add(new_user)
        db.flush()

        if role == "caterer":
            new_profile = models.CatererProfile(
                user_id=new_user.id,
                business_name=business_name,
                business_type=business_type,
                years_of_operation=years_of_operation or 0,

                description=business_description,
                coverage_area=coverage_area,
                payout_method=payout_method,
                payout_account_name=payout_account_name,
                payout_account_number=account_number,
                contact_address=address,
                contact_phone=mobile_number,
                logo_url=logo_url,
                event_types=event_list,
                min_pax=min_pax,
                city=city,
                sample_menu_url=sample_menu_url,
                permit_url=permit_url,
                gov_id_url=gov_id_url,
                latitude=latitude,
                longitude=longitude,
                verification_status="Not Verified",
                status="Pending Approval",
                team_size=team_size
            )
            db.add(new_profile)

            # Create IdentityVerification record so admin can view docs in verification detail
            if gov_id_url or selfie_url:
                identity_record = models.IdentityVerification(
                    user_id=new_user.id,
                    document_url=gov_id_url if gov_id_url else None,
                    selfie_url=selfie_url if selfie_url else None,
                    verification_type=id_type or "Government ID",
                    id_number=id_number,
                    verification_status="pending"
                )
                db.add(identity_record)



        db.flush()
        
        if role == "caterer":
            from ..services.realtime import manager
            import asyncio
            admins = db.query(models.User).filter(models.User.role == "admin").all()
            for admin in admins:
                new_notif = models.Notification(
                    user_id=admin.id,
                    title="New Caterer Application",
                    message=f"{business_name} has registered as a new caterer partner.",
                    link="/admin/kyc",
                    type="info"
                )
                db.add(new_notif)
            db.flush()
            
            for admin in admins:
                count = db.query(models.Notification).filter(models.Notification.user_id == admin.id, models.Notification.is_read == False).count()
                asyncio.create_task(manager.broadcast_to_user(admin.id, {
                    "type": "new_notification",
                    "message": f"New Caterer Application: {business_name}",
                    "count": count
                }))
    
    # Only send verification email if it's a new email/password user

    if not is_upgrade:
        try:
            if EmailService.send_verification_email(email, otp):
                print(f"[AUTH] Registration buffered for {email}. Verification email sent.")
                db.commit() # Commit all changes only if email is sent
                if role == "caterer":
                    background_tasks.add_task(utils.background_geocode, new_profile.id)
            else:
                db.rollback()
                if is_ajax:
                    return JSONResponse(status_code=500, content={"success": False, "message": f"Failed to send verification email to {email}."})
                template = "auth/register_caterer.html" if role == "caterer" else "auth/register.html"
                return templates.TemplateResponse(template, {
                    "request": request, 
                    "error": f"Failed to send verification email to {email}. Please check your email address or try again later.",
                    "next_url": next_url,
                    "role": role,
                    "submitted_data": locals()
                })
        except Exception as e:
            db.rollback()
            print(f"[AUTH ERROR] Failed to send verification email: {e}")
            if is_ajax:
                return JSONResponse(status_code=500, content={"success": False, "message": f"Email service error: {str(e)}"})
            template = "auth/register_caterer.html" if role == "caterer" else "auth/register.html"
            return templates.TemplateResponse(template, {
                "request": request, 
                "error": f"Email service error: {str(e)}",
                "next_url": next_url,
                "role": role,
                "submitted_data": locals()
            })
    else:
        db.commit() # Upgrade users don't need email OTP at this stage
            
    # Redirect logic
    if is_upgrade:
        redirect_url = next_url if next_url else utils.get_dashboard_url(user.role)
        response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
        access_token_expires = timedelta(minutes=security_auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security_auth.create_access_token(
            data={"sub": user.email, "role": user.role},
            expires_delta=access_token_expires
        )
        response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
        return response

    if is_ajax:
        verify_url = f"/auth/verify?email={email}"
        if next_url:
            verify_url += f"&next={next_url}"
        return JSONResponse(content={"status": "success", "email": email, "redirect": verify_url})

    verify_url = f"/auth/verify?email={email}"
    if next_url:
        verify_url += f"&next={next_url}"
        
    return RedirectResponse(url=verify_url, status_code=status.HTTP_303_SEE_OTHER)

@router.get("/verify", response_class=HTMLResponse)
def verify_email_page(request: Request, email: str = "", next: Optional[str] = None):
    return templates.TemplateResponse("auth/verify_email.html", {"request": request, "email": email, "next_url": next})

@router.get("/pending", response_class=HTMLResponse)
def pending_approval_page(request: Request, email: str = "", uid: Optional[int] = None):
    return templates.TemplateResponse("auth/pending_approval.html", {"request": request, "email": email, "user_id": uid})

@router.post("/verify")
def verify_email_submit(
    request: Request,
    email: str = Form(...),
    code: str = Form(...),
    next_url: Optional[str] = Form(None),
    db: Session = Depends(database.get_db)
):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or \
              "application/json" in request.headers.get("Accept", "")
              
    user = db.query(models.User).filter(models.User.email == email).first()
    
    if user:
        if user.is_email_verified:
            redirect_url = next_url if next_url else utils.get_dashboard_url(user.role)
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

        if user.verification_code == code.strip():
            from datetime import datetime, timezone
            if user.otp_expires_at:
                now_time = datetime.now(timezone.utc)
                expire_time = user.otp_expires_at
                if expire_time.tzinfo is None:
                    expire_time = expire_time.replace(tzinfo=timezone.utc)
                
                if now_time > expire_time:
                    if is_ajax:
                        return JSONResponse(status_code=400, content={"success": False, "message": "Verification code expired. Please request a new one."})
                    return templates.TemplateResponse("auth/verify_email.html", {"request": request, "email": email, "error": "Verification code expired. Please request a new one."})

            user.is_email_verified = True
            user.verification_code = None
            user.otp_expires_at = None
            if user.role == "caterer" and user.status == "pending_verification":
                user.status = "pending_approval"
            elif user.status == "pending_verification":
                user.status = "active"
                
            from sqlalchemy.sql import func
            user.last_login = func.now()
            db.commit()
            
            # Phase 1: Notify Admins of New Verified Customer
            if user.role == "customer":
                from ..services.realtime import manager
                import asyncio
                admins = db.query(models.User).filter(models.User.role == "admin").all()
                for admin in admins:
                    new_notif = models.Notification(
                        user_id=admin.id,
                        title="New Customer Registration",
                        message=f"Customer {user.first_name} {user.last_name} has registered and verified their email.",
                        link="/admin/customers",
                        type="info"
                    )
                    db.add(new_notif)
                    db.commit()
                    
                    count = db.query(models.Notification).filter(models.Notification.user_id == admin.id, models.Notification.is_read == False).count()
                    asyncio.create_task(manager.broadcast_to_user(admin.id, {
                        "type": "new_notification",
                        "message": f"New Customer: {user.first_name}",
                        "count": count
                    }))
        else:
            if is_ajax:
                return JSONResponse(status_code=400, content={"success": False, "message": "Invalid verification code"})
            return templates.TemplateResponse("auth/verify_email.html", {"request": request, "email": email, "error": "Invalid verification code"})
    else:
        if is_ajax:
            return JSONResponse(status_code=404, content={"success": False, "message": "User not found or registration expired"})
        return templates.TemplateResponse("auth/verify_email.html", {"request": request, "email": email, "error": "User not found or registration expired"})
        
    # Check if this is a caterer that needs admin approval
    if user.role == "caterer" and user.status == "pending_approval":
        return RedirectResponse(url=f"/auth/pending?email={user.email}&uid={user.id}", status_code=status.HTTP_303_SEE_OTHER)

    access_token_expires = timedelta(minutes=security_auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security_auth.create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    redirect_url = next_url if next_url else utils.get_dashboard_url(user.role)
    if "?" in redirect_url:
        redirect_url += "&verified=success"
    else:
        redirect_url += "?verified=success"
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@router.post("/resend-code")
def resend_verification_code(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(database.get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return {"success": False, "message": "User not found"}
        
    if user.is_email_verified:
        return {"success": False, "message": "Email already verified"}

    # Generate new OTP
    otp = utils.get_random_digits(6)
    user.verification_code = otp
    from datetime import datetime, timedelta, timezone
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    db.commit()
    
    # Resend Email
    from ..services.email import EmailService
    if EmailService.send_verification_email(email, otp):
        return {"success": True, "message": "Verification code resent"}
    else:
        return {"success": False, "message": "Failed to send email. Please check your email address or try again later."}

@router.get("/verify-status")
def check_verify_status(email: str, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return {"verified": False}
    return {"verified": user.is_email_verified}

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: Optional[str] = None, db: Session = Depends(database.get_db)):
    # Check if already logged in
    token = request.cookies.get("access_token")
    if token and token.startswith("Bearer "):
        token = token.split(" ")[1]
        user = security_auth.verify_token(token, db)
        if user:
            return RedirectResponse(url=next if next else utils.get_dashboard_url(user.role))
            
    # Redirect to home with login modal
    return RedirectResponse(url="/?auth_modal=login" + (f"&next={next}" if next else ""))

@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next_url: Optional[str] = Form(None),
    db: Session = Depends(database.get_db)
):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or \
              "application/json" in request.headers.get("Accept", "")

    # basic validation
    if not email or not password:
        if is_ajax:
            return JSONResponse(status_code=400, content={"success": False, "error": "Email and password are required"})
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Email and password are required",
            "next_url": next_url
        })
    try:
        from pydantic import TypeAdapter
        TypeAdapter(EmailStr).validate_python(email)
    except ValidationError:
        if is_ajax:
            return JSONResponse(status_code=400, content={"success": False, "error": "Invalid email address"})
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Invalid email address",
            "next_url": next_url
        })

    search_email = email
    if email.lower() == "admin":
        search_email = "admin@occaserve.com"
        
    user = db.query(models.User).filter(func.lower(models.User.email) == search_email.lower().strip()).first()

    if not user:
        if is_ajax:
            return JSONResponse(status_code=401, content={"success": False, "error": "Invalid credentials"})
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Invalid credentials",
            "next_url": next_url
        })
    
    # Check if password matches
    if not security_auth.verify_password(password, user.password_hash):
        # If password fails, check if this is a social user who hasn't set a password yet
        if user.auth_provider != 'email':
            provider_name = user.auth_provider.capitalize()
            error_msg = f"This account is linked with {provider_name}. Please use the 'Sign in with {provider_name}' button."
            if is_ajax:
                return JSONResponse(status_code=403, content={"success": False, "error": error_msg})
            return templates.TemplateResponse("auth/login.html", {
                "request": request,
                "error": error_msg,
                "next_url": next_url
            })
            
        if is_ajax:
            return JSONResponse(status_code=401, content={"success": False, "error": "Invalid credentials"})
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Invalid credentials",
            "next_url": next_url
        })
    
    # --- STRICT LOGIN GATE FOR CATERERS ---
    if user.role == "caterer":
        if user.status in ["pending_approval", "pending_verification"]:
            error_msg = "Your account is currently under review by our administrators. Please wait for the approval notification before logging in."
            if is_ajax:
                return JSONResponse(status_code=403, content={"success": False, "error": error_msg, "status": user.status})
            return templates.TemplateResponse("auth/login.html", {
                "request": request,
                "error": error_msg,
                "next_url": next_url
            })
        elif user.status == "rejected":
            error_msg = "Your application has been declined due to compliance issues. Please contact support for more information."
            if is_ajax:
                return JSONResponse(status_code=403, content={"success": False, "error": error_msg, "status": "rejected"})
            return templates.TemplateResponse("auth/login.html", {
                "request": request,
                "error": error_msg,
                "next_url": next_url
            })
    
    if user.status != "active":
         if user.role == "caterer" and user.status == "pending_approval":
             if is_ajax:
                 return JSONResponse(content={"success": True, "redirect_url": f"/auth/pending?email={user.email}&uid={user.id}"})
             return RedirectResponse(url=f"/auth/pending?email={user.email}&uid={user.id}", status_code=status.HTTP_303_SEE_OTHER)
         
         if user.status == "suspended":
             error_msg = f"Your account has been suspended. Reason: {user.status_reason or 'No reason provided.'}"
         elif user.status == "rejected":
             error_msg = f"Your account application was rejected. Reason: {user.status_reason or 'Identity verification failed.'}"
         elif user.status == "investigation":
             error_msg = f"Your account is currently under investigation for compliance review. Reason: {user.status_reason or 'Routine security audit.'}"
         elif user.status == "pending_verification":
             error_msg = "Please follow the email link to verify your account."
         else:
             error_msg = "Account is inactive or pending approval."

         if is_ajax:
             return JSONResponse(status_code=403, content={"success": False, "error": error_msg})
         return templates.TemplateResponse("auth/login.html", {
             "request": request,
             "error": error_msg,
             "next_url": next_url
         })
        
    if not user.is_email_verified and user.role != "admin":
        if user.auth_provider == 'email':
             if is_ajax:
                return JSONResponse(status_code=403, content={"success": False, "error": "Please verify your email address.", "verification_needed": True})
             return templates.TemplateResponse("auth/login.html", {
                "request": request,
                "error": "Please verify your email address before logging in.",
                "verification_needed": True,
                "email": email,
                "next_url": next_url
            })

    # Update last_login
    user.last_login = func.now()
    db.commit()

    access_token_expires = timedelta(minutes=security_auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security_auth.create_access_token(
        data={"sub": user.email, "role": user.role}, 
        expires_delta=access_token_expires
    )
    
    refresh_token = security_auth.create_refresh_token(user_id=user.id, db=db)
    
    new_log = models.AuditLog(
        user_id=user.id,
        action="login",
        ip_address=request.client.host,
        notes="User logged in via email"
    )
    db.add(new_log)
    db.commit()

    # Smart Redirect with success param
    redirect_url = next_url if next_url else utils.get_dashboard_url(user.role)
    if "?" in redirect_url:
        redirect_url += "&login=success"
    else:
        redirect_url += "?login=success"

    if is_ajax:
        response = JSONResponse(content={"success": True, "redirect_url": redirect_url})
    else:
        response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, max_age=security_auth.REFRESH_TOKEN_EXPIRE_DAYS * 86400)
    return response

@router.post("/refresh")
async def refresh_token(request: Request, db: Session = Depends(database.get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    
    db_token = db.query(models.RefreshToken).filter(
        models.RefreshToken.token == refresh_token,
        models.RefreshToken.is_revoked == False,
        models.RefreshToken.expires_at > datetime.utcnow()
    ).first()
    
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    user = db.query(models.User).get(db_token.user_id)
    
    access_token = security_auth.create_access_token(data={"sub": user.email, "role": user.role})
    
    # Audit Log for token refresh
    new_log = models.AuditLog(
        user_id=user.id,
        action="refresh_token",
        ip_address=request.client.host,
        notes="Access token refreshed using refresh token"
    )
    db.add(new_log)
    db.commit()

    response = RedirectResponse(url=request.url, status_code=303)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse("auth/forgot_password.html", {"request": request})

@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(database.get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()
    if user:
        token = str(uuid.uuid4())
        user.reset_token = token
        user.reset_token_expires = datetime.now() + timedelta(hours=1)
        db.commit()
        
        # Send Email
        from ..services.email import EmailService
        EmailService.send_password_reset_email(email, token)
        
    # Always return success message for security (don't reveal if email exists)
    return templates.TemplateResponse("auth/forgot_password.html", {
        "request": request,
        "success": "If your email is registered, you will receive a reset link shortly."
    })

@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request, token: str):
    return templates.TemplateResponse("auth/reset_password.html", {"request": request, "token": token})

@router.post("/reset-password")
async def reset_password(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(database.get_db)
):
    user = db.query(models.User).filter(
        models.User.reset_token == token,
        models.User.reset_token_expires > datetime.now()
    ).first()
    
    if not user:
        return templates.TemplateResponse("auth/forgot_password.html", {
            "request": request,
            "error": "Invalid or expired reset token. Please request a new one."
        })
        
    user.password_hash = security_auth.get_password_hash(password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    
    return RedirectResponse(url="/auth/login?success=password_reset", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/logout")
def logout(request: Request, db: Session = Depends(database.get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        db_token = db.query(models.RefreshToken).filter(models.RefreshToken.token == refresh_token).first()
        if db_token:
            db_token.is_revoked = True
            db.commit()

    response = RedirectResponse(url="/?logout=success&auth_modal=login#home", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response

@router.get("/check-email")
def check_email_availability(email: str, db: Session = Depends(database.get_db)):
    dummy_error = is_dummy_email(email)
    if dummy_error:
        return {"available": False, "message": dummy_error}
    user = db.query(models.User).filter(func.lower(models.User.email) == email.lower().strip()).first()
    return {"available": user is None}

# --- Onboarding / Profile Completion ---

@router.get("/onboarding", response_class=HTMLResponse)
def onboarding_page(request: Request, db: Session = Depends(database.get_db)):
    token = request.cookies.get("access_token")
    if not token or not token.startswith("Bearer "):
        return RedirectResponse(url="/auth/login")
    
    token = token.split(" ")[1]
    user = security_auth.verify_token(token, db)
    if not user:
        return RedirectResponse(url="/auth/login")
        
    return templates.TemplateResponse("auth/onboarding.html", {"request": request, "user": user})

@router.post("/onboarding")
async def onboarding_submit(
    request: Request,
    role: str = Form(...),
    mobile_number: str = Form(None),
    address: str = Form(None),
    db: Session = Depends(database.get_db)
):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401)
        
    token = token.split(" ")[1]
    user = security_auth.verify_token(token, db)
    if not user:
        raise HTTPException(status_code=401)

    if role == "customer":
        user.role = "customer"
        user.phone_number = mobile_number
        user.address = address
        db.commit()
        return RedirectResponse(url="/customer/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    elif role == "caterer":
        # Role will be updated in the full caterer registration
        return RedirectResponse(url="/auth/register/caterer", status_code=status.HTTP_303_SEE_OTHER)
    
    return RedirectResponse(url="/", status_code=303)
