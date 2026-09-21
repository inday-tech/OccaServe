from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
# Trigger reload for DB schema sync
from fastapi.responses import RedirectResponse, JSONResponse, Response
import os
from dotenv import load_dotenv
load_dotenv(override=True)
from fastapi.staticfiles import StaticFiles
from .db.database import engine, Base, get_db, SessionLocal
from .routers import website, auth, admin, bookings, social_auth, caterers, packages, caterer_dashboard, customer_dashboard, verification, kyc, quotations, payments, contact, notifications, chat, caterer_feed, inventory_api, caterer_portfolio, service_bookings, admin_caterer_verification
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

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run one-time DB schema sync on startup to avoid per-request DDL locks."""
    ddl_statements = [
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS customer_name VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS customer_email VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS customer_contact VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS event_name VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS event_type VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS event_time TIME",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS event_end_time TIME",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS venue_address TEXT",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS event_address TEXT",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS id_address TEXT",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS current_address TEXT",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS verification_status VARCHAR DEFAULT 'pending'",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS guest_count INTEGER",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS total_amount FLOAT",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS actual_cost FLOAT DEFAULT 0.0",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS actual_cost_breakdown JSONB",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS total_price FLOAT",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS reservation_fee NUMERIC",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS travel_fee FLOAT DEFAULT 0.0",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS travel_fee_status VARCHAR DEFAULT 'confirmed'",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'pending'",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_status VARCHAR DEFAULT 'pending'",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_method VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS amount_paid FLOAT DEFAULT 0.0",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS preparation_status VARCHAR DEFAULT 'not_started'",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS preparation_date DATE",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS customer_archived BOOLEAN DEFAULT FALSE",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_reference VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_proof_url VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS balance_proof_url VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS dispatch_proof_url VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS paymongo_link_id VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS paymongo_link_url VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payout_id INTEGER",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_verification_data JSONB",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS proof_image_hash VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS ocr_verified BOOLEAN DEFAULT FALSE",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS liveness_verified BOOLEAN DEFAULT FALSE",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS special_requests TEXT",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS caterer_notes TEXT",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS booking_source VARCHAR DEFAULT 'OccaServe'",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS security_deposit_amount FLOAT DEFAULT 0.0",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS security_deposit_status VARCHAR DEFAULT 'unpaid'",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS damage_deduction_amount FLOAT DEFAULT 0.0",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS missing_items_count INTEGER DEFAULT 0",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS release_photo_url VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS return_photo_url VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS damage_proof_url VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS rental_disputed BOOLEAN DEFAULT FALSE",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS commission_calculated BOOLEAN DEFAULT FALSE",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS balance_due_date TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_plan VARCHAR DEFAULT 'downpayment'",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS event_location TEXT",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS terms_accepted_ip VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS is_custom_event BOOLEAN DEFAULT FALSE",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS transaction_type VARCHAR DEFAULT 'contract_track'",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS document_type VARCHAR",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS custom_requirements JSONB",
        "ALTER TABLE ocr_verification ADD COLUMN IF NOT EXISTS full_name VARCHAR",
        "ALTER TABLE ocr_verification ADD COLUMN IF NOT EXISTS birthdate DATE",
        "ALTER TABLE ocr_verification ADD COLUMN IF NOT EXISTS id_address_extracted TEXT",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS permit_status VARCHAR DEFAULT 'Pending'",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS dti_url VARCHAR",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS bir_url VARCHAR",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS mayors_permit_url VARCHAR",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS permit_expiry_date DATE",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS permit_url VARCHAR",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS gov_id_url VARCHAR",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS registration_source VARCHAR DEFAULT 'Website'",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS admin_remarks TEXT",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS starting_price FLOAT DEFAULT 0.0",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS sample_menu_url VARCHAR",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS province_code VARCHAR",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS city_code VARCHAR",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS brgy_code VARCHAR",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS address_details TEXT",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS team_size INTEGER DEFAULT 1",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS min_pax INTEGER DEFAULT 0",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS latitude FLOAT",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS longitude FLOAT",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS primary_color VARCHAR DEFAULT '#FF7B54'",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS secondary_color VARCHAR DEFAULT '#2D4059'",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS accent_color VARCHAR DEFAULT '#FFB17A'",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS highlight_color VARCHAR DEFAULT '#FFE5D9'",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS font_family VARCHAR DEFAULT 'Inter'",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS border_radius INTEGER DEFAULT 12",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS sidebar_mode VARCHAR DEFAULT 'full'",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS show_platform_logo BOOLEAN DEFAULT TRUE",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS max_bookings_per_day INTEGER DEFAULT 1",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS auto_block_enabled BOOLEAN DEFAULT TRUE",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS glass_mode BOOLEAN DEFAULT FALSE",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS sidebar_color VARCHAR DEFAULT '#000000'",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS header_color VARCHAR DEFAULT '#FFFFFF'",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS dashboard_texture VARCHAR DEFAULT 'none'",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS sidebar_decoration VARCHAR DEFAULT 'none'",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS header_decoration VARCHAR DEFAULT 'none'",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS terms_and_conditions TEXT",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS general_terms TEXT",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS rental_policies TEXT",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS cancellation_policy TEXT",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS booking_lead_time INTEGER DEFAULT 7",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS equipment_turnover_hours INTEGER DEFAULT 24",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS accepted_payment_terms JSONB DEFAULT '[100]'",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS default_labor_cost FLOAT DEFAULT 0.0",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS default_utility_cost FLOAT DEFAULT 0.0",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS default_transport_cost FLOAT DEFAULT 0.0",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS default_reservation_type VARCHAR DEFAULT 'fixed'",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS default_reservation_value FLOAT DEFAULT 0.0",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS delivery_fee_type VARCHAR DEFAULT 'area'",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS base_delivery_fee FLOAT DEFAULT 150.0",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS scheduling_rules JSONB",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS notification_preferences JSONB",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS deactivation_reason TEXT",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS deactivated_at TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS outstanding_balance FLOAT DEFAULT 0.0",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS commission_rate FLOAT DEFAULT 10.0",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE booking_contracts ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE",
        # users structured address fields
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS province VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS city_municipality VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS barangay VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS street_address TEXT",
        
        # website_config
        "ALTER TABLE website_config ADD COLUMN IF NOT EXISTS admin_gcash_name VARCHAR",
        "ALTER TABLE website_config ADD COLUMN IF NOT EXISTS admin_gcash_number VARCHAR",
        "ALTER TABLE website_config ADD COLUMN IF NOT EXISTS admin_gcash_qr_url VARCHAR",
        "ALTER TABLE website_config ADD COLUMN IF NOT EXISTS max_file_size_mb INTEGER DEFAULT 5",
        "ALTER TABLE website_config ADD COLUMN IF NOT EXISTS commission_rate FLOAT DEFAULT 10.0",
        "ALTER TABLE website_config ADD COLUMN IF NOT EXISTS commission_fixed_amount FLOAT DEFAULT 20.0",
        "ALTER TABLE website_config ADD COLUMN IF NOT EXISTS maintenance_mode BOOLEAN DEFAULT FALSE",
        "ALTER TABLE website_config ADD COLUMN IF NOT EXISTS maintenance_message TEXT DEFAULT 'OccaServe is currently undergoing scheduled maintenance. We''ll be back online shortly!'",
        "ALTER TABLE website_config ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE",
        
        # catering_packages
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS cost_price FLOAT DEFAULT 0.0",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS cost_breakdown JSONB",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS price_unit VARCHAR DEFAULT 'per_guest'",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS min_guests INTEGER DEFAULT 10",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS max_guests INTEGER",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS image_url VARCHAR",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS gallery_images JSONB",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS service_type VARCHAR DEFAULT 'General'",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS pricing_mode VARCHAR DEFAULT 'per_pax'",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS price_per_head FLOAT",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS internal_cost_per_pax FLOAT DEFAULT 0.0",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS base_pax INTEGER DEFAULT 50",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS labor_cost FLOAT DEFAULT 0.0",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS utility_cost FLOAT DEFAULT 0.0",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS equipment_cost FLOAT DEFAULT 0.0",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS transportation_cost FLOAT DEFAULT 0.0",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS miscellaneous_cost FLOAT DEFAULT 0.0",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS ingredient_total_cost FLOAT DEFAULT 0.0",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS min_contract_amount FLOAT",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS additional_guest_price FLOAT",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS service_duration INTEGER DEFAULT 4",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS overtime_fee FLOAT DEFAULT 0.0",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS location_coverage VARCHAR",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS reservation_fee_type VARCHAR DEFAULT 'fixed'",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS reservation_fee_value FLOAT DEFAULT 0.0",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS booking_lead_time INTEGER DEFAULT 7",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS inclusions JSONB",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS policies JSONB",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS selection_rules JSONB",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'active'",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS markup_type VARCHAR DEFAULT 'percentage'",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS markup_value FLOAT DEFAULT 0.0",

        # menu_items
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'available'",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS price FLOAT DEFAULT 0.0",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS cost_price FLOAT DEFAULT 0.0",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS pricing_unit VARCHAR DEFAULT 'per_pax'",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS min_order_qty INTEGER DEFAULT 1",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS usage_type VARCHAR DEFAULT 'both'",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS available_for_package BOOLEAN DEFAULT TRUE",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS available_for_order BOOLEAN DEFAULT TRUE",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS pricing_type VARCHAR DEFAULT 'fixed'",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS cost_breakdown JSONB",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS dietary_tags VARCHAR[]",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS allergen_info VARCHAR[]",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS serving_size VARCHAR",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS serving_style VARCHAR",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS is_addon BOOLEAN DEFAULT FALSE",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS addon_price FLOAT DEFAULT 0.0",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS max_stock_quantity INTEGER",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN DEFAULT FALSE",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS is_combo BOOLEAN DEFAULT FALSE",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS max_choices INTEGER DEFAULT 0",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS combo_options JSONB",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS average_rating FLOAT DEFAULT 0.0",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS review_count INTEGER DEFAULT 0",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS upgrade_fee FLOAT DEFAULT 0.0",

        # portfolios
        "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS booking_id INTEGER",
        "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS highlights VARCHAR",
        "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS location VARCHAR",
        "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS event_date DATE",
        "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS visibility VARCHAR DEFAULT 'Public'",
        "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE",
        "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE",
        "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP",

        # portfolio_images
        "ALTER TABLE portfolio_images ADD COLUMN IF NOT EXISTS is_cover BOOLEAN DEFAULT FALSE",

        # reviews
        "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS food_quality_rating INTEGER",
        "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS service_quality_rating INTEGER",
        "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS timeliness_rating INTEGER",
        "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS recommend BOOLEAN DEFAULT FALSE",
        "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS was_punctual BOOLEAN DEFAULT FALSE",
        "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS is_highlighted BOOLEAN DEFAULT FALSE",
        "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS caterer_reply TEXT",
        "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS is_helpful BOOLEAN DEFAULT FALSE",
        "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE",

        # identity_verifications
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS booking_id INTEGER",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS verification_type VARCHAR DEFAULT 'government_id'",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS document_url VARCHAR",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS document_back_url VARCHAR",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS id_type VARCHAR",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS id_number VARCHAR",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS id_expiry_date DATE",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS selfie_url VARCHAR",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS selfie_2_url VARCHAR",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS selfie_3_url VARCHAR",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS ocr_data JSONB",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS ocr_status VARCHAR",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS liveness_status VARCHAR",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS match_status VARCHAR",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS verification_status VARCHAR DEFAULT 'PROCESSING'",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS failure_reason TEXT",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS verification_valid_until TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS review_status VARCHAR",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS reviewed_by INTEGER",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS fraud_score INTEGER DEFAULT 0",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS match_score FLOAT DEFAULT 0.0",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS face_detected BOOLEAN DEFAULT FALSE",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS id_detected BOOLEAN DEFAULT FALSE",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS ip_address VARCHAR",
        "ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS device_info JSONB",
        "ALTER TABLE identity_verifications DROP CONSTRAINT IF EXISTS identity_verifications_user_id_key",

        # equipment
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS equipment_type VARCHAR DEFAULT 'Equipment'",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS category VARCHAR",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS image_url VARCHAR",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS available_qty INTEGER DEFAULT 1",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS cost_value FLOAT DEFAULT 0.0",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS rental_price FLOAT DEFAULT 0.0",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS unit_type VARCHAR DEFAULT 'piece'",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'available'",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN DEFAULT FALSE",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS security_deposit_pct FLOAT DEFAULT 20.0",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS maintenance_buffer_hours INTEGER DEFAULT 12",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS requires_kyc BOOLEAN DEFAULT FALSE",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS usage_type VARCHAR DEFAULT 'both'",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS is_addon BOOLEAN DEFAULT FALSE",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS addon_price FLOAT DEFAULT 0.0",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS average_rating FLOAT DEFAULT 0.0",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS review_count INTEGER DEFAULT 0",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS details_json JSONB",

        # services
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS category VARCHAR",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS image_url VARCHAR",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS base_duration_hours INTEGER DEFAULT 3",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS cost FLOAT DEFAULT 0.0",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS selling_price FLOAT DEFAULT 0.0",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS unit_type VARCHAR DEFAULT 'per_event'",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS max_available INTEGER DEFAULT 1",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'available'",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN DEFAULT FALSE",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS usage_type VARCHAR DEFAULT 'both'",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS is_addon BOOLEAN DEFAULT FALSE",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS addon_price FLOAT DEFAULT 0.0",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS capacity_type VARCHAR DEFAULT 'unit_based'",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS staff_to_pax_ratio INTEGER DEFAULT 0",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS min_staff_required INTEGER DEFAULT 1",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS allow_freelancers BOOLEAN DEFAULT FALSE",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS buffer_time_hours INTEGER DEFAULT 0",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS requires_agreement BOOLEAN DEFAULT FALSE",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS downpayment_percentage INTEGER DEFAULT 50",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS minimum_hours INTEGER DEFAULT 1",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS average_rating FLOAT DEFAULT 0.0",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS review_count INTEGER DEFAULT 0",
        "ALTER TABLE services ADD COLUMN IF NOT EXISTS details_json JSONB",

        # caterer_gallery
        "ALTER TABLE caterer_gallery ADD COLUMN IF NOT EXISTS media_type VARCHAR DEFAULT 'image'",
        "ALTER TABLE caterer_gallery ADD COLUMN IF NOT EXISTS caption VARCHAR",
        "ALTER TABLE caterer_gallery ADD COLUMN IF NOT EXISTS display_order INTEGER DEFAULT 0",
        "ALTER TABLE caterer_gallery ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE",

        # platform_feedback
        "ALTER TABLE platform_feedback ADD COLUMN IF NOT EXISTS attachment_base64 TEXT",
        "ALTER TABLE platform_feedback ADD COLUMN IF NOT EXISTS role VARCHAR",
        "ALTER TABLE platform_feedback ADD COLUMN IF NOT EXISTS is_highlighted BOOLEAN DEFAULT FALSE",
        "ALTER TABLE platform_feedback ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE",

        # booking_history
        "ALTER TABLE booking_history ADD COLUMN IF NOT EXISTS entry_type VARCHAR DEFAULT 'system_change'",
        "ALTER TABLE booking_history ADD COLUMN IF NOT EXISTS communication_channel VARCHAR",

        # booking_menu_items
        "ALTER TABLE booking_menu_items ADD COLUMN IF NOT EXISTS custom_name VARCHAR",
        "ALTER TABLE booking_menu_items ADD COLUMN IF NOT EXISTS equipment_id INTEGER",
        "ALTER TABLE booking_menu_items ADD COLUMN IF NOT EXISTS service_id INTEGER",
        "ALTER TABLE booking_menu_items ADD COLUMN IF NOT EXISTS is_add_on BOOLEAN DEFAULT FALSE",
        "ALTER TABLE booking_menu_items ADD COLUMN IF NOT EXISTS choices JSONB",

        # booking_contracts
        "ALTER TABLE booking_contracts ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE booking_contracts ADD COLUMN IF NOT EXISTS contract_history JSONB",

        # billing_invoices
        "ALTER TABLE billing_invoices ADD COLUMN IF NOT EXISTS booking_id INTEGER REFERENCES bookings(id)",
        "ALTER TABLE billing_invoices ADD COLUMN IF NOT EXISTS commission_rate FLOAT DEFAULT 0.10",
        "ALTER TABLE billing_invoices ADD COLUMN IF NOT EXISTS billing_period VARCHAR",
        "ALTER TABLE billing_invoices ADD COLUMN IF NOT EXISTS amount FLOAT DEFAULT 0.0",
        "ALTER TABLE billing_invoices ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'pending'",
        "ALTER TABLE billing_invoices ADD COLUMN IF NOT EXISTS due_date DATE",
        "ALTER TABLE billing_invoices ADD COLUMN IF NOT EXISTS payment_proof_url VARCHAR",
        "ALTER TABLE billing_invoices ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP",

        # business_expenses
        "ALTER TABLE business_expenses ADD COLUMN IF NOT EXISTS expense_category VARCHAR",
        "ALTER TABLE business_expenses ADD COLUMN IF NOT EXISTS description VARCHAR",
        "ALTER TABLE business_expenses ADD COLUMN IF NOT EXISTS amount FLOAT DEFAULT 0.0",
        "ALTER TABLE business_expenses ADD COLUMN IF NOT EXISTS date_incurred DATE",
        "ALTER TABLE business_expenses ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP",

        # booking_payment_records
        """
        CREATE TABLE IF NOT EXISTS booking_payment_records (
            id SERIAL PRIMARY KEY,
            booking_id INTEGER REFERENCES bookings(id) ON DELETE CASCADE,
            amount FLOAT NOT NULL,
            payment_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            payment_method VARCHAR,
            payment_type VARCHAR,
            reference_notes TEXT,
            recorded_by VARCHAR
        )
        """
    ]

    try:
        from .db.database import engine
        from .db import models
        models.Base.metadata.create_all(bind=engine)
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            for sql in ddl_statements:
                try:
                    conn.execute(text(sql))
                except Exception as stmt_err:
                    pass
            
            # Post-sync updates
            post_updates = [
                "UPDATE caterer_profiles SET is_verified = TRUE WHERE verification_status = 'Verified'",
                "UPDATE users SET is_verified = TRUE WHERE id IN (SELECT user_id FROM caterer_profiles WHERE verification_status = 'Verified')",
                "UPDATE caterer_profiles SET account_status = 'Active' WHERE account_status = 'Approved'"
            ]
            for upd in post_updates:
                try:
                    conn.execute(text(upd))
                except Exception as upd_err:
                    pass
        print("[STARTUP] Schema sync completed successfully.")
    except Exception as e:
        print(f"[STARTUP] Schema sync connection error (non-fatal): {e}")

    yield  # App runs here

app = FastAPI(lifespan=lifespan)


import traceback
from fastapi.responses import PlainTextResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = f"Unhandled Exception: {type(exc).__name__}: {str(exc)}\n\n"
    error_msg += "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    print(error_msg)
    
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or \
              "application/json" in request.headers.get("Accept", "")
    if is_ajax:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "success": False,
                "message": f"Server error: {type(exc).__name__}: {str(exc)}"
            }
        )
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
    except Exception as e:
        print(f"[MAINTENANCE CHECK ERROR] Non-fatal config query error: {e}")
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
app.include_router(admin_caterer_verification.router)
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
app.include_router(service_bookings.router)

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


# TEST CLOUDINARY UPLOAD ENDPOINT
from fastapi import UploadFile, File
from .services.storage import upload_image_with_metadata

@app.post("/upload-test")
async def test_cloudinary_upload(file: UploadFile = File(...), folder: str = "gallery"):
    """Test endpoint for Cloudinary integration validation."""
    content = await file.read()
    res = upload_image_with_metadata(content, folder=folder)
    if not res:
        raise HTTPException(status_code=500, detail="Cloudinary upload failed. Please verify CLOUDINARY credentials.")
    return {
        "public_id": res.get("public_id"),
        "secure_url": res.get("url")
    }


@app.post("/api/admin/migrate-base64-to-cloudinary")
async def trigger_base64_migration():
    """Trigger script to convert all legacy base64 images in PostgreSQL into Cloudinary URLs."""
    from migrate_base64_to_cloudinary import run_migration
    import threading
    thread = threading.Thread(target=run_migration)
    thread.start()
    return {"status": "started", "message": "Base64 to Cloudinary migration started in background thread."}


