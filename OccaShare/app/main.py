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

# Create tables (will be handled by releaseCommand on Railway, but kept here as fallback)
# Base.metadata.create_all(bind=engine)

from starlette.middleware.sessions import SessionMiddleware
from .core.config import settings
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

app = FastAPI()

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

# DEBUG MIDDLEWARE: Log all incoming requests to find the 404 culprit
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"[DEBUG LOG] Request: {request.method} {request.url}")
    response = await call_next(request)
    print(f"[DEBUG LOG] Response: {response.status_code} for {request.url.path}")
    return response

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
