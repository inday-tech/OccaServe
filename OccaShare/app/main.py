import os
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from .routers import website, auth, admin, bookings, social_auth, caterers, packages, caterer_dashboard, customer_dashboard, verification, kyc, quotations, payments, contact, notifications, chat, caterer_feed
from .db import models, database
from .core.config import settings
from .core.middleware import db_session_middleware, add_website_config, add_security_headers

# Create tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="OccaServe")

# Standard Middlewares (Order is important!)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SECRET_KEY,
    same_site="lax",
    https_only=False,
    max_age=3600 * 24 * 7
)

# Proxy headers handling
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# Custom app middlewares
app.middleware("http")(db_session_middleware)
app.middleware("http")(add_website_config)
app.middleware("http")(add_security_headers)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Routers (Social Auth first for priority)
app.include_router(social_auth.router)
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
