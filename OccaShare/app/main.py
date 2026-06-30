from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
# Trigger reload for DB schema sync
from fastapi.responses import RedirectResponse, JSONResponse, Response
import os
from dotenv import load_dotenv
load_dotenv(override=True)
from fastapi.staticfiles import StaticFiles
from .db.database import engine, Base, get_db
from .routers import website, auth, admin, bookings, social_auth, caterers, packages, caterer_dashboard, customer_dashboard, verification, kyc, quotations, payments, contact, notifications, chat, caterer_feed, inventory_api, caterer_portfolio
from .db import models
from sqlalchemy.orm import Session
from .services.realtime import manager
from sqlalchemy import text

# MIGRATION REMOVED FROM STARTUP: Running database migrations inside worker processes
# causes deadlocks and Gunicorn timeouts when deploying with multiple workers.
# Migrations are already run during the build/release phase (releaseCommand in railway.json).
#
# try:
#     from scripts.master_migration import master_migration
#     print("[STARTUP] Executing master database schema migrations...")
#     master_migration()
# except Exception as e:
#     print(f"[STARTUP ERROR] Master database schema migrations failed: {e}")
from starlette.middleware.sessions import SessionMiddleware
from .core.config import settings
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from .core.security import SECRET_KEY, ALGORITHM
from jose import jwt, JWTError

app = FastAPI()

import traceback
from fastapi.responses import PlainTextResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = f"Unhandled Exception: {type(exc).__name__}: {str(exc)}\n\n"
    error_msg += "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    print(error_msg)
    return PlainTextResponse(content=error_msg, status_code=500)

# Removed conflicting root route to allow website.router landing page to load
# @app.get("/", include_in_schema=False)
# async def root():
#     return {"status": "running", "message": "OccaServe API is operational"}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    # Attempt to redirect to a static favicon if it exists to silence the default 404
    return Response(status_code=204)

@app.middleware("http")
async def add_website_config(request: Request, call_next):
    # This middleware approach is one way, but context_processors are better for Jinja2
    return await call_next(request)

# Better: Global Template Context Processor
from .db.database import SessionLocal
@app.middleware("http")
async def maintenance_middleware(request: Request, call_next):
    # 1. Skip check for Static Files and Admin routes
    path = request.url.path
    if path.startswith("/static") or path.startswith("/admin") or path.startswith("/api/admin") or path == "/favicon.ico":
        return await call_next(request)

    # 2. Fetch Config (Optimized: Check if it's in request state if we had it, but for now fetch)
    db = SessionLocal()
    try:
        config = db.query(models.WebsiteConfig).first()
        if config and config.maintenance_mode:
            # 3. Check if current user is an admin
            token = request.cookies.get("access_token")
            is_admin = False
            if token:
                if token.startswith("Bearer "): token = token.split(" ")[1]
                try:
                    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                    email: str = payload.get("sub")
                    user = db.query(models.User).filter(models.User.email == email).first()
                    if user and user.role == "admin":
                        is_admin = True
                except: pass
            
            if not is_admin:
                # Return Maintenance Page (HTML) or JSON if API
                if "text/html" in request.headers.get("accept", ""):
                    from .core.templates import templates
                    return templates.TemplateResponse("maintenance.html", {
                        "request": request,
                        "message": config.maintenance_message,
                        "config": config
                    }, status_code=503)
                else:
                    return JSONResponse(
                        status_code=503,
                        content={"success": False, "message": config.maintenance_message}
                    )
    finally:
        db.close()

    return await call_next(request)

@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    request.state.db = SessionLocal()
    response = await call_next(request)
    request.state.db.close()
    return response

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    
    # Allow browser to cache static assets (images, CSS, JS, fonts)
    if path.startswith("/static"):
        response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
        return response
    
    # Prevent browser from caching dashboard HTML pages (Back/Forward button security)
    dashboard_routes = ["/caterer", "/admin", "/customer", "/kyc", "/verification", "/payments"]
    if any(path.startswith(route) for route in dashboard_routes):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

def get_website_config():
    """Returns a plain dict snapshot of website config to avoid SQLAlchemy DetachedInstanceError."""
    db = SessionLocal()
    try:
        config = db.query(models.WebsiteConfig).first()
        if not config:
            config = models.WebsiteConfig()
            db.add(config)
            db.commit()
            db.refresh(config)
        
        # Convert to a plain dict while session is still open
        # This prevents DetachedInstanceError when templates access attributes
        # after the session is closed
        return {
            "id": config.id,
            "site_name": config.site_name,
            "support_email": config.support_email,
            "seo_description": config.seo_description,
            "logo_url": config.logo_url,
            "favicon_url": config.favicon_url,
            "facebook_link": config.facebook_link,
            "instagram_link": config.instagram_link,
            "twitter_link": config.twitter_link,
            "commission_rate": config.commission_rate,
            "commission_fixed_amount": config.commission_fixed_amount,
            "max_file_size_mb": config.max_file_size_mb,
            "maintenance_mode": config.maintenance_mode,
            "maintenance_message": config.maintenance_message
        }
    except Exception as e:
        print(f"[STARTUP ERROR] Website config fail: {e}")
        return None
    finally:
        db.close()


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    # Check if the error is 401 Unauthorized
    if exc.status_code == 401:
        accept_header = request.headers.get("accept", "")
        # If it's a browser requesting HTML, redirect to home and open login modal
        if "text/html" in accept_header:
            return RedirectResponse(url="/?auth_modal=login&reason=session_expired", status_code=303)
        
        # Otherwise, for APIs/fetch requests, return standard JSON
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None)
        )
    
    # For all other HTTPExceptions
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None)
    )

# Add SessionMiddleware - Using lax and secure if behind HTTPS proxy
app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SECRET_KEY,
    same_site="lax",
    https_only=False, # Better for local development and Ngrok-as-a-Proxy
    max_age=3600 * 24 * 7 # 1 week
)

# Add ProxyHeadersMiddleware to handle Ngrok/Proxy headers (X-Forwarded-Proto)
# Adding this AFTER SessionMiddleware ensures it's at the TOP of the stack (runs first on request)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# DEBUG MIDDLEWARE: Log all incoming requests to find the 404 culprit
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # print(f"[DEBUG LOG] Request: {request.method} {request.url}")
    response = await call_next(request)
    # print(f"[DEBUG LOG] Response: {response.status_code} for {request.url.path}")
    return response

@app.get("/test-extract")
async def test_extract():
    import glob
    import time
    from app.services.verification import verification_service
    upload_dir = "app/static/uploads/verification"
    files = glob.glob(os.path.join(upload_dir, "temp_ocr_*.enc"))
    if not files:
        return {"error": "No temp_ocr files found in verification upload directory."}
    # Sort by modification time to get the latest file
    latest_file = max(files, key=os.path.getmtime)
    filename = os.path.basename(latest_file)
    id_url = f"/api/bookings/kyc/view/{filename}"
    
    try:
        with open("ocr_debug.log", "a", encoding="utf-8") as f:
            f.write(f"\n--- test_extract ROUTE TRIGGERED at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            f.write(f"Testing file: {latest_file}\n")
            f.write(f"GEMINI_API_KEY: {os.getenv('GEMINI_API_KEY')[:20] if os.getenv('GEMINI_API_KEY') else 'None'}...\n")
    except Exception as e:
        print(f"Error writing to ocr_debug.log: {e}")
        
    result = await verification_service.extract_id_data(id_url, "PhilSys / PhilID")
    return {
        "cwd": os.getcwd(),
        "file_tested": latest_file,
        "result": result
    }

from .routers.social_auth import router as social_router
app.include_router(social_router)
app.include_router(website.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(bookings.router)
app.include_router(caterers.router)
app.include_router(packages.router)

app.include_router(caterer_dashboard.router)
app.include_router(customer_dashboard.router)
app.include_router(verification.router)
app.include_router(contact.router)
app.include_router(quotations.router)
app.include_router(kyc.router)
app.include_router(payments.router)
app.include_router(notifications.router)
app.include_router(chat.router)
app.include_router(caterer_feed.router)
app.include_router(inventory_api.router)
app.include_router(caterer_portfolio.router)

# --- WebSocket Implementation ---

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    # Try to authenticate the user from cookies
    user_id = None
    role = None
    
    token = websocket.cookies.get("access_token")
    if token:
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if email:
                db = SessionLocal()
                user = db.query(models.User).filter(models.User.email == email).first()
                if user:
                    user_id = user.id
                    role = user.role
                db.close()
        except JWTError:
            pass

    await manager.connect(client_id, websocket, user_id=user_id, role=role)
    try:
        while True:
            # We just need to keep the connection alive
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        await manager.disconnect(client_id)
