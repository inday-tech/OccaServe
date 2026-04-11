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

# Register Facebook
oauth.register(
    name='facebook',
    client_id=settings.FACEBOOK_CLIENT_ID,
    client_secret=settings.FACEBOOK_CLIENT_SECRET,
    access_token_url='https://graph.facebook.com/oauth/access_token',
    access_token_params=None,
    authorize_url='https://www.facebook.com/dialog/oauth',
    authorize_params=None,
    api_base_url='https://graph.facebook.com/',
    client_kwargs={'scope': 'email public_profile'},
)

# Register Google
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
    authorize_params={'access_type': 'offline'},
)

# Register Instagram
oauth.register(
    name='instagram',
    client_id=settings.INSTAGRAM_CLIENT_ID,
    client_secret=settings.INSTAGRAM_CLIENT_SECRET,
    authorize_url='https://api.instagram.com/oauth/authorize',
    access_token_url='https://api.instagram.com/oauth/access_token',
    api_base_url='https://graph.instagram.com/',
    client_kwargs={'scope': 'user_profile,user_media'},
)

@router.get("/login/{provider}")
async def social_login(request: Request, provider: str):
    """
    Redirects the user to the social provider's login page.
    Real OAuth flow using Authlib.
    """
    # Standardize host and SITE_URL for comparison
    current_host = str(request.base_url.hostname)
    site_url_obj = settings.SITE_URL.split("//")[-1].split("/")[0].split(":")[0]

    # If the user is on a different host than configured, redirect to the correct one
    # This prevents 'mismatching_state' errors due to session cookie host isolation
    is_localhost_variant = current_host in ["localhost", "127.0.0.1"]
    configured_is_localhost = site_url_obj in ["localhost", "127.0.0.1"]

    if current_host != site_url_obj and not (is_localhost_variant and configured_is_localhost):
        target_base = settings.SITE_URL.rstrip('/')
        full_target_url = f"{target_base}{request.url.path}"
        if request.query_params:
            full_target_url += f"?{request.query_params}"
        
        print(f"[OAUTH] DOMAIN MISMATCH: Redirecting {current_host} -> {site_url_obj} to preserve session")
        return RedirectResponse(url=full_target_url)

    client = oauth.create_client(provider)
    
    # Simple and robust config check
    configs = {
        'facebook': settings.FACEBOOK_CLIENT_ID,
        'google': settings.GOOGLE_CLIENT_ID,
        'instagram': settings.INSTAGRAM_CLIENT_ID
    }
    config_id = configs.get(provider)

    if not client or not config_id:
        print(f"DEBUG ERROR: Missing config for {provider}. Config ID: '{config_id}'")
        return RedirectResponse(url=f"/auth/login?error=config_missing&provider={provider}")
        
    # Construct redirect_uri using SITE_URL from config
    site_url = settings.SITE_URL.rstrip('/')
    
    # --- PROTOCOL AWARENESS ---
    # Detect if we are behind an HTTPS proxy (like Ngrok)
    is_secure = request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https"
    
    # Force HTTPS ONLY if we are genuinely behind a secure proxy or SITE_URL is https
    if is_secure or settings.SITE_URL.startswith("https://"):
        if site_url.startswith("http://"):
            site_url = site_url.replace("http://", "https://")
            print(f"[OAUTH] Using HTTPS for {provider} callback (Proxy/Config detected)")
    elif provider in ['facebook', 'instagram']:
        print(f"[OAUTH WARNING] {provider} usually requires HTTPS. If login fails, please use ngrok.")

    redirect_uri = f"{site_url}/auth/callback/{provider}"
    
    print(f"[OAUTH] Initiating {provider} login. Redirect URI: {redirect_uri}")
    
    try:
        return await client.authorize_redirect(request, redirect_uri)
    except Exception as e:
        print(f"[OAUTH ERROR] Failed to initiate redirect for {provider}: {e}")
        return RedirectResponse(url=f"/auth/login?error=oauth_failed&details=init_failed")

    print(f"[OAUTH] Received callback for {provider}. Processing token exchange...")
    
    try:
        # Authlib automatically retrieves state and redirect_uri from the session
        client = oauth.create_client(provider)
        if not client:
            raise HTTPException(status_code=400, detail=f"OAuthConfig for {provider} not found")
            
        token = await client.authorize_access_token(request)
        print(f"[OAUTH] Token exchange successful for {provider}")
    except OAuthError as error:
        print(f"[OAUTH ERROR] Callback failed for {provider}: {error.error} - {error.description}")
        # Check for specific 'mismatching_state' which is usually a domain/cookie issue
        error_msg = str(error.description if hasattr(error, 'description') else error)
        return RedirectResponse(url=f"/auth/login?error=oauth_failed&details={error_msg}")
    except Exception as e:
        print(f"[OAUTH CRITICAL ERROR] Unexpected failure during {provider} callback: {e}")
        return RedirectResponse(url=f"/auth/login?error=oauth_failed&details=system_error")

    # --- 1. HANDLE EXTERNAL INFO ---
    user_info = None
    email = None
    social_id = None
    name = None
    picture = None
    
    if provider == 'facebook':
        # Request specific fields from Facebook for higher accuracy and larger picture
        resp = await oauth.facebook.get('me?fields=id,name,email,first_name,last_name,picture.type(large)', token=token)
        user_info = resp.json()
        social_id = user_info.get('id')
        email = user_info.get('email')
        name = user_info.get('name')
        first_name = user_info.get('first_name')
        last_name = user_info.get('last_name')
        picture = user_info.get('picture', {}).get('data', {}).get('url')
        
    elif provider == 'google':
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

    elif provider == 'instagram':
        resp = await oauth.instagram.get('me?fields=id,username', token=token)
        user_info = resp.json()
        social_id = user_info.get('id')
        name = user_info.get('username')
        # Instagram API doesn't always provide email; use a placeholder
        email = f"{social_id}@instagram.user" 
        picture = None

    # --- 2. DATABASE SYNCHRONIZATION ---
    user = None
    
    # Priority A: Check by Social ID (Most reliable for social login)
    if provider == 'facebook':
        user = db.query(models.User).filter(models.User.facebook_id == social_id).first()
    elif provider == 'google':
        user = db.query(models.User).filter(models.User.google_id == social_id).first()
    elif provider == 'instagram':
        user = db.query(models.User).filter(models.User.instagram_id == social_id).first()

    # Priority B: Check by Email if Social ID check failed
    if not user and email:
        user = db.query(models.User).filter(models.User.email == email).first()
    
    # --- 3. AUTO-CREATE OR UPDATE ACCOUNT ---
    if not user:
        # Create New User
        # If email is missing, we use a placeholder that the user must update in onboarding
        final_email = email if email else f"fb_{social_id}@no-email.com"
        
        user = models.User(
            email=final_email,
            password_hash=auth.get_password_hash(os.urandom(16).hex()), # Unusable random password
            first_name=first_name if first_name else (name.split(" ")[0] if name else "User"),
            last_name=last_name if last_name else (name.split(" ")[-1] if name and " " in name else ""),
            role="customer", # Default role as requested
            status="active",
            is_email_verified=True if email else False, # Verified if we got it from provider
            auth_provider=provider,
            profile_image_url=picture
        )
        if provider == 'facebook': user.facebook_id = social_id
        if provider == 'google': user.google_id = social_id
        if provider == 'instagram': user.instagram_id = social_id
        
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Handle existing account: Link social ID if missing
        updated = False
        if provider == 'facebook' and not user.facebook_id:
            user.facebook_id = social_id
            updated = True
        elif provider == 'google' and not user.google_id:
            user.google_id = social_id
            updated = True
        elif provider == 'instagram' and not user.instagram_id:
            user.instagram_id = social_id
            updated = True
        
        if updated:
            db.commit()

    # Create Final Session Token
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    # --- 4. DESTINATION CALCULATION ---
    # For social users, we enforce the 'customer' role as requested
    if user.role == "pending" or user.role is None:
        user.role = "customer"
        db.commit()
    
    # User wants to skip onboarding and go straight to dashboard for social login
    redirect_url = utils.get_dashboard_url(user.role)

    # Redirect user to the calculated destination
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response
