import os
from fastapi import APIRouter, Request, HTTPException, status, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from authlib.integrations.starlette_client import OAuth, OAuthError
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt, JWTError
from ..core.templates import templates
from ..db import database, models
from ..core import security as auth, utils
from ..core.config import settings

# Templates configuration

# Initialize Router
# NOTE: To use this REAL router, you must include it in main.py instead of the mock 'oauth' router.
router = APIRouter(prefix="/auth", tags=["social-auth"])

# Initialize Authlib
oauth = OAuth()

# Register Google
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
    authorize_params={'access_type': 'offline'},
)

@router.get("/login/{provider}")
async def social_login(request: Request, provider: str):
    """
    Redirects the user to the social provider's login page.
    """
    if provider != 'google':
        return RedirectResponse(url=f"/auth/login?error=invalid_provider")

    # Standardize host and SITE_URL for comparison
    current_host = str(request.base_url.hostname)
    site_url_obj = settings.SITE_URL.split("//")[-1].split("/")[0].split(":")[0]

    # If the user is on a different host than configured, redirect to the correct one
    is_localhost_variant = current_host in ["localhost", "127.0.0.1"]
    configured_is_localhost = site_url_obj in ["localhost", "127.0.0.1"]

    if current_host != site_url_obj and not (is_localhost_variant and configured_is_localhost):
        target_base = settings.SITE_URL.rstrip('/')
        full_target_url = f"{target_base}{request.url.path}"
        if request.query_params:
            full_target_url += f"?{request.query_params}"
        
        print(f"[OAUTH] DOMAIN MISMATCH: Redirecting {current_host} -> {site_url_obj}")
        return RedirectResponse(url=full_target_url)

    client = oauth.create_client(provider)
    if not client or not settings.GOOGLE_CLIENT_ID:
        print(f"DEBUG ERROR: Missing config for {provider}")
        return RedirectResponse(url=f"/auth/login?error=config_missing&provider={provider}")
        
    # Construct redirect_uri using SITE_URL from config
    site_url = settings.SITE_URL.rstrip('/')
    is_secure = request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https"
    
    if is_secure or settings.SITE_URL.startswith("https://"):
        if site_url.startswith("http://"):
            site_url = site_url.replace("http://", "https://")

    redirect_uri = f"{site_url}/auth/callback/{provider}"
    print(f"[OAUTH] Initiating {provider} login. Redirect URI: {redirect_uri}")
    
    try:
        return await client.authorize_redirect(request, redirect_uri)
    except Exception as e:
        print(f"[OAUTH ERROR] Failed to initiate redirect: {e}")
        return RedirectResponse(url=f"/auth/login?error=oauth_failed&details=init_failed")

@router.get("/callback/{provider}")
async def social_callback(request: Request, provider: str, db: Session = Depends(database.get_db)):
    """
    Handles the callback from the social provider.
    """
    if provider != 'google':
        return RedirectResponse(url=f"/auth/login?error=invalid_provider")

    print(f"[OAUTH] Received callback for {provider}. Processing token exchange...")
    
    try:
        client = oauth.create_client(provider)
        token = await client.authorize_access_token(request)
        print(f"[OAUTH] Token exchange successful for {provider}")
    except OAuthError as error:
        print(f"[OAUTH ERROR] Callback failed for {provider}: {error.error}")
        return RedirectResponse(url=f"/auth/login?error=oauth_failed&details={error.error}")
    except Exception as e:
        print(f"[OAUTH CRITICAL ERROR] Unexpected failure during {provider} callback: {e}")
        return RedirectResponse(url=f"/auth/login?error=oauth_failed&details=system_error")

    # --- 1. HANDLE EXTERNAL INFO ---
    user_info = token.get('userinfo')
    if not user_info:
        resp = await oauth.google.get('https://openidconnect.googleapis.com/v1/userinfo', token=token)
        user_info = resp.json()
    
    social_id = user_info.get('sub')
    email = user_info.get('email')
    name = user_info.get('name')
    first_name = user_info.get('given_name')
    last_name = user_info.get('family_name')
    picture = user_info.get('picture')

    # Request higher resolution if it's a standard Google profile photo
    if picture and "googleusercontent.com" in picture and "=s96-c" in picture:
        picture = picture.replace("=s96-c", "=s400-c")

    # --- 2. DATABASE SYNCHRONIZATION ---
    # Priority A: Check by Social ID
    user = db.query(models.User).filter(models.User.google_id == social_id).first()

    # Priority B: Check by Email if Social ID check failed
    if not user and email:
        user = db.query(models.User).filter(models.User.email == email).first()
    
    # --- 3. AUTO-CREATE OR UPDATE ACCOUNT ---
    if not user:
        # Create New User
        user = models.User(
            email=email,
            password_hash=auth.get_password_hash(os.urandom(16).hex()),
            first_name=first_name if first_name else (name.split(" ")[0] if name else "User"),
            last_name=last_name if last_name else (name.split(" ")[-1] if name and " " in name else ""),
            role="customer",
            status="active",
            is_email_verified=True,
            auth_provider=provider,
            profile_image_url=picture,
            google_id=social_id
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Link social ID if missing
        if not user.google_id:
            user.google_id = social_id
            db.commit()

    # Create Final Session Token
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    # User goes straight to dashboard
    redirect_url = utils.get_dashboard_url(user.role)

    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

