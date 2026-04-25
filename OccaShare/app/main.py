from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
# Trigger reload for DB schema sync
from fastapi.responses import RedirectResponse, JSONResponse, Response
import os
from fastapi.staticfiles import StaticFiles
from .db.database import engine, Base, get_db
from .routers import website, auth, admin, bookings, social_auth, caterers, packages, caterer_dashboard, customer_dashboard, verification, kyc, quotations, payments, contact, notifications, chat, caterer_feed
from .db import models
from sqlalchemy.orm import Session
from .services.realtime import manager
from sqlalchemy import text

# Create tables
Base.metadata.create_all(bind=engine)

# Manual Migration for newly added columns
print("Running manual migrations...")
try:
    with engine.begin() as conn:
        print("Checking bookings table...")
        cols = [
            ("event_end_time", "TIME"),
            ("venue_province", "VARCHAR"),
            ("venue_city", "VARCHAR"),
            ("venue_barangay", "VARCHAR"),
            ("total_price", "FLOAT"),
            ("balance_due_date", "TIMESTAMP WITH TIME ZONE"),
            ("event_location", "TEXT"),
            ("is_archived", "BOOLEAN DEFAULT FALSE"),
            ("actual_cost", "FLOAT DEFAULT 0.0"),
            ("balance_proof_url", "VARCHAR"),
            ("reservation_fee", "DECIMAL"),
            ("expires_at", "TIMESTAMP WITH TIME ZONE"),
            ("payout_id", "INTEGER"),
            ("payment_plan", "VARCHAR DEFAULT 'downpayment'"),
            ("ocr_verified", "BOOLEAN DEFAULT FALSE"),
            ("liveness_verified", "BOOLEAN DEFAULT FALSE"),
            ("paymongo_link_id", "VARCHAR"),
            ("paymongo_link_url", "VARCHAR"),
            ("payment_verification_data", "JSONB"),
            ("proof_image_hash", "VARCHAR")
        ]
        for col_name, col_type in cols:
            try:
                # PostgreSQL supports IF NOT EXISTS for ADD COLUMN
                conn.execute(text(f"ALTER TABLE bookings ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception as e:
                print(f"  Warning: Could not add column '{col_name}' to 'bookings': {e}")
                
        print("Checking reviews table...")
        review_cols = [
            ("recommend", "BOOLEAN DEFAULT FALSE"),
            ("was_punctual", "BOOLEAN DEFAULT FALSE"),
            ("is_highlighted", "BOOLEAN DEFAULT FALSE"),
            ("caterer_reply", "TEXT"),
            ("is_helpful", "BOOLEAN DEFAULT FALSE")
        ]
        for col_name, col_type in review_cols:
            try:
                conn.execute(text(f"ALTER TABLE reviews ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception as e:
                print(f"  Warning: Could not add column '{col_name}' to 'reviews': {e}")
                
        print("Checking users table...")
        user_cols = [
            ("is_kyc_complete", "BOOLEAN DEFAULT FALSE"),
            ("kyc_attempts", "INTEGER DEFAULT 0"),
            ("must_change_password", "BOOLEAN DEFAULT FALSE")
        ]
        for col_name, col_type in user_cols:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception as e:
                print(f"  Warning: Could not add column '{col_name}' to 'users': {e}")
                
        print("Checking caterer_profiles table...")
        caterer_cols = [
            ("is_verified", "BOOLEAN DEFAULT FALSE"),
            ("primary_color", "VARCHAR DEFAULT '#2D3748'"),
            ("secondary_color", "VARCHAR DEFAULT '#4A5568'"),
            ("accent_color", "VARCHAR DEFAULT '#48BB78'"),
            ("highlight_color", "VARCHAR DEFAULT '#48BB78'"),
            ("font_family", "VARCHAR DEFAULT 'Inter'"),
            ("border_radius", "INTEGER DEFAULT 12"),
            ("sidebar_mode", "VARCHAR DEFAULT 'full'"),
            ("show_platform_logo", "BOOLEAN DEFAULT TRUE")
        ]
        for col_name, col_type in caterer_cols:
            try:
                conn.execute(text(f"ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception as e:
                print(f"  Warning: Could not add column '{col_name}' to 'caterer_profiles': {e}")
                
        print("Creating social_posts table if not exists...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS social_posts (
                    id SERIAL PRIMARY KEY,
                    caterer_id INTEGER REFERENCES caterer_profiles(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    image_url VARCHAR(255),
                    post_type VARCHAR(50) DEFAULT 'general',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))
        except Exception as e:
            print(f"  Warning: Could not create 'social_posts' table: {e}")
                
        print("Checking menu_items table...")
        menu_cols = [
            ("is_hidden", "BOOLEAN DEFAULT FALSE"),
            ("is_archived", "BOOLEAN DEFAULT FALSE"),
            ("image_url", "VARCHAR"),
            ("addon_price", "FLOAT DEFAULT 0.0"),
            ("is_addon", "BOOLEAN DEFAULT FALSE"),
            ("serving_size", "VARCHAR"),
            ("dietary_tags", "VARCHAR[]"),
            ("allergen_info", "VARCHAR[]")
        ]
        for col_name, col_type in menu_cols:
            try:
                conn.execute(text(f"ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception as e:
                print(f"  Warning: Could not add column '{col_name}' to 'menu_items': {e}")

        print("Checking catering_packages table...")
        package_cols = [
            ("status", "VARCHAR DEFAULT 'active'"),
            ("is_featured", "BOOLEAN DEFAULT FALSE"),
            ("service_type", "VARCHAR DEFAULT 'General'"),
            ("inclusions", "JSONB"),
            ("policies", "JSONB"),
            ("price_per_head", "FLOAT"),
            ("min_contract_amount", "FLOAT"),
            ("additional_guest_price", "FLOAT"),
            ("service_duration", "INTEGER DEFAULT 4"),
            ("overtime_fee", "FLOAT DEFAULT 0.0"),
            ("location_coverage", "VARCHAR")
        ]
        for col_name, col_type in package_cols:
            try:
                conn.execute(text(f"ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception as e:
                print(f"  Warning: Could not add column '{col_name}' to 'catering_packages': {e}")

        print("Checking caterer_gallery table...")
        gallery_cols = [
            ("is_archived", "BOOLEAN DEFAULT FALSE"),
            ("display_order", "INTEGER DEFAULT 0"),
            ("caption", "VARCHAR"),
            ("media_type", "VARCHAR DEFAULT 'image'")
        ]
        for col_name, col_type in gallery_cols:
            try:
                conn.execute(text(f"ALTER TABLE caterer_gallery ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception as e:
                print(f"  Warning: Could not add column '{col_name}' to 'caterer_gallery': {e}")

        print("Checking website_config table...")
        config_cols = [
            ("commission_rate", "FLOAT DEFAULT 10.0"),
            ("commission_fixed_amount", "FLOAT DEFAULT 20.0"),
            ("max_file_size_mb", "INTEGER DEFAULT 5"),
            ("maintenance_mode", "BOOLEAN DEFAULT FALSE"),
            ("maintenance_message", "TEXT")
        ]
        for col_name, col_type in config_cols:
            try:
                conn.execute(text(f"ALTER TABLE website_config ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception as e:
                print(f"  Warning: Could not add column '{col_name}' to 'website_config': {e}")

        print("Checking payouts table...")
        payout_cols = [
            ("is_archived", "BOOLEAN DEFAULT FALSE"),
            ("notes", "TEXT"),
            ("completed_at", "TIMESTAMP WITH TIME ZONE")
        ]
        for col_name, col_type in payout_cols:
            try:
                conn.execute(text(f"ALTER TABLE payouts ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception as e:
                print(f"  Warning: Could not add column '{col_name}' to 'payouts': {e}")

        print("Checking payout_items table...")
        payout_item_cols = [
            ("status", "VARCHAR DEFAULT 'pending'"),
            ("release_trigger", "VARCHAR DEFAULT 'on_completion'")
        ]
        for col_name, col_type in payout_item_cols:
            try:
                conn.execute(text(f"ALTER TABLE payout_items ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception as e:
                print(f"  Warning: Could not add column '{col_name}' to 'payout_items': {e}")

        print("Checking quotations table...")
        quotation_cols = [
            ("contract_url", "VARCHAR"),
            ("status", "VARCHAR(20) DEFAULT 'draft'"),
            ("caterer_signature", "TEXT"),
            ("customer_signature", "TEXT"),
            ("caterer_signed_at", "TIMESTAMP WITH TIME ZONE"),
            ("customer_signed_at", "TIMESTAMP WITH TIME ZONE")
        ]
        for col_name, col_type in quotation_cols:
            try:
                conn.execute(text(f"ALTER TABLE quotations ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception as e:
                print(f"  Warning: Could not add column '{col_name}' to 'quotations': {e}")

        print("Checking identity_verifications table...")
        id_ver_cols = [
            ("is_archived", "BOOLEAN DEFAULT FALSE"),
            ("fraud_score", "INTEGER DEFAULT 0"),
            ("ip_address", "VARCHAR"),
            ("device_info", "JSONB"),
            ("liveness_status", "VARCHAR"),
            ("verified_at", "TIMESTAMP WITH TIME ZONE")
        ]
        for col_name, col_type in id_ver_cols:
            try:
                conn.execute(text(f"ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception as e:
                print(f"  Warning: Could not add column '{col_name}' to 'identity_verifications': {e}")

        print("Checking users table (additional)...")
        user_add_cols = [
            ("is_archived", "BOOLEAN DEFAULT FALSE")
        ]
        for col_name, col_type in user_add_cols:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception as e:
                print(f"  Warning: Could not add column '{col_name}' to 'users': {e}")
                
    print("Manual migrations section finished.")
except Exception as e:
    print(f"CRITICAL: Manual migration failed: {e}")

from starlette.middleware.sessions import SessionMiddleware

from .core.config import settings
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

app = FastAPI()

@app.get("/", include_in_schema=False)
async def root():
    return {"status": "running", "message": "OccaServe API is operational"}

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
async def db_session_middleware(request: Request, call_next):
    request.state.db = SessionLocal()
    response = await call_next(request)
    request.state.db.close()
    return response

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # Prevent browser from caching dashboard pages to handle Back/Forward button security
    path = request.url.path
    dashboard_routes = ["/caterer", "/admin", "/customer", "/kyc", "/verification", "/payments"]
    if any(path.startswith(route) for route in dashboard_routes):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

def get_website_config():
    db = SessionLocal()
    try:
        config = db.query(models.WebsiteConfig).first()
        if not config:
            config = models.WebsiteConfig()
            db.add(config)
            db.commit()
            db.refresh(config)
        return config
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

app.include_router(website.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(bookings.router)
app.include_router(social_auth.router)
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

from .core.security import SECRET_KEY, ALGORITHM
from jose import jwt, JWTError

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
        manager.disconnect(client_id)
