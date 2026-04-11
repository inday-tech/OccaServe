from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from ..core.templates import templates
from sqlalchemy.orm import Session
from ..db import database, models
from ..core import security as auth, utils
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["oauth"])

@router.get("/{provider}/login", response_class=HTMLResponse)
def login_via_provider(request: Request, provider: str):
    if provider != 'facebook':
        raise HTTPException(status_code=404, detail="Provider not supported")
    
    # Simulate Redirect to Provider
    return templates.TemplateResponse("auth/mock_oauth.html", {
        "request": request, 
        "provider": provider,
        "provider_name": "Facebook"
    })

@router.get("/callback/{provider}")
def oauth_callback(request: Request, provider: str, code: str, db: Session = Depends(database.get_db)):
    if provider != 'facebook':
         # We removed Instagram support
         raise HTTPException(status_code=400, detail="Only Facebook is supported")
    
    # Simulation: We act as if we got this data from Facebook
    mock_email = "naomi.caragay@example.com"
    mock_social_id = "fb_1020304050"
    mock_first_name = "Naomi"
    mock_last_name = "Caragay"
    
    # Check if user exists
    user = db.query(models.User).filter(models.User.email == mock_email).first()
    
    if not user:
        # Create new user
        password = utils.get_random_string(16)
        hashed_password = auth.get_password_hash(password)
        
        user = models.User(
            email=mock_email,
            password_hash=hashed_password,
            first_name=mock_first_name,
            last_name=mock_last_name,
            role="customer",
            status="active",
            is_email_verified=True, # Trust Social Login
            auth_provider=provider,
            facebook_id=mock_social_id
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update existing
        if not user.facebook_id:
            user.facebook_id = mock_social_id
            user.auth_provider = provider
            user.is_email_verified = True
            db.commit()

    # Create Session
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    # Redirect to Dashboard
    redirect_url = utils.get_dashboard_url(user.role)
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response
