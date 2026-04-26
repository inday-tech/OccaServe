import os
from fastapi import APIRouter, Request, HTTPException, status, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from authlib.integrations.starlette_client import OAuth, OAuthError
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt, JWTError
from ..core.templates import templates
from ..db import database, models
from ..core import security as auth_security, utils
from ..core.config import settings

# Initialize Router
router = APIRouter(prefix="/social", tags=["social-auth"])

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
    if provider != 'google':
        return RedirectResponse(url=f"/?auth_modal=login&error=invalid_provider")

    site_url = settings.SITE_URL.rstrip('/')
    if site_url.startswith("http:"):
        site_url = site_url.replace("http:", "https:")
    elif not site_url.startswith("https:"):
        site_url = f"https://{site_url}"

    redirect_uri = f"{site_url}/social/callback/{provider}"
    print(f"[OAUTH DEBUG] Initiating login. Redirect URI: {redirect_uri}")
    
    client = oauth.create_client(provider)
    if not client or not settings.GOOGLE_CLIENT_ID:
        return RedirectResponse(url=f"/?auth_modal=login&error=config_missing")
        
    try:
        return await client.authorize_redirect(request, redirect_uri)
    except Exception as e:
        print(f"[OAUTH ERROR] Redirect failed: {e}")
        return RedirectResponse(url=f"/?auth_modal=login&error=oauth_failed")

@router.get("/callback/{provider}")
async def social_callback(request: Request, provider: str, db: Session = Depends(database.get_db)):
    print(f"[OAUTH DEBUG] Callback received for provider: {provider}")
    if provider != 'google':
        return RedirectResponse(url=f"/?auth_modal=login&error=invalid_provider")

    try:
        client = oauth.create_client(provider)
        token = await client.authorize_access_token(request)
    except Exception as e:
        print(f"[OAUTH ERROR] Token exchange failed: {e}")
        return RedirectResponse(url=f"/?auth_modal=login&error=oauth_failed")

    user_info = token.get('userinfo')
    if not user_info:
        resp = await oauth.google.get('https://openidconnect.googleapis.com/v1/userinfo', token=token)
        user_info = resp.json()
    
    social_id = user_info.get('sub')
    email = user_info.get('email')
    
    # Check existing user
    user = db.query(models.User).filter(models.User.google_id == social_id).first()
    if not user and email:
        user = db.query(models.User).filter(models.User.email == email).first()
    
    if not user:
        # Create new user
        user = models.User(
            email=email,
            password_hash=auth_security.get_password_hash(os.urandom(16).hex()),
            first_name=user_info.get('given_name', user_info.get('name', 'User').split(" ")[0]),
            last_name=user_info.get('family_name', user_info.get('name', '').split(" ")[-1] if " " in user_info.get('name', '') else ""),
            role="customer",
            status="active",
            is_email_verified=True,
            auth_provider=provider,
            profile_image_url=user_info.get('picture'),
            google_id=social_id
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if not user.google_id:
            user.google_id = social_id
            db.commit()

    # Log them in
    access_token_expires = timedelta(minutes=auth_security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_security.create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url=utils.get_dashboard_url(user.role), status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response
