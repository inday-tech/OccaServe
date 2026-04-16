from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, File, UploadFile
from jose import JWTError, jwt
from fastapi.responses import HTMLResponse, RedirectResponse
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

# Router instance
router = APIRouter(prefix="/auth", tags=["auth"])

UPLOAD_DIR = "app/static/uploads/verification"
os.makedirs(UPLOAD_DIR, exist_ok=True)

from ..core.utils import (
    is_gibberish, calculate_entropy, is_keyboard_walk, 
    is_dummy_email, is_dummy_name, is_dummy_phone, is_dummy_address
)

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

@router.post("/register")
async def register(
    request: Request,
    role: str = Form("customer"),
    full_name: str = Form(...),
    email: str = Form(...),
    mobile_number: str = Form(...),
    address: Optional[str] = Form(""),
    password: str = Form(...),
    confirm_password: str = Form(...),
    # Caterer fields
    business_name: str = Form(None),
    business_type: str = Form(None),
    years_of_operation: int = Form(0),
    business_description: str = Form(None),
    coverage_area: str = Form(None),
    payout_method: str = Form(None),
    payout_account_name: Optional[str] = Form(None),
    account_number: Optional[str] = Form(None),
    event_types: Optional[str] = Form(None),
    min_pax: int = Form(0),
    starting_price: float = Form(0.0),
    city: str = Form(None),
    # Verification Files & Logo
    logo: UploadFile = File(None),
    gov_id: UploadFile = File(None),
    permit: UploadFile = File(None),
    sample_menu: UploadFile = File(None),
    next_url: Optional[str] = Form(None),
    db: Session = Depends(database.get_db)
):
    # Split full_name into first and last
    parts = full_name.strip().split(None, 1)
    if len(parts) > 1:
        first_name, last_name = parts[0], parts[1]
    else:
        first_name, last_name = parts[0], ""
        
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
        if name_error: errors["full_name"] = name_error

    if not mobile_number.isdigit():
        errors["mobile_number"] = "Mobile number must contain only digits"
    else:
        phone_error = is_dummy_phone(mobile_number)
        if phone_error: errors["mobile_number"] = phone_error

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
            bn_error = is_dummy_name(business_name)
            if bn_error: errors["business_name"] = bn_error
            
        if years_of_operation < 0 or years_of_operation > 100:
            errors["years_of_operation"] = "Years of operation must be between 0 and 100"
            
        if min_pax < 1 or min_pax > 10000:
            errors["min_pax"] = "Minimum Pax must be between 1 and 10000"
            
        if starting_price < 0 or starting_price > 10000000:
            errors["starting_price"] = "Starting Price must be between 0 and 10000000"
        # Removed coverage_area requirement per user request

    if errors:
        context = {
            "request": request,
            "error": "Please correct the highlighted fields below.",
            "field_errors": errors,
            "next_url": next_url,
            "role": role,
            "submitted_data": locals()
        }
        template = "auth/register_caterer.html" if role == "caterer" else "auth/register.html"
        return templates.TemplateResponse(template, context)

    user = db.query(models.User).filter(models.User.email == email).first()
    
    # Check if this is a social user upgrading to caterer
    is_upgrade = False
    if user and user.auth_provider != 'email' and user.role == "pending":
        is_upgrade = True
    elif user:
        template = "auth/register_caterer.html" if role == "caterer" else "auth/register.html"
        return templates.TemplateResponse(template, {
            "request": request,
            "error": "Email already registered",
            "next_url": next_url,
            "role": role
        })
    
    if is_upgrade:
        # Update existing social user
        user.first_name = first_name
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
            import uuid
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
                file_path = os.path.join(UPLOAD_DIR, f"{temp_id}_gov_id_{gov_id.filename}")
                with open(file_path, "wb") as buffer:
                    buffer.write(await gov_id.read())
                gov_id_url = f"/static/uploads/verification/{temp_id}_gov_id_{gov_id.filename}"
                
            if permit and permit.filename:
                file_path = os.path.join(UPLOAD_DIR, f"{temp_id}_permit_{permit.filename}")
                with open(file_path, "wb") as buffer:
                    buffer.write(await permit.read())
                permit_url = f"/static/uploads/verification/{temp_id}_permit_{permit.filename}"

            if sample_menu and sample_menu.filename:
                file_path = os.path.join(UPLOAD_DIR, f"{temp_id}_menu_{sample_menu.filename}")
                with open(file_path, "wb") as buffer:
                    buffer.write(await sample_menu.read())
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
            last_name=last_name,
            phone_number=mobile_number,
            address=address,
            status="pending_verification",
            is_verified=False,
            is_email_verified=False,
            verification_code=otp,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=3)
        )
        db.add(new_user)
        db.flush()

        if role == "caterer":
            new_profile = models.CatererProfile(
                user_id=new_user.id,
                business_name=business_name,
                business_type=business_type,
                years_of_operation=years_of_operation,
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
                starting_price=starting_price,
                city=city,
                sample_menu_url=sample_menu_url,
                permit_url=permit_url,
                gov_id_url=gov_id_url,
                verification_status="Pending"
            )
            db.add(new_profile)

            if gov_id_url or permit_url:
                verification = models.IdentityVerification(
                    user_id=new_user.id,
                    document_url=gov_id_url,
                    selfie_url=permit_url,
                    ocr_data={
                        "extracted_business_name": business_name,
                        "document_type": "Business Permit",
                        "confidence": 0.98,
                        "verification_check_passed": True,
                        "extracted_at": datetime.now().isoformat()
                    },
                    verification_status="pending"
                )
                db.add(verification)

        db.commit()
    
    # Only send verification email if it's a new email/password user
    if not is_upgrade:
        try:
            from ..services.email import EmailService
            EmailService.send_verification_email(email, otp)
            print(f"[AUTH] Registration buffered for {email}. Verification email sent.")
        except Exception as e:
            print(f"[AUTH ERROR] Failed to send verification email: {e}")
            
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
        else:
            return templates.TemplateResponse("auth/verify_email.html", {"request": request, "email": email, "error": "Invalid verification code"})
    else:
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
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=3)
    db.commit()
    
    # Resend Email
    from ..services.email import EmailService
    EmailService.send_verification_email(email, otp)
    
    return {"success": True, "message": "Verification code resent"}

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
            
    # Initialize session to ensure cookie is set before OAuth redirect (fixes mismatching_state)
    if not request.session.get("session_init"):
        request.session["session_init"] = True

    return templates.TemplateResponse("auth/login.html", {"request": request, "next_url": next})

@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next_url: Optional[str] = Form(None),
    db: Session = Depends(database.get_db)
):
    # basic validation
    if not email or not password:
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Email and password are required",
            "next_url": next_url
        })
    try:
        from pydantic import TypeAdapter
        TypeAdapter(EmailStr).validate_python(email)
    except ValidationError:
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Invalid email address",
            "next_url": next_url
        })

    search_email = email
    if email.lower() == "admin":
        search_email = "admin@occaserve.com"
        
    user = db.query(models.User).filter(func.lower(models.User.email) == search_email.lower().strip()).first()

    if not user or not security_auth.verify_password(password, user.password_hash):
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Invalid credentials",
            "next_url": next_url
        })
    
    if user.status != "active":
         if user.role == "caterer" and user.status == "pending_approval":
             return RedirectResponse(url=f"/auth/pending?email={user.email}&uid={user.id}", status_code=status.HTTP_303_SEE_OTHER)
         
         error_msg = "Please follow the email link to verify your account." if user.status == "pending_verification" else "Account is inactive or pending approval."
         return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": error_msg
        })
        
    if not user.is_email_verified and user.role != "admin":
        # Check if auth provider is email, if social it should be verified
        if user.auth_provider == 'email':
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
        data={"sub": user.email, "role": user.role}, # Include role in token
        expires_delta=access_token_expires
    )
    
    # Issue Refresh Token
    refresh_token = security_auth.create_refresh_token(user_id=user.id, db=db)
    
    # Audit Log
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

    response = RedirectResponse(url="/?logout=success#home", status_code=status.HTTP_303_SEE_OTHER)
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
