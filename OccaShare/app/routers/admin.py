from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile, BackgroundTasks
from typing import Optional
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from ..core.templates import templates
from sqlalchemy.orm import Session
import os, secrets, string, logging
from ..db import database, models
from ..core import security as auth
from ..core.utils import is_dummy_email, is_dummy_name, is_dummy_phone, is_dummy_address, is_valid_person_name, is_valid_business_name
from ..services.email import EmailService
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote
from sqlalchemy import and_, case, func, String, or_
import json, re, asyncio
from ..services.realtime import manager
from ..services.verification import verification_service
from ..services.commission import (
    get_commission_rate_percent,
    is_pre_deployment_manual_booking,
)
from ..services.payment_service import PaymentService

router = APIRouter(prefix="/admin", tags=["admin"])

# Standard dependency for admin access
admin_only = auth.RoleChecker(["admin"])

logger = logging.getLogger(__name__)
MANILA_TIMEZONE = timezone(timedelta(hours=8), name="PHT")


def _format_manila_timestamp(value, date_format="%b %d, %Y %I:%M:%S %p PHT"):
    if value is None:
        return "N/A"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(MANILA_TIMEZONE).strftime(date_format)


def _search_like_pattern(query: str) -> str:
    escaped_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped_query}%"


def _is_walkin_booking(booking: models.Booking) -> bool:
    source = (booking.booking_source or "").strip().lower()
    customer_email = (booking.customer_email or "").strip().lower()
    requirements = booking.custom_requirements or {}
    return (
        not booking.user_id
        or "walk" in source
        or "internal" in source
        or "manual" in source
        or (customer_email.startswith("walkin_") and customer_email.endswith("@guest.occashare.com"))
        or (isinstance(requirements, dict) and bool(requirements.get("is_walk_in")))
        or bool(booking.user and booking.user.auth_provider == "manual_entry")
    )


def _not_archived(column):
    return or_(column.is_(False), column.is_(None))


def _booking_total_amount(booking) -> float:
    # total_price is the amount consumed by PaymentService; total_amount is
    # the legacy/current booking column fallback. Never use amount_paid here.
    return float(booking.total_price or booking.total_amount or 0.0)


def _tracked_platform_commissions(db: Session) -> float:
    """Sum commission ledger entries once, using invoices before payout items."""
    from sqlalchemy.orm import joinedload

    commission_statuses = ("pending", "processing", "overdue", "paid", "settled")
    invoice_rows = db.query(models.BillingInvoice).options(
        joinedload(models.BillingInvoice.booking)
    ).filter(
        models.BillingInvoice.booking_id.isnot(None),
        func.lower(func.trim(func.coalesce(models.BillingInvoice.status, ""))).in_(commission_statuses),
    ).all()

    invoice_total = 0.0
    invoiced_booking_ids = set()
    for invoice in invoice_rows:
        if invoice.booking and is_pre_deployment_manual_booking(invoice.booking):
            continue
        invoiced_booking_ids.add(invoice.booking_id)
        invoice_total += float(invoice.amount or 0.0)

    payout_rows = db.query(models.PayoutItem).options(
        joinedload(models.PayoutItem.booking)
    ).filter(
        func.lower(func.trim(func.coalesce(models.PayoutItem.status, ""))).in_(("ready", "released")),
    ).all()
    payout_total = 0.0
    for item in payout_rows:
        if item.booking_id in invoiced_booking_ids:
            continue
        if item.booking and is_pre_deployment_manual_booking(item.booking):
            continue
        payout_total += float(item.commission_amount or 0.0)

    return invoice_total + payout_total


def _get_darwin_profile(db: Session):
    return db.query(models.CatererProfile).filter(
        func.lower(func.trim(models.CatererProfile.business_name)) == "darwin's catering services"
    ).first()


@router.get("/api/omni-search")
async def omni_search(
    q: str,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    q = q.strip()[:100]
    if len(q) < 2:
        return {"success": True, "results": []}
    
    q_low = q.lower()
    like_pattern = _search_like_pattern(q)
    results = []
    
    # 1. System Pages (Static Links)
    pages = [
        {"title": "Overview Dashboard", "link": "/admin/dashboard", "tags": ["home", "stats", "index", "analytics"]},
        {"title": "Caterer Partners", "link": "/admin/caterers", "tags": ["vendors", "business", "partners", "verify"]},
        {"title": "Customer Directory", "link": "/admin/customers", "tags": ["users", "clients", "directory"]},
        {"title": "All Bookings", "link": "/admin/bookings", "tags": ["orders", "events", "calendar", "manage"]},
        {"title": "Caterer Applications", "link": "/admin/caterers?status=pending", "tags": ["verification", "approval", "applications"]},
        {"title": "Notifications", "link": "/admin/notifications", "tags": ["alerts", "messages"]},
        {"title": "Commissions", "link": "/admin/commissions", "tags": ["revenue", "payouts", "payments"]},
        {"title": "Reports & Analytics", "link": "/admin/reports", "tags": ["reports", "analytics", "statistics"]},
        {"title": "Site Settings", "link": "/admin/settings", "tags": ["config", "branding", "system"]},
        {"title": "Audit Logs", "link": "/admin/audit-logs", "tags": ["security", "logs", "history"]},
        {"title": "Archives", "link": "/admin/archives", "tags": ["deleted", "trash", "history"]},
    ]
    for p in pages:
        if q_low in p["title"].lower() or any(q_low in t for t in p["tags"]):
            results.append({
                "type": "System Page",
                "title": p["title"],
                "subtitle": "Direct Link",
                "link": p["link"],
                "icon": "fas fa-terminal"
            })

    # 2. Search Caterers
    caterers = db.query(models.CatererProfile).join(
        models.User, models.CatererProfile.user_id == models.User.id
    ).filter(
        models.User.is_archived == False,
        models.CatererProfile.verification_status.in_(["Verified", "Suspended"]),
        or_(
            models.CatererProfile.business_name.ilike(like_pattern, escape="\\"),
            models.CatererProfile.city.ilike(like_pattern, escape="\\"),
            models.CatererProfile.contact_phone.ilike(like_pattern, escape="\\"),
            models.User.first_name.ilike(like_pattern, escape="\\"),
            models.User.last_name.ilike(like_pattern, escape="\\"),
            models.User.email.ilike(like_pattern, escape="\\")
        )
    ).order_by(models.CatererProfile.business_name).limit(11).all()
    for c in caterers[:10]:
        results.append({
            "type": "Caterer", 
            "title": c.business_name, 
            "subtitle": f"{c.city or 'Location not set'} · Status: {c.verification_status}",
            "link": f"/admin/caterers?search={quote(c.business_name or '', safe='')}",
            "icon": "fas fa-utensils"
        })
    if len(caterers) > 10:
        results.append({
            "type": "More Results",
            "title": "View all matching caterers",
            "subtitle": "Open the caterer directory with this search",
            "link": f"/admin/caterers?search={quote(q, safe='')}",
            "icon": "fas fa-list"
        })
    
    # 3. Search Customers
    customers = db.query(models.User).filter(
        models.User.role == "customer",
        models.User.is_archived == False,
        models.User.email.isnot(None),
        func.trim(models.User.email) != "",
        func.coalesce(models.User.auth_provider, "email") != "manual_entry",
        or_(
            models.User.first_name.ilike(like_pattern, escape="\\"),
            models.User.last_name.ilike(like_pattern, escape="\\"),
            models.User.email.ilike(like_pattern, escape="\\"),
            models.User.phone_number.ilike(like_pattern, escape="\\")
        )
    ).order_by(models.User.last_name, models.User.first_name).limit(11).all()
    for u in customers[:10]:
        customer_name = " ".join(filter(None, [u.first_name, u.last_name]))
        results.append({
            "type": "Customer", 
            "title": customer_name or "Customer",
            "subtitle": u.email or u.phone_number or "Customer account",
            "link": f"/admin/customers?search={quote(u.email or customer_name, safe='')}",
            "icon": "fas fa-user"
        })
    if len(customers) > 10:
        results.append({
            "type": "More Results",
            "title": "View all matching customers",
            "subtitle": "Open the customer directory with this search",
            "link": f"/admin/customers?search={quote(q, safe='')}",
            "icon": "fas fa-list"
        })
    
    # 4. Search Bookings
    bookings = db.query(models.Booking).outerjoin(
        models.User, models.Booking.user_id == models.User.id
    ).outerjoin(
        models.CatererProfile, models.Booking.caterer_id == models.CatererProfile.id
    ).outerjoin(
        models.CateringPackage, models.Booking.package_id == models.CateringPackage.id
    ).filter(
        models.Booking.is_archived == False,
        or_(
            func.cast(models.Booking.id, String).ilike(like_pattern, escape="\\"),
            models.User.first_name.ilike(like_pattern, escape="\\"),
            models.User.last_name.ilike(like_pattern, escape="\\"),
            models.User.email.ilike(like_pattern, escape="\\"),
            models.Booking.customer_name.ilike(like_pattern, escape="\\"),
            models.Booking.customer_email.ilike(like_pattern, escape="\\"),
            models.Booking.customer_contact.ilike(like_pattern, escape="\\"),
            models.Booking.event_name.ilike(like_pattern, escape="\\"),
            models.Booking.event_type.ilike(like_pattern, escape="\\"),
            models.CatererProfile.business_name.ilike(like_pattern, escape="\\"),
            models.CateringPackage.name.ilike(like_pattern, escape="\\")
        )
    ).order_by(models.Booking.created_at.desc()).limit(11).all()
    for b in bookings[:10]:
        booking_customer_name = "Walk-in" if _is_walkin_booking(b) else b.customer_name
        if not booking_customer_name and b.user:
            booking_customer_name = " ".join(filter(None, [b.user.first_name, b.user.last_name]))
        results.append({
            "type": "Booking", 
            "title": f"Booking {b.booking_ref}",
            "subtitle": f"{booking_customer_name or 'Customer'} · {(b.status or 'UNKNOWN').upper()}",
            "link": f"/admin/bookings?search={b.id}",
            "icon": "fas fa-calendar-check"
        })
    if len(bookings) > 10:
        results.append({
            "type": "More Results",
            "title": "View all matching bookings",
            "subtitle": "Open the bookings list with this search",
            "link": f"/admin/bookings?search={quote(q, safe='')}",
            "icon": "fas fa-list"
        })
        
    return {"success": True, "results": results}


@router.get("/messages", response_class=HTMLResponse)
async def admin_messages(
    request: Request,
    embedded: bool = False,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only),
):
    unread_messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.receiver_id == user.id,
        models.ChatMessage.is_read == False,
    ).count()
    return templates.TemplateResponse("admin/messages.html", {
        "request": request,
        "user": user,
        "active_page": "messages",
        "unread_messages": unread_messages,
        "embedded": embedded,
    })

@router.get("/notifications", response_class=HTMLResponse)
async def admin_notifications(
    request: Request, 
    page: int = 1,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    per_page = 10
    page = max(1, page)
    
    base_query = db.query(models.Notification).filter(
        models.Notification.user_id == user.id
    )
    
    total_notifications = base_query.count()
    total_pages = (total_notifications + per_page - 1) // per_page if total_notifications > 0 else 1
    
    notifications = base_query.order_by(
        models.Notification.created_at.desc()
    ).offset((page - 1) * per_page).limit(per_page).all()
    
    return templates.TemplateResponse("admin/notifications.html", {
        "request": request,
        "user": user,
        "notifications": notifications,
        "active_page": "notifications",
        "current_page": page,
        "total_pages": total_pages,
        "total_notifications": total_notifications
    })

@router.get("/api/notifications/recent")
async def get_recent_notifications(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    notifs = db.query(models.Notification).filter(
        models.Notification.user_id == user.id
    ).order_by(models.Notification.created_at.desc()).limit(8).all()
    
    return {
        "success": True, 
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "link": n.link,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat()
            } for n in notifs
        ]
    }

@router.post("/api/notifications/mark-all-read")
async def mark_all_read(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    db.query(models.Notification).filter(
        models.Notification.user_id == user.id,
        models.Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"success": True}

@router.get("/api/sidebar-badges")
async def get_sidebar_badges(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    # Caterer Management (No direct action needed by default, badge hidden)
    caterers_count = 0

    # Caterer Verification (Action Needed: pending verifications)
    verifications_count = db.query(models.CatererVerification).filter(
        models.CatererVerification.status == 'PENDING_REVIEW'
    ).count()

    # Customer Management (Action Needed: pending KYC reviews)
    latest_customer_verifications = db.query(
        func.max(models.IdentityVerification.id).label("latest_id")
    ).join(
        models.User,
        models.User.id == models.IdentityVerification.user_id,
    ).filter(
        models.User.role == "customer",
        models.IdentityVerification.verification_type != "business_permit",
    ).group_by(
        models.IdentityVerification.user_id
    ).subquery()
    customers_count = db.query(func.count(models.IdentityVerification.id)).join(
        latest_customer_verifications,
        models.IdentityVerification.id == latest_customer_verifications.c.latest_id,
    ).filter(
        models.IdentityVerification.verification_status == "pending_manual_review"
    ).scalar() or 0

    # All Bookings (Action Needed: disputes or flagged bookings)
    bookings_count = db.query(models.DisputeReport).filter(
        models.DisputeReport.status == 'Open'
    ).count()

    # Reports & Analytics (Action Needed: pending invoices/payouts)
    revenue_count = db.query(models.BillingInvoice).filter(
        models.BillingInvoice.status.in_(('pending', 'processing')),
        models.BillingInvoice.booking_id.is_(None),
        models.BillingInvoice.payment_proof_url.isnot(None),
        models.BillingInvoice.payment_proof_url != ''
    ).count()

    return {
        "success": True,
        "badges": {
            "caterers": caterers_count,
            "caterer_verification": verifications_count,
            "customers": customers_count,
            "bookings": bookings_count,
            "revenue": revenue_count
        }
    }

@router.get("/api/system-health")
async def system_health(db: Session = Depends(database.get_db), user: models.User = Depends(admin_only)):
    # Real DB check
    db_status = "Connected"
    try:
        db.execute(text("SELECT 1"))
    except:
        db_status = "Disconnected"
        
    # Simulated Load Data (since psutil is not in requirements)
    import random
    cpu = random.randint(8, 22)
    mem = random.randint(35, 55)
    disk = random.randint(20, 30)
    
    return {
        "success": True,
        "db_status": db_status,
        "uptime": "99.99%",
        "cpu_usage": cpu,
        "memory_usage": mem,
        "disk_usage": disk,
        "server_time": datetime.now().strftime("%I:%M:%S %p")
    }

@router.get("/disputes", response_class=HTMLResponse)
async def admin_disputes(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    from sqlalchemy.orm import joinedload
    disputes = db.query(models.DisputeReport).options(
        joinedload(models.DisputeReport.reporter),
        joinedload(models.DisputeReport.reported),
        joinedload(models.DisputeReport.booking)
    ).order_by(models.DisputeReport.created_at.desc()).all()

    return templates.TemplateResponse("admin/disputes.html", {
        "request": request,
        "user": user,
        "disputes": disputes,
        "active_page": "disputes"
    })

@router.post("/api/disputes/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: int,
    action: str = Form(...), # 'dismiss' or 'suspend_reported'
    notes: str = Form(...),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    from fastapi.responses import JSONResponse
    dispute = db.query(models.DisputeReport).get(dispute_id)
    if not dispute:
        return JSONResponse(status_code=404, content={"success": False, "message": "Dispute not found"})

    dispute.admin_notes = notes
    dispute.resolved_at = func.now()

    if action == "dismiss":
        dispute.status = "dismissed"
        msg = "Dispute dismissed."
    elif action == "suspend_reported":
        dispute.status = "resolved"
        reported_user = dispute.reported
        if reported_user:
            reported_user.status = "suspended"
            reported_user.status_reason = f"Suspended due to Dispute {dispute.reference_id}: {notes}"
            
            # Log Audit
            audit = models.AuditLog(
                user_id=reported_user.id,
                action="account_suspended",
                new_status="suspended",
                notes=f"Suspended by Admin via Dispute {dispute.reference_id}: {notes}"
            )
            db.add(audit)
        msg = f"Reported user ({reported_user.first_name}) suspended."
    
    db.commit()
    return JSONResponse(content={"success": True, "message": msg})

@router.get("/audit-logs", response_class=HTMLResponse)
async def admin_audit_logs(
    request: Request,
    q: Optional[str] = None,
    category: Optional[str] = None,
    date: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    query = db.query(models.AuditLog)
    q = q.strip()[:100] if q else ""
    
    # Apply Filters
    if q:
        search_pattern = _search_like_pattern(q)
        query = query.outerjoin(models.User, models.AuditLog.user_id == models.User.id)
        query = query.filter(
            or_(
                models.AuditLog.notes.ilike(search_pattern, escape="\\"),
                models.AuditLog.action.ilike(search_pattern, escape="\\"),
                models.AuditLog.ip_address.ilike(search_pattern, escape="\\"),
                models.User.first_name.ilike(search_pattern, escape="\\"),
                models.User.last_name.ilike(search_pattern, escape="\\"),
                models.User.email.ilike(search_pattern, escape="\\"),
            )
        )
    
    if category:
        query = query.filter(models.AuditLog.action == category)
        
    if date:
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
            query = query.filter(func.date(models.AuditLog.timestamp) == target_date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Date filter must use YYYY-MM-DD format.") from exc

    # Pagination Logic
    per_page = 20
    total_count = query.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = min(max(page, 1), total_pages)
    logs = query.order_by(models.AuditLog.timestamp.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    distinct_actions = [row[0] for row in db.query(models.AuditLog.action).distinct().all() if row[0]]

    return templates.TemplateResponse("admin/audit_logs.html", {
        "request": request,
        "user": user,
        "logs": logs,
        "distinct_actions": distinct_actions,
        "active_page": "audit-logs",
        "total_pages": total_pages,
        "current_page": page,
        "total_count": total_count,
        "filters": {"q": q or "", "category": category or "", "date": date or ""},
        "now": datetime.now()
    })

@router.get("/api/audit-logs/export")
async def export_audit_logs(
    q: Optional[str] = None,
    category: Optional[str] = None,
    date: Optional[str] = None,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    import csv
    from io import StringIO
    from fastapi.responses import StreamingResponse

    query = db.query(models.AuditLog)
    q = q.strip()[:100] if q else ""
    if q:
        search_pattern = _search_like_pattern(q)
        query = query.outerjoin(models.User, models.AuditLog.user_id == models.User.id).filter(
            or_(
                models.AuditLog.notes.ilike(search_pattern, escape="\\"),
                models.AuditLog.action.ilike(search_pattern, escape="\\"),
                models.AuditLog.ip_address.ilike(search_pattern, escape="\\"),
                models.User.first_name.ilike(search_pattern, escape="\\"),
                models.User.last_name.ilike(search_pattern, escape="\\"),
                models.User.email.ilike(search_pattern, escape="\\"),
            )
        )
    if category:
        query = query.filter(models.AuditLog.action == category)
    if date:
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Date filter must use YYYY-MM-DD format.") from exc
        query = query.filter(func.date(models.AuditLog.timestamp) == target_date)

    logs = query.order_by(models.AuditLog.timestamp.desc()).all()
    
    def generate():
        data = StringIO()
        writer = csv.writer(data)
        writer.writerow(['Timestamp', 'User', 'Action', 'Old Status', 'New Status', 'IP Address', 'Notes'])
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        for log in logs:
            user_name = f"{log.user.first_name} {log.user.last_name}" if log.user else "System"
            writer.writerow([
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                user_name,
                log.action,
                log.old_status or '',
                log.new_status or '',
                log.ip_address or '',
                log.notes or ''
            ])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    response = StreamingResponse(generate(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=system_audit_logs.csv"
    return response



def _send_caterer_welcome_email(email: str, temp_password: str, business_name: str) -> None:
    """Send the caterer account-created email, logging any failure without raising."""
    print(f"[CATERER EMAIL] Starting to send welcome email to {email}")
    try:
        EmailService.send_caterer_account_created_email(email, temp_password, business_name)
        print(f"[CATERER EMAIL] Successfully sent welcome email to {email}")
    except Exception as exc:
        print(f"[CATERER EMAIL] FAILED to send welcome email to {email}: {exc}")
        logger.error(
            "[admin] Failed to send caterer account-created email to %s (%s): %s",
            email, business_name, exc, exc_info=True
        )

UPLOAD_DIR_SITE = "app/static/uploads/website"
os.makedirs(UPLOAD_DIR_SITE, exist_ok=True)

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):

    # Platform Metrics
    active_user_filter = _not_archived(models.User.is_archived)
    user_count = db.query(models.User).filter(active_user_filter).count()
    customer_count = db.query(models.User).filter(models.User.role == 'customer', active_user_filter).count()
    
    # Caterer Metrics
    total_caterers = db.query(models.CatererProfile).join(models.User).filter(active_user_filter).count()
    pending_caterers = db.query(models.CatererProfile).join(models.User).filter(models.CatererProfile.verification_status.in_(["Pending", "Pending Review"]), active_user_filter).order_by(models.CatererProfile.id.desc()).limit(5).all()
    approved_caterers_count = db.query(models.CatererProfile).join(models.User).filter(models.CatererProfile.verification_status == "Verified", active_user_filter).count()
    approved_caterers = db.query(models.CatererProfile).join(models.User).filter(models.CatererProfile.verification_status == "Verified", active_user_filter).order_by(models.CatererProfile.rating.desc()).limit(5).all()
    rejected_caterers_count = db.query(models.CatererProfile).join(models.User).filter(models.CatererProfile.verification_status == "Rejected", active_user_filter).count()
    
    # Keep dashboard aggregates in SQL; materializing every booking and then
    # making 12 more month queries made this page scale with database history.
    for caterer in pending_caterers:
        caterer.registered_at_display = _format_manila_timestamp(
            caterer.created_at,
            "%b %d, %Y",
        )

    booking_amount = func.coalesce(func.nullif(models.Booking.total_price, 0), models.Booking.total_amount, 0.0)
    normalized_booking_status = func.lower(func.trim(func.coalesce(models.Booking.status, "")))
    excluded_sales_statuses = ['cancelled', 'inquiry', 'negotiating', 'quoted']
    active_booking_filter = _not_archived(models.Booking.is_archived)
    booking_count, total_sales = db.query(
        func.count(models.Booking.id),
        func.coalesce(func.sum(case(
            (~normalized_booking_status.in_(excluded_sales_statuses), booking_amount),
            else_=0.0,
        )), 0.0),
    ).filter(active_booking_filter).one()
    booking_count = int(booking_count or 0)
    total_sales = float(total_sales or 0.0)
    
    # Dynamic commission check 
    config = db.query(models.WebsiteConfig).first()
    commission_rate_percent = get_commission_rate_percent(config)
    commission_rate = commission_rate_percent / 100.0
    platform_earnings = _tracked_platform_commissions(db)

    # --- Analytics Chart Data (Last 6 Months) ---
    chart_data = {"months": [], "sales": [], "earnings": [], "bookings": [], "new_users": []}
    now = datetime.now(MANILA_TIMEZONE)
    current_month = datetime(now.year, now.month, 1, tzinfo=MANILA_TIMEZONE)
    month_starts = []
    for months_back in range(5, -1, -1):
        month_index = current_month.year * 12 + current_month.month - 1 - months_back
        month_starts.append(datetime(month_index // 12, month_index % 12 + 1, 1, tzinfo=MANILA_TIMEZONE))
    next_month_index = current_month.year * 12 + current_month.month
    month_range_end = datetime(next_month_index // 12, next_month_index % 12 + 1, 1, tzinfo=MANILA_TIMEZONE)
    month_bucket = func.date_trunc('month', func.timezone("+08:00", models.Booking.created_at))
    monthly_bookings = db.query(
        month_bucket.label('month'),
        func.count(models.Booking.id).label('booking_count'),
        func.coalesce(func.sum(case(
            (~normalized_booking_status.in_(excluded_sales_statuses), booking_amount), else_=0.0
        )), 0.0).label('sales'),
        func.coalesce(func.sum(case(
            (func.lower(func.trim(func.coalesce(models.Booking.payment_status, ""))) == 'paid', booking_amount), else_=0.0
        )), 0.0).label('paid_sales'),
    ).filter(
        models.Booking.created_at >= month_starts[0],
        models.Booking.created_at < month_range_end,
        active_booking_filter,
    ).group_by(month_bucket).all()
    monthly_bookings_by_key = {(row.month.year, row.month.month): row for row in monthly_bookings}

    user_month_bucket = func.date_trunc('month', func.timezone("+08:00", models.User.created_at))
    monthly_users = db.query(
        user_month_bucket.label('month'),
        func.count(models.User.id).label('user_count'),
    ).filter(
        models.User.created_at >= month_starts[0],
        models.User.created_at < month_range_end,
        active_user_filter,
    ).group_by(user_month_bucket).all()
    monthly_users_by_key = {(row.month.year, row.month.month): row.user_count for row in monthly_users}

    for first_day in month_starts:
        key = (first_day.year, first_day.month)
        booking_row = monthly_bookings_by_key.get(key)
        sales = float(booking_row.sales or 0.0) if booking_row else 0.0
        paid_sales = float(booking_row.paid_sales or 0.0) if booking_row else 0.0
        chart_data["months"].append(first_day.strftime("%b"))
        chart_data["sales"].append(sales)
        chart_data["earnings"].append(paid_sales * commission_rate)
        chart_data["bookings"].append(int(booking_row.booking_count or 0) if booking_row else 0)
        chart_data["new_users"].append(int(monthly_users_by_key.get(key, 0) or 0))

    # --- Extra Stats for Analytics Cards ---
    avg_rating_result = db.query(func.avg(models.Review.rating)).filter(_not_archived(models.Review.is_archived)).scalar()
    avg_rating = round(float(avg_rating_result), 1) if avg_rating_result else 0.0
    total_reviews = db.query(models.Review).filter(_not_archived(models.Review.is_archived)).count()

    booking_status_rows = db.query(
        normalized_booking_status.label("normalized_status"),
        func.count(models.Booking.id),
    ).filter(
        active_booking_filter,
    ).group_by(normalized_booking_status).order_by(normalized_booking_status).all()
    booking_status_chart = {
        "labels": [
            " ".join((status or "unknown").replace("_", " ").split()).title()
            for status, _ in booking_status_rows
        ],
        "values": [int(count or 0) for _, count in booking_status_rows],
    }

    from sqlalchemy.orm import joinedload
    recent_login_logs = db.query(models.AuditLog).options(
        joinedload(models.AuditLog.user)
    ).filter(
        models.AuditLog.action == "login",
    ).order_by(models.AuditLog.timestamp.desc()).limit(8).all()
    recent_system_logs = []
    for log in recent_login_logs:
        logged_user = log.user
        full_name = " ".join(
            part for part in (
                getattr(logged_user, "first_name", None),
                getattr(logged_user, "last_name", None),
            ) if part
        ) if logged_user else ""
        recent_system_logs.append({
            "name": full_name or (logged_user.email if logged_user else "Unknown account"),
            "email": logged_user.email if logged_user else "",
            "role": (logged_user.role or "user").title() if logged_user else "Unknown",
            "ip_address": log.ip_address or "Unavailable",
            "timestamp": _format_manila_timestamp(log.timestamp),
        })

    pending_settlements = db.query(models.Payout).options(
        joinedload(models.Payout.caterer)
    ).filter(
        models.Payout.status == 'pending'
    ).order_by(models.Payout.created_at.desc()).limit(5).all()

    # --- Recent Revenue Audit Yields (Last 10 Paid Bookings) ---
    recent_yields = db.query(models.Booking).options(
        joinedload(models.Booking.caterer)
    ).filter(
        func.lower(func.trim(func.coalesce(models.Booking.payment_status, ""))).in_(['paid', 'fully_paid']),
        ~normalized_booking_status.in_(['cancelled', 'inquiry', 'negotiating', 'quoted'])
    ).order_by(models.Booking.created_at.desc()).limit(10).all()

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": user,
        "metrics": {
            "user_count": user_count,
            "total_caterers": total_caterers,
            "customer_count": customer_count,
            "approved_caterers_count": approved_caterers_count,
            "booking_count": booking_count,
            "total_sales": total_sales,
            "platform_earnings": platform_earnings,
            "commission_rate": round(commission_rate * 100, 1)
        },
        "pending_caterers": pending_caterers,
        "recent_system_logs": recent_system_logs,
        "approved_caterers": approved_caterers,
        "active_page": "dashboard",
        "chart_data": chart_data,
        "recent_notifications": db.query(models.Notification).filter(models.Notification.user_id == user.id).order_by(models.Notification.created_at.desc()).limit(5).all(),
        "avg_rating": avg_rating,
        "total_reviews": total_reviews,
        "booking_status_chart": booking_status_chart,
        "recent_yields": recent_yields,
        "pending_settlements": pending_settlements
    })

@router.get("/caterers", response_class=HTMLResponse)
async def manage_caterers(
    request: Request,
    status: Optional[str] = None,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    # Fetch all non-archived caterers to allow management of all states
    from sqlalchemy.orm import joinedload
    caterers_list = db.query(models.CatererProfile).options(
        joinedload(models.CatererProfile.user).joinedload(models.User.identity_verifications)
    ).join(models.User).filter(
        models.User.is_archived == False
    ).order_by(models.CatererProfile.business_name.asc()).all()
    
    # Enrich with performance metrics
    for c in caterers_list:
        # Calculate performance
        booking_count = db.query(models.Booking).filter(models.Booking.caterer_id == c.id).count()
        c.booking_count = booking_count
        # Average rating is already a field in CatererProfile, but let's ensure it's fresh if needed
        # (Assuming the model updates it automatically on review submission)

    metrics = {
        "total_caterers": db.query(models.CatererProfile).join(models.User).filter(models.User.is_archived == False).count(),
        "pending_caterers_count": db.query(models.CatererProfile).join(models.User).filter(
            func.lower(func.coalesce(models.CatererProfile.verification_status, "")).in_([
                "unverified", "pending", "pending review", "pending_review", "requires revision",
                "revision requested", "resubmission_required",
            ]),
            models.User.is_archived == False,
        ).count(),
        "approved_caterers_count": db.query(models.CatererProfile).join(models.User).filter(
            func.lower(func.coalesce(models.CatererProfile.verification_status, "")) == "verified",
            models.User.is_archived == False,
            func.lower(func.coalesce(models.CatererProfile.account_status, "")) != "suspended",
            func.lower(func.coalesce(models.User.status, "")) != "suspended",
        ).count(),
        "rejected_caterers_count": db.query(models.CatererProfile).join(models.User).filter(models.CatererProfile.verification_status == "Rejected", models.User.is_archived == False).count(),
        "suspended_caterers_count": db.query(models.CatererProfile).join(models.User).filter(
            or_(
                models.CatererProfile.account_status == "Suspended",
                func.lower(models.User.status) == "suspended",
            ),
            models.User.is_archived == False,
        ).count(),
    }
    verified_caterers = [
        caterer for caterer in caterers_list
        if (caterer.verification_status or "").lower() == "verified"
    ]
    unverified_caterers = [
        caterer for caterer in caterers_list
        if (caterer.verification_status or "").lower() != "verified"
    ]
    allowed_filters = {"all", "pending", "verified", "suspended", "unverified", "revision", "rejected"}
    initial_filter = status.lower() if status and status.lower() in allowed_filters else "all"

    return templates.TemplateResponse("admin/caterers.html", {
        "request": request,
        "user": user,
        "caterers": caterers_list,
        "verified_caterers": verified_caterers,
        "unverified_caterers": unverified_caterers,
        "initial_filter": initial_filter,
        "metrics": metrics,
        "active_page": "caterers"
    })

@router.post("/api/caterers/{caterer_id}/suspend")
async def suspend_caterer(
    caterer_id: int,
    reason: str = Form(...),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer: return {"success": False, "message": "Caterer not found"}
    
    caterer.account_status = "Suspended"
    if caterer.user:
        caterer.user.status = "suspended"
        caterer.user.status_reason = reason
        
        # Log Audit
        audit = models.AuditLog(
            user_id=caterer.user_id,
            action="account_suspended",
            new_status="suspended",
            notes=f"Suspended by Admin: {reason}"
        )
        db.add(audit)
        
    db.commit()
    
    
    asyncio.create_task(manager.broadcast({"type": "caterer_update", "caterer_id": caterer_id, "action": "suspend"}))
    return {"success": True, "message": "Partner account suspended."}

@router.post("/api/caterers/{caterer_id}/activate")
async def activate_caterer(
    caterer_id: int,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer: return {"success": False, "message": "Caterer not found"}
    
    caterer.account_status = "Active"
    if caterer.user:
        caterer.user.status = "active"
        caterer.user.status_reason = None
        
        # Log Audit
        audit = models.AuditLog(
            user_id=caterer.user_id,
            action="account_activated",
            new_status="active",
            notes="Activated by Admin"
        )
        db.add(audit)
        
    db.commit()
    
    asyncio.create_task(manager.broadcast({"type": "caterer_update", "caterer_id": caterer_id, "action": "activate"}))
    return {"success": True, "message": "Partner account reactivated."}

@router.post("/api/caterers/{caterer_id}/recover")
async def recover_caterer_account(
    caterer_id: int,
    email: str = Form(...),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    import uuid
    from datetime import datetime, timedelta
    from ..services.email import EmailService
    
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer or not caterer.user:
        return {"success": False, "message": "Caterer account not found."}
        
    user = caterer.user
    
    token = str(uuid.uuid4())
    user.reset_token = token
    user.reset_token_expires = datetime.now() + timedelta(hours=1)
    
    # Log Audit
    audit = models.AuditLog(
        user_id=user.id,
        action="account_recovery_initiated",
        new_status=user.status,
        notes=f"Admin {admin.first_name} triggered account recovery to email: {email}"
    )
    db.add(audit)
    db.commit()
    
    try:
        success = EmailService.send_password_reset_email(email, token)
        if success:
            return {"success": True, "message": "Recovery link sent securely."}
        else:
            return {"success": False, "message": "Failed to send email. SMTP error."}
    except Exception as e:
        return {"success": False, "message": f"Service Error: {str(e)}"}

@router.post("/api/caterers/{caterer_id}/flag")
async def flag_caterer(
    caterer_id: int,
    reason: str = Form(...),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer: return {"success": False, "message": "Caterer not found"}
    
    if caterer.user:
        caterer.user.status = "investigation"
        caterer.user.status_reason = reason
        caterer.verification_status = "Pending"
        caterer.account_status = "RESTRICTED"
        caterer.status = "Unpublished"
        
        # Log Audit
        audit = models.AuditLog(
            user_id=caterer.user_id,
            action="account_flagged",
            new_status="investigation",
            notes=f"Flagged for investigation: {reason}"
        )
        db.add(audit)
        db.commit()
        
    
    asyncio.create_task(manager.broadcast({"type": "caterer_update", "caterer_id": caterer_id, "action": "flag"}))
    return {"success": True, "message": "Partner flagged for compliance review."}

@router.get("/api/caterers-overview")
async def get_caterers_overview(
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    from sqlalchemy.orm import joinedload
    caterers = db.query(models.CatererProfile).options(
        joinedload(models.CatererProfile.user)
    ).join(models.User).filter(
        models.User.is_archived == False,
        models.CatererProfile.verification_status.in_(['Verified', 'Suspended'])
    ).all()
    
    # Enrichment
    enriched = []
    for c in caterers:
        booking_count = db.query(models.Booking).filter(models.Booking.caterer_id == c.id).count()
        enriched.append({
            "id": c.id,
            "business_name": c.business_name,
            "first_name": c.user.first_name if c.user else "N/A",
            "last_name": c.user.last_name if c.user else "",
            "email": c.user.email if c.user else "N/A",
            "contact_phone": c.contact_phone,
            "contact_address": c.contact_address,
            "city": c.city,
            "verification_status": c.verification_status,
            "account_status": c.account_status,
            "rating": float(c.rating or 0),
            "booking_count": booking_count,
            "created_at": c.created_at.strftime('%b %d, %Y') if c.created_at else "TBD",
            "latitude": c.latitude,
            "longitude": c.longitude,
            "user_id": c.user_id,
            "status_reason": c.user.status_reason if c.user else None,
            "investigation_notes": c.user.investigation_notes if c.user else None
        })
        
    metrics = {
        "total_caterers": db.query(models.CatererProfile).join(models.User).filter(models.User.is_archived == False).count(),
        "pending_caterers_count": db.query(models.CatererProfile).join(models.User).filter(
            func.lower(func.coalesce(models.CatererProfile.verification_status, "")).in_([
                "unverified", "pending", "pending review", "pending_review", "requires revision",
                "revision requested", "resubmission_required",
            ]),
            models.User.is_archived == False,
        ).count(),
        "approved_caterers_count": db.query(models.CatererProfile).join(models.User).filter(
            models.CatererProfile.verification_status == "Verified",
            models.User.is_archived == False,
            func.lower(func.coalesce(models.CatererProfile.account_status, "")) != "suspended",
            func.lower(func.coalesce(models.User.status, "")) != "suspended",
        ).count(),
        "rejected_caterers_count": db.query(models.CatererProfile).join(models.User).filter(models.CatererProfile.verification_status == "Rejected", models.User.is_archived == False).count(),
    }
    
    return {"success": True, "caterers": enriched, "metrics": metrics}


@router.get("/commissions", response_class=HTMLResponse)
async def manage_commissions(
    request: Request, 
    invoice_id: Optional[int] = None,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    from sqlalchemy.orm import joinedload

    submitted_statuses = ('pending', 'processing')
    pending_invoices = db.query(models.BillingInvoice).options(
        joinedload(models.BillingInvoice.caterer),
        joinedload(models.BillingInvoice.booking)
    ).filter(
        models.BillingInvoice.status.in_(submitted_statuses),
        models.BillingInvoice.booking_id.is_(None),
        models.BillingInvoice.payment_proof_url.isnot(None),
        models.BillingInvoice.payment_proof_url != ''
    ).order_by(models.BillingInvoice.created_at.desc()).all()

    focus_invoice = None
    if invoice_id is not None:
        focus_invoice = db.query(models.BillingInvoice).options(
            joinedload(models.BillingInvoice.caterer),
            joinedload(models.BillingInvoice.booking),
        ).filter(
            models.BillingInvoice.id == invoice_id,
            models.BillingInvoice.booking_id.is_(None),
            models.BillingInvoice.payment_proof_url.isnot(None),
            models.BillingInvoice.payment_proof_url != '',
        ).first()

    paid_invoices = db.query(models.BillingInvoice).filter(
        models.BillingInvoice.status == 'paid',
        models.BillingInvoice.booking_id.is_(None),
        models.BillingInvoice.payment_proof_url.isnot(None),
        models.BillingInvoice.payment_proof_url != ''
    ).order_by(models.BillingInvoice.created_at.desc()).all()
    recent_paid = paid_invoices[:15]

    rejected_count = db.query(models.BillingInvoice).filter(
        models.BillingInvoice.status == 'rejected',
        models.BillingInvoice.booking_id.is_(None),
        models.BillingInvoice.payment_proof_url.isnot(None),
        models.BillingInvoice.payment_proof_url != ''
    ).count()

    booking_due_rows = db.query(models.BillingInvoice).options(
        joinedload(models.BillingInvoice.booking)
    ).filter(
        models.BillingInvoice.booking_id.isnot(None),
        models.BillingInvoice.status.in_(submitted_statuses)
    ).all()
    batch_booking_totals = {}
    for due_row in booking_due_rows:
        if not due_row.booking:
            continue
        total, count = batch_booking_totals.get(due_row.caterer_id, (0.0, 0))
        batch_booking_totals[due_row.caterer_id] = (
            total + float(due_row.booking.total_amount or due_row.booking.total_price or 0.0),
            count + 1
        )

    current_commission_rate = get_commission_rate_percent(db.query(models.WebsiteConfig).first()) / 100.0
    for invoice in pending_invoices:
        invoice.display_commission_rate = (
            invoice.commission_rate
            if invoice.booking_id is not None and invoice.commission_rate is not None
            else current_commission_rate
        )
        if invoice.booking:
            invoice.display_booking_amount = float(
                invoice.booking.total_amount or invoice.booking.total_price or 0.0
            )
            invoice.display_booking_count = 1
        elif invoice.booking_id is None:
            invoice.display_booking_amount, invoice.display_booking_count = batch_booking_totals.get(
                invoice.caterer_id, (0.0, 0)
            )
        else:
            invoice.display_booking_amount = None
            invoice.display_booking_count = 0

    from datetime import datetime
    from sqlalchemy import extract
    
    now = datetime.utcnow()
    monthly_collections = db.query(models.BillingInvoice).filter(
        models.BillingInvoice.status == 'paid',
        models.BillingInvoice.booking_id.is_(None),
        models.BillingInvoice.payment_proof_url.isnot(None),
        models.BillingInvoice.payment_proof_url != '',
        extract('month', models.BillingInvoice.created_at) == now.month,
        extract('year', models.BillingInvoice.created_at) == now.year
    ).all()
    
    pending_total = float(sum((inv.amount or 0.0) for inv in pending_invoices) or 0.0)
    paid_total = float(sum((inv.amount or 0.0) for inv in paid_invoices) or 0.0)
    monthly_total = float(sum((inv.amount or 0.0) for inv in monthly_collections) or 0.0)

    return templates.TemplateResponse("admin/payouts.html", {
        "request": request,
        "user": user,
        "pending_invoices": pending_invoices,
        "recent_paid": recent_paid,
        "focus_invoice": focus_invoice,
        "pending_total": pending_total,
        "paid_total": paid_total,
        "rejected_count": rejected_count,
        "monthly_total": monthly_total,
        "commission_rate_percent": current_commission_rate * 100.0,
        "active_page": "commissions"
    })

@router.post("/api/invoices/{invoice_id}/approve")
async def approve_invoice(
    invoice_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    invoice = db.query(models.BillingInvoice).get(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.booking_id is not None or invoice.status not in ('pending', 'processing') or not invoice.payment_proof_url:
        raise HTTPException(status_code=409, detail="This invoice has no submitted settlement proof.")
        
    invoice.status = "paid"

    if invoice.booking_id is None and invoice.caterer:
        covered_invoices = db.query(models.BillingInvoice).filter(
            models.BillingInvoice.caterer_id == invoice.caterer_id,
            models.BillingInvoice.booking_id.isnot(None),
            models.BillingInvoice.billing_period == invoice.billing_period,
            models.BillingInvoice.status == 'processing'
        ).all()
        if not covered_invoices and invoice.created_at:
            covered_invoices = db.query(models.BillingInvoice).filter(
                models.BillingInvoice.caterer_id == invoice.caterer_id,
                models.BillingInvoice.booking_id.isnot(None),
                models.BillingInvoice.status.in_(('pending', 'processing', 'overdue')),
                models.BillingInvoice.created_at <= invoice.created_at
            ).all()
        for covered_invoice in covered_invoices:
            covered_invoice.status = 'settled'

        remaining_invoices = db.query(models.BillingInvoice).filter(
            models.BillingInvoice.caterer_id == invoice.caterer_id,
            models.BillingInvoice.booking_id.isnot(None),
            models.BillingInvoice.status.in_(('pending', 'processing', 'overdue'))
        ).all()
        invoice.caterer.outstanding_balance = sum(float(row.amount or 0.0) for row in remaining_invoices)
    
    # Audit Log
    audit = models.AuditLog(
        user_id=user.id,
        action="INVOICE_APPROVED",
        notes=f"Admin {user.first_name} approved settlement for Invoice ID {invoice_id}. Amount: ₱{invoice.amount:,.2f}"
    )
    db.add(audit)
    db.commit()
    
    return RedirectResponse(url="/admin/commissions?success_msg=Invoice+settlement+approved.", status_code=303)

@router.post("/api/invoices/{invoice_id}/reject")
async def reject_invoice(
    invoice_id: int,
    reason: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    invoice = db.query(models.BillingInvoice).get(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.booking_id is not None or invoice.status not in ('pending', 'processing') or not invoice.payment_proof_url:
        raise HTTPException(status_code=409, detail="This invoice has no submitted settlement proof.")
        
    invoice.status = "rejected"
    
    caterer = invoice.caterer
    if caterer:
        if invoice.booking_id is None:
            covered_invoices = db.query(models.BillingInvoice).filter(
                models.BillingInvoice.caterer_id == invoice.caterer_id,
                models.BillingInvoice.booking_id.isnot(None),
                models.BillingInvoice.billing_period == invoice.billing_period,
                models.BillingInvoice.status == 'processing'
            ).all()
            if not covered_invoices and invoice.created_at:
                covered_invoices = db.query(models.BillingInvoice).filter(
                    models.BillingInvoice.caterer_id == invoice.caterer_id,
                    models.BillingInvoice.booking_id.isnot(None),
                    models.BillingInvoice.status.in_(('pending', 'processing', 'overdue')),
                    models.BillingInvoice.created_at <= invoice.created_at
                ).all()
            for covered_invoice in covered_invoices:
                covered_invoice.status = 'pending'
                covered_invoice.payment_proof_url = None

            open_invoices = db.query(models.BillingInvoice).filter(
                models.BillingInvoice.caterer_id == invoice.caterer_id,
                models.BillingInvoice.booking_id.isnot(None),
                models.BillingInvoice.status.in_(('pending', 'processing', 'overdue'))
            ).all()
            caterer.outstanding_balance = sum(float(row.amount or 0.0) for row in open_invoices)
        
    audit = models.AuditLog(
        user_id=user.id,
        action="INVOICE_REJECTED",
        notes=f"Admin {user.first_name} rejected settlement for Invoice ID {invoice_id}. Reason: {reason}"
    )
    db.add(audit)
    db.commit()
    
    return RedirectResponse(url="/admin/commissions?success_msg=Invoice+settlement+rejected.", status_code=303)


@router.get("/settings", response_class=HTMLResponse)
async def website_settings(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    config = db.query(models.WebsiteConfig).first()
    if not config:
        config = models.WebsiteConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
        
    # Fetch recent configuration audit logs
    audit_logs = db.query(models.AuditLog).filter(
        models.AuditLog.action.in_(["PLATFORM_CONFIG_UPDATE", "SECURITY_CREDENTIAL_ROTATION"])
    ).order_by(models.AuditLog.timestamp.desc()).limit(15).all()
        
    return templates.TemplateResponse("admin/settings.html", {
        "request": request,
        "user": user,
        "config": config,
        "audit_logs": audit_logs,
        "active_page": "settings"
    })

@router.post("/settings/update")
async def update_website_settings(
    request: Request,
    fb_link: Optional[str] = Form(None),
    ig_link: Optional[str] = Form(None),
    tw_link: Optional[str] = Form(None),
    commission: Optional[float] = Form(None),
    max_upload: Optional[int] = Form(None),
    maintenance_mode: str = Form("off"),
    maint_msg: str = Form(...),
    admin_gcash_name: Optional[str] = Form(None),
    admin_gcash_number: Optional[str] = Form(None),
    admin_gcash_qr: Optional[UploadFile] = File(None),
    logo: Optional[UploadFile] = File(None),
    favicon: Optional[UploadFile] = File(None),
    hero_label_1: Optional[str] = Form(None),
    hero_label_2: Optional[str] = Form(None),
    hero_label_3: Optional[str] = Form(None),
    hero_label_4: Optional[str] = Form(None),
    hero_label_5: Optional[str] = Form(None),
    hero_bg_1: Optional[UploadFile] = File(None),
    hero_bg_2: Optional[UploadFile] = File(None),
    hero_bg_3: Optional[UploadFile] = File(None),
    hero_bg_4: Optional[UploadFile] = File(None),
    hero_bg_5: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    config = db.query(models.WebsiteConfig).first()
    if not config:
        config = models.WebsiteConfig()
        db.add(config)

    # 🛡️ VALIDATION & SANITATION
    if commission is not None and (commission < 0 or commission > 100):
        return {"success": False, "message": "Commission rate must be between 0% and 100%."}
    
    if max_upload is not None and (max_upload < 1 or max_upload > 100):
        return {"success": False, "message": "Maximum upload file size must be between 1MB and 100MB."}

    # 📝 AUDIT PREPARATION (Capture old values)
    changes = []
    if config.commission_rate != commission: changes.append(f"Commission: {config.commission_rate}% -> {commission}%")
    if config.max_file_size_mb != max_upload: changes.append(f"Max Upload: {config.max_file_size_mb}MB -> {max_upload}MB")
    
    new_maint_mode = True if maintenance_mode == "on" else False
    if config.maintenance_mode != new_maint_mode:
        changes.append(f"Maintenance Mode: {'ON' if new_maint_mode else 'OFF'}")

    # APPLY CHANGES
    config.facebook_link = fb_link
    config.instagram_link = ig_link
    config.twitter_link = tw_link
    if commission is not None:
        config.commission_rate = commission
    if max_upload is not None:
        config.max_file_size_mb = max_upload
    config.maintenance_mode = new_maint_mode
    config.maintenance_message = maint_msg
    if admin_gcash_name is not None:
        config.admin_gcash_name = admin_gcash_name
    if admin_gcash_number is not None:
        config.admin_gcash_number = admin_gcash_number

    import time
    timestamp = int(time.time())

    import base64

    from app.services.storage import upload_file_to_cloudinary

    # Handle Logo Upload
    if logo and logo.filename:
        try:
            logo_content = await logo.read()
            if logo_content:
                c_url = upload_file_to_cloudinary(logo_content, folder="gallery")
                if c_url:
                    config.logo_url = c_url
                    changes.append("Updated Platform Logo")
        except Exception as e:
            pass

    # Handle GCash QR Upload
    if admin_gcash_qr and admin_gcash_qr.filename:
        try:
            qr_content = await admin_gcash_qr.read()
            if qr_content:
                c_url = upload_file_to_cloudinary(qr_content, folder="gallery")
                if c_url:
                    config.admin_gcash_qr_url = c_url
                    changes.append("Updated Admin GCash QR")
        except Exception as e:
            pass

    # Handle Favicon Upload
    if favicon and favicon.filename:
        try:
            fav_content = await favicon.read()
            if fav_content:
                c_url = upload_file_to_cloudinary(fav_content, folder="gallery")
                if c_url:
                    config.favicon_url = c_url
                    changes.append("Updated Browser Favicon")
        except Exception as e:
            pass
            
    if hero_label_1 is not None: config.hero_label_1 = hero_label_1
    if hero_label_2 is not None: config.hero_label_2 = hero_label_2
    if hero_label_3 is not None: config.hero_label_3 = hero_label_3
    if hero_label_4 is not None: config.hero_label_4 = hero_label_4
    if hero_label_5 is not None: config.hero_label_5 = hero_label_5
    
    # Handle Hero Backgrounds
    for i, bg_file in enumerate([hero_bg_1, hero_bg_2, hero_bg_3, hero_bg_4, hero_bg_5], start=1):
        if bg_file and bg_file.filename:
            try:
                bg_content = await bg_file.read()
                if bg_content:
                    c_url = upload_file_to_cloudinary(bg_content, folder="gallery")
                    if c_url:
                        setattr(config, f"hero_bg_{i}", c_url)
                        changes.append(f"Updated Hero Background {i}")
            except Exception as e:
                pass


    # 🕵️ LOG AUDIT
    if changes:
        audit = models.AuditLog(
            user_id=user.id,
            action="PLATFORM_CONFIG_UPDATE",
            notes="; ".join(changes),
            ip_address=request.client.host if request.client else None
        )
        db.add(audit)

    db.commit()
    return {"success": True, "message": "Website configuration synchronized successfully."}

@router.post("/profile/change-password")
async def admin_change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    import re
    if new_password != confirm_password:
        return {"success": False, "message": "New passwords do not match."}
    
    if len(new_password) < 8:
        return {"success": False, "message": "Password must be at least 8 characters long."}
        
    if not re.search(r"[A-Z]", new_password):
        return {"success": False, "message": "Password must contain at least one uppercase letter."}

    if not re.search(r"[a-z]", new_password):
        return {"success": False, "message": "Password must contain at least one lowercase letter."}

    if not re.search(r"[0-9]", new_password):
        return {"success": False, "message": "Password must contain at least one number."}

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_password):
        return {"success": False, "message": "Password must contain at least one special character."}
        
    if not auth.verify_password(current_password, user.password_hash):
        return {"success": False, "message": "Current password is incorrect."}
    
    # Update password
    user.password_hash = auth.get_password_hash(new_password)
    
    # 🕵️ LOG AUDIT
    audit = models.AuditLog(
        user_id=user.id,
        action="SECURITY_CREDENTIAL_ROTATION",
        notes="Admin rotated their own administrative password.",
        ip_address=request.client.host if request.client else None
    )
    db.add(audit)
    
    db.commit()
    
    return {"success": True, "message": "Administrative key rotated successfully."}

@router.post("/api/caterers/{caterer_id}/approve")
async def approve_caterer(
    caterer_id: int,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer: return {"success": False, "message": "Caterer not found"}
    caterer.verification_status = "Verified"
    caterer.account_status = "Active"
    if caterer.status == "Published":
        caterer.status = "Unpublished"
    
    audit = models.AuditLog(user_id=caterer.user_id, action="caterer_approved", notes=f"Admin {admin.first_name} verified caterer account.")
    db.add(audit)
    db.commit()
    return {"success": True, "message": "Caterer successfully verified."}

@router.post("/api/caterers/{caterer_id}/reject")
async def reject_caterer(
    caterer_id: int,
    reason: str = Form(...),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer: return {"success": False, "message": "Caterer not found"}
    caterer.verification_status = "Rejected"
    caterer.account_status = "RESTRICTED"
    caterer.status = "Unpublished"
    
    audit = models.AuditLog(user_id=caterer.user_id, action="caterer_rejected", notes=f"Admin {admin.first_name} rejected caterer application. Reason: {reason}")
    db.add(audit)
    db.commit()
    return {"success": True, "message": "Caterer application rejected."}

@router.post("/api/caterers/{caterer_id}/suspend")
async def suspend_caterer_api(
    caterer_id: int,
    reason: str = Form(...),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer: return {"success": False, "message": "Caterer not found"}
    caterer.account_status = "Suspended"
    caterer.user.status = "suspended"
    
    audit = models.AuditLog(user_id=caterer.user_id, action="caterer_suspended", notes=f"Admin {admin.first_name} suspended caterer. Reason: {reason}")
    db.add(audit)
    db.commit()
    return {"success": True, "message": "Caterer account suspended."}

@router.post("/api/caterers/{caterer_id}/activate")
async def reactivate_caterer_api(
    caterer_id: int,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer: return {"success": False, "message": "Caterer not found"}
    caterer.account_status = "Active"
    caterer.user.status = "active"
    
    audit = models.AuditLog(user_id=caterer.user_id, action="caterer_reactivated", notes=f"Admin {admin.first_name} reactivated caterer account.")
    db.add(audit)
    db.commit()
    return {"success": True, "message": "Caterer account reactivated."}

# --- KYC & Review Management ---
@router.get("/inquiries", response_class=HTMLResponse)
async def list_inquiries(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    all_inquiries = db.query(models.Inquiry).order_by(models.Inquiry.created_at.desc()).all()
    
    # Group by email
    grouped = {}
    for i in all_inquiries:
        if i.email not in grouped:
            grouped[i.email] = {
                "name": i.name,
                "email": i.email,
                "messages": [],
                "latest_date": i.created_at,
                "status": "responded",
                "is_caterer_lead": i.caterer_id is not None,
                "target_caterer": i.caterer.business_name if i.caterer else "General Support"
            }
        
        msg_data = {
            "id": i.id,
            "message": i.message,
            "status": i.status,
            "created_at": i.created_at.strftime("%b %d, %Y %I:%M %p")
        }
        grouped[i.email]["messages"].append(msg_data)
        
        # If any message in thread is 'new', the thread status is 'new'
        if i.status == "new":
            grouped[i.email]["status"] = "new"
    
    # Sort grouped list by latest message date
    senders_list = sorted(grouped.values(), key=lambda x: x["latest_date"], reverse=True)
    
    return templates.TemplateResponse("admin/inquiries.html", {
        "request": request,
        "senders": senders_list,
        "senders_json": json.dumps(senders_list, default=str), # default=str to handle datetime if any
        "active_page": "inquiries",
        "user": user
    })

@router.post("/inquiries/thread/{email}/status")
async def update_thread_status(
    email: str, 
    status: str, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    db.query(models.Inquiry).filter(models.Inquiry.email == email).update({"status": status})
    db.commit()
    return RedirectResponse(url="/admin/inquiries?success_msg=Thread+status+updated", status_code=303)

@router.post("/inquiries/{inquiry_id}/status")
async def update_inquiry_status(
    inquiry_id: int, 
    status: str, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    inquiry = db.query(models.Inquiry).filter(models.Inquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    
    inquiry.status = status
    db.commit()
    return RedirectResponse(url="/admin/inquiries?success_msg=Inquiry+status+updated", status_code=303)

@router.post("/inquiries/{inquiry_id}/delete")
async def delete_inquiry(
    inquiry_id: int, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    inquiry = db.query(models.Inquiry).filter(models.Inquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    
    db.delete(inquiry)
    db.commit()
    return RedirectResponse(url="/admin/inquiries?success_msg=Inquiry+deleted+successfully", status_code=303)


@router.post("/caterers/{caterer_id}/verify")
def verify_caterer(
    caterer_id: int, 
    action: str = Form(...), 
    reason: Optional[str] = Form(None),
    db: Session = Depends(database.get_db), 
    user: models.User = Depends(admin_only)
):
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer:
        raise HTTPException(status_code=404, detail="Caterer not found")
    
    if action == "approve":
        caterer.verification_status = "Verified"
        caterer.is_verified = True
        caterer.account_status = "Active"
        # Explicitly activate the associated user account and clear all barriers
        if caterer.user_id:
            caterer_user = db.query(models.User).get(caterer.user_id)
            if caterer_user:
                caterer_user.status = "active"
                caterer_user.is_email_verified = True
                caterer_user.is_verified = True
    elif action == "reject":
        caterer.verification_status = "Rejected"
        caterer.is_verified = False
        caterer.account_status = "RESTRICTED"
        caterer.status = "Unpublished"
        # Optional: Store rejection reason if we added a field for it, 
        # or send a notification/email to the caterer.
    elif action == "revision":
        caterer.verification_status = "Revision Requested"
        caterer.is_verified = False
        caterer.account_status = "RESTRICTED"
        caterer.status = "Unpublished"
    
    db.commit()
    
    # Real-time update
    asyncio.create_task(manager.broadcast({
        "type": "caterer_update",
        "caterer_id": caterer_id,
        "action": action,
        "status": caterer.verification_status
    }))
    
    return RedirectResponse(url=f"/admin/caterers?success_msg=Caterer+{action}+successfully", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/caterers/{caterer_id}/status")
def toggle_caterer_status(caterer_id: int, db: Session = Depends(database.get_db), user: models.User = Depends(admin_only)):
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer:
        raise HTTPException(status_code=404, detail="Caterer not found")
    
    # Toggle status of the associated user account using direct lookup
    if caterer.user_id:
        caterer_user = db.query(models.User).get(caterer.user_id)
        if caterer_user:
            if caterer_user.status == "active":
                caterer_user.status = "suspended"
            else:
                # Activate and clear barriers if coming from suspended or pending
                caterer_user.status = "active"
                caterer_user.is_email_verified = True
                caterer_user.is_verified = True
    
    db.commit()
    
    # Real-time update
    asyncio.create_task(manager.broadcast({
        "type": "caterer_update",
        "caterer_id": caterer_id,
        "action": "status_toggle",
        "status": caterer_user.status if caterer.user_id else "unknown"
    }))
    
    return RedirectResponse(url="/admin/caterers?success_msg=Caterer+status+updated", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/caterers/{caterer_id}/delete")
def delete_caterer(caterer_id: int, db: Session = Depends(database.get_db), user: models.User = Depends(admin_only)):
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer:
        raise HTTPException(status_code=404, detail="Caterer not found")
        
    user_id = caterer.user_id
    
    # Manually delete related data that doesn't have cascade-delete or might cause issues
    if user_id:
        db.query(models.RefreshToken).filter(models.RefreshToken.user_id == user_id).delete()
        db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == user_id).delete()
        db.query(models.AuditLog).filter(models.AuditLog.user_id == user_id).delete()
        db.query(models.Notification).filter(models.Notification.user_id == user_id).delete()
        db.query(models.VerificationAttempt).filter(models.VerificationAttempt.user_id == user_id).delete()
        db.query(models.Review).filter(models.Review.user_id == user_id).delete()
        db.query(models.Inquiry).filter(models.Inquiry.user_id == user_id).delete()
        db.query(models.OCRVerification).filter(models.OCRVerification.user_id == user_id).delete()
        
    # Delete Caterer specific tables
    # Delete Caterer specific tables (Packages, Menu Items, Bookings, Gallery)
    packages = db.query(models.CateringPackage).filter(models.CateringPackage.caterer_id == caterer_id).all()
    package_ids = [p.id for p in packages]
    if package_ids:
        db.query(models.MenuItem).filter(models.MenuItem.package_id.in_(package_ids)).delete(synchronize_session=False)
    
    db.query(models.CateringPackage).filter(models.CateringPackage.caterer_id == caterer_id).delete(synchronize_session=False)
    db.query(models.CatererGallery).filter(models.CatererGallery.caterer_id == caterer_id).delete(synchronize_session=False)
    
    # Bookings and payouts
    db.query(models.Payout).filter(models.Payout.caterer_id == caterer_id).delete(synchronize_session=False)
    db.query(models.Booking).filter(models.Booking.caterer_id == caterer_id).delete(synchronize_session=False)

    # Finally delete the user and profile
    db.delete(caterer)
    if user_id:
        associated_user = db.query(models.User).get(user_id)
        if associated_user:
            db.delete(associated_user)
            
    db.commit()
    
    # Real-time update
    asyncio.create_task(manager.broadcast({
        "type": "user_archived",
        "user_id": user_id,
        "role": "caterer"
    }))
    
    return RedirectResponse(url="/admin/caterers?success_msg=Caterer+deleted+successfully", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/api/caterers/{caterer_id}/edit")
async def edit_caterer(
    caterer_id: int,
    city: Optional[str] = Form(None),
    coverage_area: Optional[str] = Form(None),
    admin_remarks: Optional[str] = Form(None),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    """Update operational listing fields only. Personal identity (name, email, phone) is not editable here."""
    caterer = db.query(models.CatererProfile).get(caterer_id)
    if not caterer:
         return {"success": False, "message": "Caterer not found."}

    if city is not None:
        caterer.city = city.strip() or None
    if coverage_area is not None:
        caterer.coverage_area = coverage_area.strip() or None
    if admin_remarks is not None:
        caterer.admin_remarks = admin_remarks.strip() or None
    db.commit()

    asyncio.create_task(manager.broadcast({
        "type": "caterer_update",
        "caterer_id": caterer_id,
        "action": "edit"
    }))

    return {"success": True, "message": "Operational details were updated."}


@router.get("/api/caterers/audit-identity")
async def audit_identity(
    email: Optional[str] = None,
    phone: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    middle_name: Optional[str] = None,
    business_name: Optional[str] = None,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    results = {
        "email_taken": False,
        "email_invalid": None,
        "phone_taken": False,
        "name_collision": False,
        "business_name_taken": False
    }
    
    if email:
        clean_email = email.strip().lower()
        from ..core.utils import is_dummy_email
        email_err = is_dummy_email(clean_email)
        if email_err:
            results["email_invalid"] = email_err
        else:
            results["email_taken"] = db.query(models.User).filter(
                func.lower(func.trim(models.User.email)) == clean_email,
                models.User.is_archived == False
            ).first() is not None
        
    if phone:
        # Normalize phone: remove non-numeric characters if any
        phone_clean = ''.join(filter(str.isdigit, phone.strip()))
        results["phone_taken"] = db.query(models.User).filter(
            models.User.phone_number == phone_clean
        ).first() is not None or db.query(models.CatererProfile).filter(
            models.CatererProfile.contact_phone == phone_clean
        ).first() is not None

    if first_name and last_name:
        # Deep Name Normalization Audit
        # Strips extra spaces and ignores case
        fname_clean = first_name.strip().lower()
        lname_clean = last_name.strip().lower()
        mn_clean = middle_name.strip().lower() if middle_name else ""
        
        # Broaden the search to catch partial matches (e.g. if DB has "Andresito" and "b bonifacio jr")
        from sqlalchemy import or_, and_
        q = db.query(models.User).filter(
            models.User.is_archived == False,
            or_(
                # Exact match
                and_(
                    func.lower(func.trim(models.User.first_name)) == fname_clean,
                    func.lower(func.trim(models.User.last_name)) == lname_clean
                ),
                # Fuzzy match for names that might have extra suffixes/initials in the DB
                and_(
                    func.lower(func.trim(models.User.first_name)).contains(fname_clean),
                    func.lower(func.trim(models.User.last_name)).contains(lname_clean)
                ),
                # Check if the DB first_name somehow contains the entire full name
                func.lower(func.trim(models.User.first_name)).contains(f"{fname_clean} {lname_clean}")
            )
        )
        if mn_clean:
            # Check middle_name specifically if provided
            q = q.filter(func.lower(func.trim(models.User.middle_name)).contains(mn_clean))
        
        results["name_collision"] = q.first() is not None

    if business_name:
        biz_clean = business_name.strip().lower()
        results["business_name_taken"] = db.query(models.CatererProfile).filter(
            func.lower(func.trim(models.CatererProfile.business_name)) == biz_clean
        ).first() is not None
            
    return results

@router.post("/caterers/add")
async def add_caterer(
    request: Request,
    background_tasks: BackgroundTasks,
    business_name: str = Form(...),
    email: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    middle_name: str = Form(""),
    phone: str = Form(...),
    province: str = Form(...),
    municipality: str = Form(...),
    barangay: str = Form(...),
    street: str = Form(...),
    event_types: str = Form(...), # JSON String from JS
    cuisine_types: str = Form(...), # JSON String from JS
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    business_name = business_name.strip()
    email = email.strip().lower()
    first_name = first_name.strip()
    middle_name = middle_name.strip()
    last_name = last_name.strip()
    province = province.strip()
    municipality = municipality.strip()
    barangay = barangay.strip()
    street = street.strip()

    phone_digits = re.sub(r"\D", "", phone or "")
    if phone_digits.startswith("63"):
        phone_digits = phone_digits[2:]
    if len(phone_digits) == 10 and phone_digits.startswith("9"):
        phone = "0" + phone_digits
    else:
        phone = phone_digits

    # 1. Server-side Validation (High Fidelity Adjudication)
    errors = {}

    for field_name, field_value in {
        "business_name": business_name,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "phone": phone,
        "province": province,
        "municipality": municipality,
        "barangay": barangay,
        "street": street,
    }.items():
        if not field_value:
            errors[field_name] = "This field is required."

    if latitude is None or longitude is None:
        errors["location"] = "Save a valid business location pin before creating the caterer."
    elif not (-90 <= latitude <= 90 and -180 <= longitude <= 180) or (latitude == 0 and longitude == 0):
        errors["location"] = "The business location coordinates are invalid."

    for field_name, field_value in (("first_name", first_name), ("last_name", last_name)):
        if field_value and is_valid_person_name(field_value):
            errors[field_name] = is_valid_person_name(field_value)
    
    # Email check
    email_err = is_dummy_email(email)
    if email_err:
        errors['email'] = email_err
    else:
        existing_user = db.query(models.User).filter(func.lower(models.User.email) == email).first()
        if existing_user:
            errors['email'] = "This email identity is already registered."

    # Business Name check
    biz_err = is_valid_business_name(business_name)
    if biz_err:
        errors['business_name'] = biz_err
    else:
        existing_profile = db.query(models.CatererProfile).filter(
            func.lower(models.CatererProfile.business_name) == business_name.strip().lower()
        ).first()
        if existing_profile:
            errors['business_name'] = "Business name already exists in our registry."

    # Phone check
    phone_err = is_dummy_phone(phone)
    if phone_err:
        errors['phone'] = phone_err
    else:
        existing_phone = db.query(models.User).filter(models.User.phone_number == phone.strip()).first()
        if existing_phone:
            errors['phone'] = "This mobile number is already linked to another account."

    # Operational Domain Check (Laguna Enforcement)
    if province != "Laguna":
        errors['province'] = "Operational domain must be within the Laguna jurisdiction."

    if errors:
        return {"success": False, "errors": errors, "message": "Identity verification failed."}

    # Process Address
    full_address = f"{street}, Brgy. {barangay}, {municipality}, {province}"
    
    # Process Categories
    try:
        parsed_events = json.loads(event_types)
        parsed_cuisines = json.loads(cuisine_types)
    except json.JSONDecodeError:
        return {
            "success": False,
            "message": "Event and cuisine selections must be valid lists.",
        }
    if (
        not isinstance(parsed_events, list)
        or not parsed_events
        or not all(isinstance(item, str) and item.strip() for item in parsed_events)
        or not isinstance(parsed_cuisines, list)
        or not parsed_cuisines
        or not all(isinstance(item, str) and item.strip() for item in parsed_cuisines)
    ):
        return {
            "success": False,
            "message": "Choose at least one valid event type and cuisine.",
        }


    # Name formatting
    final_first_name = first_name.strip()
    final_middle_name = middle_name.strip()
    final_last_name = last_name.strip()

    # password logic
    alphabet = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(alphabet) for i in range(10))
    hashed_password = auth.get_password_hash(temp_password)

    try:
        # 3. Create User record
        new_user = models.User(
            email=email,
            password_hash=hashed_password,
            role="caterer",
            first_name=final_first_name,
            middle_name=final_middle_name,
            last_name=final_last_name,
            phone_number=phone,
            status="active",
            is_verified=False,
            is_email_verified=True,
            is_kyc_complete=False,
            must_change_password=True
        )
        db.add(new_user)
        db.flush()
        db.refresh(new_user)

        # 4. Create Caterer Profile
        new_profile = models.CatererProfile(
            user_id=new_user.id,
            business_name=business_name,
            contact_phone=phone,
            contact_address=full_address,
            province_code=province,
            city_code=municipality,
            brgy_code=barangay,
            address_details=street,
            city=municipality,
            event_types=parsed_events,
            cuisine_types=parsed_cuisines,
            latitude=latitude,
            longitude=longitude,
            verification_status="Unverified",
            is_verified=False,
            slug=business_name.lower().replace(" ", "-") + f"-{new_user.id}"
        )
        db.add(new_profile)
        db.commit()

        # 5. Send welcome email synchronously to check for SMTP delivery success
        email_sent = False
        try:
            email_sent = EmailService.send_caterer_account_created_email(email, temp_password, business_name)
        except Exception as exc:
            logger.error(f"[admin] Welcome email exception: {exc}")

        # Real-time update
        asyncio.create_task(manager.broadcast({
            "type": "new_signup",
            "role": "caterer",
            "name": business_name
        }))

        if email_sent:
            return {"success": True, "message": "Caterer account created! The credentials have been sent to their email."}
        else:
            return {
                "success": True,
                "email_failed": True,
                "temp_password": temp_password,
                "message": f"Caterer account was created, but the welcome email failed to send (SMTP Authentication failure).<br><br><strong>Temporary Password:</strong> <code style='font-size:1.2rem; color:#f97316; font-weight:bold;'>{temp_password}</code><br><br>Please copy this password and send it to the caterer manually."
            }

    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Error creating account: {str(e)}"}

@router.post("/api/customers/{customer_id}/edit")
async def edit_customer(
    customer_id: int,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    customer = db.query(models.User).filter(
        models.User.id == customer_id,
        models.User.role == "customer"
    ).first()
    if not customer:
        return {"success": False, "message": "Customer not found."}

    # Check email not taken by someone else
    existing = db.query(models.User).filter(
        models.User.email == email.strip().lower(),
        models.User.id != customer_id
    ).first()
    if existing:
        return {"success": False, "message": "This email is already in use by another account."}

    customer.first_name = first_name.strip()
    customer.last_name = last_name.strip()
    customer.email = email.strip().lower()
    if phone:
        customer.phone_number = phone.strip()
    if address:
        customer.address = address.strip()

    db.commit()
    
    # Real-time update
    asyncio.create_task(manager.broadcast({
        "type": "customer_update",
        "customer_id": customer_id,
        "action": "edit"
    }))
    
    return {"success": True, "message": "Customer details updated successfully."}

@router.post("/customers/{customer_id}/status")
def toggle_customer_status(customer_id: int, db: Session = Depends(database.get_db), user: models.User = Depends(admin_only)):
    customer = db.query(models.User).filter(models.User.id == customer_id, models.User.role == "customer").first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    if customer.status == "active":
        customer.status = "suspended"
    else:
        customer.status = "active"
        customer.is_email_verified = True
        customer.is_verified = True
        
    db.commit()
    
    # Real-time update
    asyncio.create_task(manager.broadcast({
        "type": "customer_update",
        "customer_id": customer_id,
        "action": "status_toggle",
        "status": customer.status
    }))
    
    return RedirectResponse(url="/admin/customers?success_msg=Customer+status+updated", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/customers/{customer_id}/delete")
def delete_customer(customer_id: int, db: Session = Depends(database.get_db), user: models.User = Depends(admin_only)):
    # Find the user as a customer only to be safe
    customer = db.query(models.User).filter(models.User.id == customer_id, models.User.role == "customer").first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Manually delete related data that doesn't have cascade-delete or might cause issues
    db.query(models.RefreshToken).filter(models.RefreshToken.user_id == customer_id).delete()
    db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == customer_id).delete()
    db.query(models.AuditLog).filter(models.AuditLog.user_id == customer_id).delete()
    db.query(models.Notification).filter(models.Notification.user_id == customer_id).delete()
    db.query(models.VerificationAttempt).filter(models.VerificationAttempt.user_id == customer_id).delete()
    db.query(models.Review).filter(models.Review.user_id == customer_id).delete()
    db.query(models.Inquiry).filter(models.Inquiry.user_id == customer_id).delete()
    db.query(models.OCRVerification).filter(models.OCRVerification.user_id == customer_id).delete()
    
    # Finally delete the user
    db.delete(customer)
    db.commit()
    
    # Real-time update
    asyncio.create_task(manager.broadcast({
        "type": "user_archived",
        "user_id": customer_id,
        "role": "customer"
    }))
    
    return RedirectResponse(url="/admin/customers?success_msg=Customer+deleted+successfully", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/api/customers-overview")
async def get_customers_overview(
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    darwin_profile = _get_darwin_profile(db)
    active_darwin_filter = or_(
        models.Booking.is_archived.is_(False),
        models.Booking.is_archived.is_(None),
    )
    darwin_customer_ids = db.query(models.Booking.user_id).filter(
        models.Booking.caterer_id == darwin_profile.id,
        models.Booking.user_id.isnot(None),
        active_darwin_filter,
    ).distinct().subquery() if darwin_profile else None
    customers = db.query(models.User).filter(
        models.User.role == "customer",
        models.User.is_archived == False,
        models.User.id.in_(darwin_customer_ids) if darwin_customer_ids is not None else False,
    ).all()
    
    enriched = []
    for c in customers:
        # Get engagement metrics
        bookings = db.query(models.Booking).filter(
            models.Booking.user_id == c.id,
            models.Booking.caterer_id == darwin_profile.id,
            active_darwin_filter,
        ).all()
        booking_count = len(bookings)
        completed_bookings = [b for b in bookings if b.status == "completed"]
        cancelled_bookings = [b for b in bookings if b.status == "cancelled"]
        
        success_rate = 100
        if booking_count > 0:
            # Success rate is completed bookings vs total non-draft bookings
            success_rate = (len(completed_bookings) / booking_count) * 100 if booking_count > 0 else 100
            
        total_spent = sum([b.total_amount for b in completed_bookings if b.total_amount])
        
        # Get KYC details if any
        fraud_score = 0
        if c.identity_verification:
            fraud_score = c.identity_verification.fraud_score or 0

        enriched.append({
            "id": c.id,
            "first_name": c.first_name,
            "last_name": c.last_name,
            "email": c.email,
            "phone_number": c.phone_number,
            "address": c.address,
            "is_kyc_complete": c.is_kyc_complete,
            "status": c.status or "active",
            "fraud_score": fraud_score,
            "booking_count": booking_count,
            "success_rate": round(success_rate, 1),
            "total_spent": total_spent,
            "status_reason": c.status_reason,
            "investigation_notes": c.investigation_notes,
            "created_at": c.created_at.strftime('%b %d, %Y') if c.created_at else "N/A"
        })
        
    metrics = {
        "total_customers": len(customers),
        "active_customers": sum(1 for customer in customers if customer.status == "active"),
        "kyc_completed": sum(1 for customer in customers if customer.is_kyc_complete),
    }
    
    return {"success": True, "customers": enriched, "metrics": metrics}

@router.post("/api/customers/{user_id}/suspend")
async def suspend_customer(
    user_id: int, 
    reason: str = Form(...),
    db: Session = Depends(database.get_db), 
    admin: models.User = Depends(admin_only)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: return {"success": False, "message": "User not found"}
    user.status = "suspended"
    user.status_reason = reason
    
    # Log Audit
    audit = models.AuditLog(
        user_id=user_id,
        action="account_suspended",
        new_status="suspended",
        notes=f"Suspended by Admin: {reason}"
    )
    db.add(audit)
    
    db.commit()
    return {"success": True, "message": f"Account for {user.first_name} has been suspended."}

@router.post("/api/customers/{user_id}/activate")
async def activate_customer(user_id: int, db: Session = Depends(database.get_db), admin: models.User = Depends(admin_only)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: return {"success": False, "message": "User not found"}
    user.status = "active"
    user.status_reason = None
    
    # Log Audit
    audit = models.AuditLog(
        user_id=user_id,
        action="account_activated",
        new_status="active",
        notes="Activated by Admin"
    )
    db.add(audit)
    
    db.commit()
    return {"success": True, "message": f"Account for {user.first_name} is now active."}

@router.post("/api/customers/{user_id}/flag")
async def flag_customer(
    user_id: int, 
    reason: str = Form(...),
    db: Session = Depends(database.get_db), 
    admin: models.User = Depends(admin_only)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: return {"success": False, "message": "User not found"}
    user.status = "investigation"
    user.status_reason = reason
    
    # Log Audit
    audit = models.AuditLog(
        user_id=user_id,
        action="account_flagged",
        new_status="investigation",
        notes=f"Flagged for investigation: {reason}"
    )
    db.add(audit)
    
    db.commit()
    return {"success": True, "message": f"Account for {user.first_name} has been flagged for compliance investigation."}

@router.post("/api/users/{user_id}/clear-audit")
async def clear_user_audit(
    user_id: int,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return {"success": False, "message": "User not found."}

    user.status = "active"
    user.status_reason = None
    
    # If this is a caterer, also update the profile status
    if user.role == "caterer":
        profile = db.query(models.CatererProfile).filter(models.CatererProfile.user_id == user_id).first()
        if profile:
            profile.account_status = "Active"

    # Log Audit
    audit = models.AuditLog(
        user_id=user_id,
        action="audit_cleared",
        new_status="active",
        notes="Investigation finalized: Account cleared of all compliance concerns."
    )
    db.add(audit)
    db.commit()

    # Broadcast update
    
    asyncio.create_task(manager.broadcast({
        "type": "customer_update" if user.role == "customer" else "caterer_update",
        "user_id": user_id,
        "action": "audit_cleared"
    }))

    return {"success": True, "message": f"Audit cleared. Account for {user.first_name} is now restored."}

@router.post("/api/customers/{user_id}/investigation-update")
async def update_investigation(
    user_id: int,
    notes: str = Form(...),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: return {"success": False, "message": "User not found"}
    
    user.investigation_notes = notes
    
    # Log Audit
    audit = models.AuditLog(
        user_id=user_id,
        action="investigation_update",
        notes=f"Admin updated investigation notes: {notes}"
    )
    db.add(audit)
    
    db.commit()
    return {"success": True, "message": "Investigation notes updated."}

@router.get("/api/customers/{user_id}/kyc-audit")
async def get_customer_kyc_audit(user_id: int, db: Session = Depends(database.get_db), admin: models.User = Depends(admin_only)):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.role == "customer").first()
    if not user: return {"success": False, "message": "User not found"}
    
    kyc = db.query(models.IdentityVerification).filter(
        models.IdentityVerification.user_id == user_id,
        or_(models.IdentityVerification.verification_type.is_(None), models.IdentityVerification.verification_type != "business_permit")
    ).order_by(models.IdentityVerification.id.desc()).first()
    def safe_document_url(value):
        if value and value.startswith("/static/uploads/verification/"):
            return value.replace("/static/uploads/verification/", "/api/bookings/kyc/view/")
        return value
    if not kyc:
        return {"success": False, "message": "No identity submission was found for this customer."}
    
    return {
        "success": True,
        "document_url": safe_document_url(kyc.document_url),
        "document_back_url": safe_document_url(kyc.document_back_url),
        "selfie_url": safe_document_url(kyc.selfie_url),
        "selfie_2_url": safe_document_url(kyc.selfie_2_url),
        "selfie_3_url": safe_document_url(kyc.selfie_3_url),
        "id_type": kyc.id_type,
        "id_expiry_date": kyc.id_expiry_date.isoformat() if kyc.id_expiry_date else None,
        "id_number": kyc.id_number,
        "fraud_score": kyc.fraud_score or 0,
        "ocr_status": kyc.ocr_status,
        "liveness_status": kyc.liveness_status,
        "match_status": kyc.match_status,
        "failure_reason": kyc.failure_reason,
        "verification_status": kyc.verification_status,
        "verified_at": kyc.verified_at.strftime('%b %d, %Y') if kyc.verified_at else "N/A",
        "ocr_data": kyc.ocr_data,
        "status": user.status,
        "status_reason": user.status_reason,
        "investigation_notes": user.investigation_notes
    }

@router.post("/customers/{customer_id}/verify")
def verify_customer(
    customer_id: int, 
    action: str = Form(...), 
    reason: Optional[str] = Form(None),
    db: Session = Depends(database.get_db), 
    user: models.User = Depends(admin_only)
):
    customer = db.query(models.User).filter(models.User.id == customer_id, models.User.role == "customer").first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    if action == "approve":
        customer.is_verified = True
        customer.is_email_verified = True
        customer.status = "active"
        customer.status_reason = None
    else:
        customer.is_verified = False
        customer.status = "rejected"
        customer.status_reason = reason or "Identity verification failed."
    
    # Log Audit
    audit = models.AuditLog(
        user_id=customer_id,
        action=f"kyc_{action}",
        new_status=customer.status,
        notes=f"KYC {action} by Admin. Reason: {reason if reason else 'N/A'}"
    )
    db.add(audit)
    
    db.commit()
    return RedirectResponse(url=f"/admin/customers?success_msg=Customer+{action}+successfully", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/verify/{user_id_str}", response_class=HTMLResponse)
async def review_verification(
    user_id_str: str,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    if user_id_str == "None" or not user_id_str.isdigit():
        # Handle orphaned profiles gracefully
        return RedirectResponse(url="/admin/caterers?error_msg=This+partner+has+no+associated+identity+account", status_code=303)
        
    user_id = int(user_id_str)
    target_user = db.query(models.User).get(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Retrieve Government ID verification specifically (never accidentally select business_permit)
    gov_id_verification = db.query(models.IdentityVerification).filter(
        models.IdentityVerification.user_id == user_id,
        models.IdentityVerification.verification_type != 'business_permit'
    ).order_by(models.IdentityVerification.id.desc()).first()

    if not gov_id_verification:
        # Use a transient record for rendering; a read-only page must not persist an empty submission.
        gov_id_verification = models.IdentityVerification(user_id=user_id, verification_type='government_id')

    # Separate Business Permit verification specifically
    permit_verification = None
    if target_user.role == 'caterer' and target_user.caterer_profile:
        permit_verification = db.query(models.IdentityVerification).filter(
            models.IdentityVerification.user_id == user_id,
            models.IdentityVerification.verification_type == 'business_permit'
        ).order_by(models.IdentityVerification.id.desc()).first()

        # Retroactive Permit OCR for older profiles if permit exists but OCR record missing
        if not permit_verification and target_user.caterer_profile.permit_url:
            from app.services.verification import VerificationService
            try:
                v_service = VerificationService()
                permit_ocr_res = await v_service.extract_permit_data(target_user.caterer_profile.permit_url)
                permit_data = permit_ocr_res.get("data") if (permit_ocr_res and permit_ocr_res.get("success")) else None
                permit_verification = models.IdentityVerification(
                    user_id=user_id,
                    verification_type='business_permit',
                    document_url=target_user.caterer_profile.permit_url,
                    ocr_data=permit_data,
                    verification_status='Pending Review'
                )
                db.add(permit_verification)
                db.commit()
                db.refresh(permit_verification)
            except Exception as e:
                db.rollback()
                print(f"[KYC PERMIT OCR RECOVERY ERROR] {e}")

    # Explicit Document URLs
    caterer_prof = target_user.caterer_profile if target_user.role == 'caterer' else None
    gov_id_url = gov_id_verification.document_url or (caterer_prof.gov_id_url if caterer_prof else None)
    gov_id_back_url = gov_id_verification.document_back_url
    selfie_url = gov_id_verification.selfie_url
    permit_url = (caterer_prof.permit_url if caterer_prof else None) or (permit_verification.document_url if permit_verification else None)
    dti_url = caterer_prof.dti_url if caterer_prof else None
    bir_url = caterer_prof.bir_url if caterer_prof else None
    mayors_permit_url = caterer_prof.mayors_permit_url if caterer_prof else None

    # Calculate Name Match Status dynamically without guessing
    from app.services.verification import VerificationService
    v_service = VerificationService()
    reg_full_name = f"{target_user.first_name or ''} {target_user.last_name or ''}".strip()
    
    ocr_name_raw = None
    if gov_id_verification and gov_id_verification.ocr_data and isinstance(gov_id_verification.ocr_data, dict):
        f_data = gov_id_verification.ocr_data.get('fields', {})
        first_n = f_data.get('first_name', {}).get('value') or gov_id_verification.ocr_data.get('first_name')
        last_n = f_data.get('last_name', {}).get('value') or gov_id_verification.ocr_data.get('last_name')
        full_n = f_data.get('full_name', {}).get('value') or gov_id_verification.ocr_data.get('full_name')
        if full_n:
            ocr_name_raw = full_n
        elif first_n or last_n:
            ocr_name_raw = f"{first_n or ''} {last_n or ''}".strip()

    name_matched = False
    if ocr_name_raw and reg_full_name:
        name_matched = v_service.match_name(reg_full_name, ocr_name_raw)

    return templates.TemplateResponse("admin/verification_detail.html", {
        "request": request,
        "user": user,
        "target_user": target_user,
        "verification": gov_id_verification,
        "gov_id_verification": gov_id_verification,
        "permit_verification": permit_verification,
        "gov_id_url": gov_id_url,
        "gov_id_back_url": gov_id_back_url,
        "selfie_url": selfie_url,
        "permit_url": permit_url,
        "dti_url": dti_url,
        "bir_url": bir_url,
        "mayors_permit_url": mayors_permit_url,
        "ocr_name_raw": ocr_name_raw,
        "name_matched": name_matched,
        "active_page": "kyc"
    })


# --- New KYC & Fraud Admin Endpoints ---

@router.get("/api/bookings")
async def api_list_bookings(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    query = db.query(models.Booking)
    if status:
        query = query.filter(models.Booking.status == status)
    return query.order_by(models.Booking.created_at.desc(), models.Booking.id.desc()).offset(max(0, offset)).limit(min(max(1, limit), 500)).all()

@router.get("/bookings/{booking_id}/kyc")
async def view_booking_kyc(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    kyc = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == booking.user_id).first()
    audit_trail = db.query(models.AuditLog).filter(models.AuditLog.user_id == booking.user_id).order_by(models.AuditLog.timestamp.desc()).all()
    
    return templates.TemplateResponse("admin/booking_kyc.html", {
        "request": request,
        "user": user,
        "booking": booking,
        "kyc": kyc,
        "audit_trail": audit_trail,
        "active_page": "bookings"
    })

@router.post("/kyc/user/{user_id}/action")
async def kyc_manual_action(
    user_id: int,
    action: str = Form(...),
    notes: str = Form(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    target_user = db.query(models.User).get(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
        
    kyc = target_user.identity_verification
    if not kyc:
        # Create a placeholder if not exists to store the decision
        kyc = models.IdentityVerification(user_id=user_id, verification_status="pending")
        db.add(kyc)
        db.flush()
    
    old_status = kyc.verification_status
    
    target_user = db.query(models.User).get(kyc.user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    full_name = f"{target_user.first_name} {target_user.last_name}"
    
    if action == "approve":
        kyc.verification_status = "verified"
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        valid_until = datetime.now() + relativedelta(months=6)
        if hasattr(kyc, 'id_expiry_date') and kyc.id_expiry_date:
            id_expiry = kyc.id_expiry_date
            if isinstance(id_expiry, str):
                try: id_expiry = datetime.strptime(id_expiry, '%Y-%m-%d').date()
                except: pass
            if not isinstance(id_expiry, str) and id_expiry < valid_until.date():
                valid_until = datetime.combine(id_expiry, datetime.min.time())
        kyc.verification_valid_until = valid_until
        kyc.failure_reason = None
        target_user.is_verified = True
        target_user.is_kyc_complete = True
        target_user.status = "active"
        
        # If caterer, also update profile status
        if target_user.role == "caterer" and target_user.caterer_profile:
            target_user.caterer_profile.verification_status = "Verified"
            target_user.caterer_profile.account_status = "Active"
            if target_user.caterer_profile.status == "Published":
                target_user.caterer_profile.status = "Unpublished"
            if target_user.caterer_profile.permit_url:
                target_user.caterer_profile.permit_status = "Verified"
            
        # Send Approval Email
        EmailService.send_kyc_approval_email(target_user.email, full_name)
    else:
        kyc.verification_status = "rejected"
        kyc.failure_reason = notes or "Identity verification failed security audit."
        target_user.is_verified = False
        target_user.status = "suspended" # Prevents login
        
        if target_user.role == "caterer" and target_user.caterer_profile:
            target_user.caterer_profile.verification_status = "Rejected"
            target_user.caterer_profile.status = "Unpublished"
            if target_user.caterer_profile.permit_url:
                target_user.caterer_profile.permit_status = "Rejected"
            
        # Send Rejection Email
        EmailService.send_kyc_rejection_email(target_user.email, full_name, kyc.failure_reason)
    
    # Audit Log
    audit = models.AuditLog(
        user_id=target_user.id,
        action="manual_kyc_decision",
        old_status=old_status,
        new_status=kyc.verification_status,
        notes=f"Admin {user.email}: {notes}"
    )
    db.add(audit)
    db.commit()

    # Real-time update for all connected admins
    from ..services.realtime import manager
    
    asyncio.create_task(manager.broadcast({
        "type": "kyc_update",
        "user_id": target_user.id,
        "status": kyc.verification_status,
        "message": f"KYC for {full_name} has been {action}d."
    }))
    
    return RedirectResponse(url=f"/admin/verify/{target_user.id}?success_msg=Action+processed+successfully", status_code=303)

@router.post("/bookings/{booking_id}/flag")
async def flag_booking(
    booking_id: int,
    flag_type: str = Form(...),
    description: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    flag = models.FraudFlag(
        booking_id=booking_id,
        flag_type=flag_type,
        description=description
    )
    db.add(flag)
    db.commit()
    return RedirectResponse(url=f"/admin/bookings/{booking_id}/kyc?success_msg=Booking+flagged+successfully", status_code=303)

# Redirect old /reviews URL to the new /feedback page for backward compatibility
@router.get("/reviews")
async def redirect_reviews_to_feedback():
    return RedirectResponse(url="/admin/feedback", status_code=301)

@router.get("/feedback", response_class=HTMLResponse)
async def admin_feedback(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    feedbacks = db.query(models.PlatformFeedback).filter(
        models.PlatformFeedback.is_archived == False
    ).order_by(models.PlatformFeedback.created_at.desc()).all()

    total_count = len(feedbacks)
    highlighted_count = sum(1 for f in feedbacks if f.is_highlighted)
    high_rated_count = sum(1 for f in feedbacks if f.rating and f.rating >= 4)
    avg_rating = round(sum(f.rating for f in feedbacks if f.rating) / total_count, 1) if total_count else 0.0

    return templates.TemplateResponse("admin/feedback.html", {
        "request": request,
        "user": user,
        "feedbacks": feedbacks,
        "total_count": total_count,
        "highlighted_count": highlighted_count,
        "high_rated_count": high_rated_count,
        "avg_rating": avg_rating,
        "active_page": "feedback"
    })

@router.post("/feedback/{feedback_id}/highlight")
async def toggle_feedback_highlight(
    feedback_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    fb = db.query(models.PlatformFeedback).get(feedback_id)
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
    fb.is_highlighted = not fb.is_highlighted
    db.commit()
    return RedirectResponse(url="/admin/feedback?success_msg=Feedback+updated", status_code=303)

@router.post("/feedback/{feedback_id}/archive")
async def archive_feedback(
    feedback_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    fb = db.query(models.PlatformFeedback).get(feedback_id)
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
    fb.is_archived = True
    db.commit()
    return RedirectResponse(url="/admin/feedback?success_msg=Feedback+archived", status_code=303)

@router.get("/revenue", response_class=HTMLResponse)
async def admin_revenue(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    # Fetch all Commission Records (BillingInvoice)
    from sqlalchemy.orm import joinedload
    from sqlalchemy import extract
    
    invoices = db.query(models.BillingInvoice).options(
        joinedload(models.BillingInvoice.caterer),
        joinedload(models.BillingInvoice.booking)
    ).order_by(models.BillingInvoice.created_at.desc()).all()
    
    verified_invoices = [
        inv for inv in invoices
        if inv.status == 'paid' and inv.booking_id is None and inv.payment_proof_url
    ]
    total_commission_revenue = sum((inv.amount or 0.0) for inv in verified_invoices)
    
    now = datetime.utcnow()
    monthly_revenue = sum(
        (inv.amount or 0.0) for inv in verified_invoices
        if inv.created_at and inv.created_at.month == now.month and inv.created_at.year == now.year
    )
    
    pending_collection = sum(
        (inv.amount or 0.0) for inv in invoices
        if inv.booking_id is not None and inv.status in ('pending', 'processing')
    )
    verified_payments_count = len(verified_invoices)

    metrics_context = {
        "total_commission_revenue": total_commission_revenue,
        "monthly_revenue": monthly_revenue,
        "pending_collection": pending_collection,
        "verified_payments_count": verified_payments_count
    }
    
    return templates.TemplateResponse("admin/payments.html", {
        "request": request,
        "user": user,
        "invoices": invoices,
        "metrics": metrics_context,
        "active_page": "revenue"
    })

# --- REPORTS / ANALYTICS ---

@router.get("/reports", response_class=HTMLResponse)
async def admin_reports(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    from calendar import month_abbr
    from sqlalchemy.orm import joinedload, selectinload
    now = datetime.now(MANILA_TIMEZONE)

    # ── Shared definitions (kept in sync with the rest of the admin panel) ──
    # Bookings in these states never converted into platform revenue.
    NON_REVENUE_STATUSES = [
        'cancelled', 'canceled', 'rejected', 'inquiry', 'pending', 'pending_payment',
        'awaiting_payment', 'pending_review', 'negotiating', 'quoted',
        'pending_quotation', 'awaiting_customer', 'awaiting_caterer', 'draft', 'expired'
    ]
    # Bookings are "settled" when the flag says so, or when the amount collected
    # already covers the contract value (identical rule to PaymentService).
    # --- Monthly Growth (live platform accounts) ---
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)

    new_users_this_month = db.query(models.User).filter(
        _not_archived(models.User.is_archived),
        models.User.created_at >= this_month_start
    ).count()
    new_users_last_month = db.query(models.User).filter(
        _not_archived(models.User.is_archived),
        models.User.created_at >= last_month_start,
        models.User.created_at < this_month_start
    ).count()

    if new_users_last_month > 0:
        monthly_growth_pct = round(((new_users_this_month - new_users_last_month) / new_users_last_month) * 100, 1)
    else:
        monthly_growth_pct = 100.0 if new_users_this_month > 0 else 0.0

    # --- User Satisfaction (Average Review Rating) ---
    avg_rating_result = db.query(func.avg(models.Review.rating)).filter(
        _not_archived(models.Review.is_archived)
    ).scalar()
    avg_rating = round(float(avg_rating_result), 1) if avg_rating_result else 0.0
    total_reviews = db.query(models.Review).filter(_not_archived(models.Review.is_archived)).count()

    # --- Booking Summary ---
    # Count every active booking for volume; exclude archived rows, include NULL flags.
    active_booking_filter = _not_archived(models.Booking.is_archived)
    all_live_bookings = db.query(models.Booking).options(
        selectinload(models.Booking.payment_records),
        joinedload(models.Booking.quotation),
    ).filter(active_booking_filter).all()
    total_bookings = len(all_live_bookings)
    normalized_status = lambda booking: (booking.status or "").strip().lower().replace(" ", "_")
    cancelled_bookings = sum(1 for b in all_live_bookings if normalized_status(b) in {"cancelled", "canceled"})

    # Revenue metrics ignore cancelled / never-converted bookings.
    revenue_bookings = [b for b in all_live_bookings if normalized_status(b) not in NON_REVENUE_STATUSES]
    # Match PaymentService's canonical total field (total_price, then total_amount).
    total_revenue = sum(_booking_total_amount(b) for b in revenue_bookings)
    payment_summaries = {
        b.id: PaymentService.get_payment_summary(b)
        for b in all_live_bookings
    }
    # PaymentService reconciles transaction rows with legacy amount_paid using
    # verified_paid (max, never sum), excluding pending customer submissions.
    # Pending/partially paid bookings still contribute verified cash. Exclude
    # cancelled/expired bookings under the existing revenue treatment.
    cash_eligible_statuses = {"cancelled", "canceled", "expired"}
    total_collected = sum(
        payment_summaries[b.id]["verified_paid"]
        for b in all_live_bookings
        if normalized_status(b) not in cash_eligible_statuses
    )
    paid_bookings = sum(
        1 for b in revenue_bookings
        if payment_summaries[b.id].get("is_fully_paid")
    )

    # --- Monthly Bookings Trend (last 6 months) ---
    monthly_bookings = []
    monthly_labels = []
    month_starts = [now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)]
    for _ in range(5):
        previous_month = month_starts[-1] - timedelta(days=1)
        month_starts.append(previous_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0))

    for month_start in reversed(month_starts):
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        count = db.query(models.Booking).filter(
            active_booking_filter,
            models.Booking.created_at >= month_start,
            models.Booking.created_at < month_end
        ).count()
        monthly_bookings.append(count)
        monthly_labels.append(month_abbr[month_start.month])
    
    # --- Top Caterers (by booking count) ---
    top_caterers_raw = (
        db.query(models.CatererProfile, func.count(models.Booking.id).label("booking_count"))
        .join(models.Booking, models.Booking.caterer_id == models.CatererProfile.id)
        .join(models.User, models.User.id == models.CatererProfile.user_id)
        .filter(
            _not_archived(models.User.is_archived),
            active_booking_filter,
            func.lower(func.trim(func.coalesce(models.Booking.status, ''))).notin_(NON_REVENUE_STATUSES)
        )
        .group_by(models.CatererProfile.id)
        .order_by(func.count(models.Booking.id).desc())
        .limit(5)
        .all()
    )
    top_caterers = [{"name": c.business_name, "bookings": b} for c, b in top_caterers_raw]

    # Existing invoice ledger is the source of assessed commission; a payout
    # fee is included only where no booking invoice already accounts for it.
    total_commission = _tracked_platform_commissions(db)

    return templates.TemplateResponse("admin/reports.html", {
        "request": request,
        "user": user,
        "active_page": "reports",
        "monthly_growth_pct": monthly_growth_pct,
        "new_users_this_month": new_users_this_month,
        "avg_rating": avg_rating,
        "total_reviews": total_reviews,
        "total_bookings": total_bookings,
        "cancelled_bookings": cancelled_bookings,
        "paid_bookings": paid_bookings,
        "total_revenue": total_revenue,
        "total_collected": total_collected,
        "total_commission": total_commission,
        "monthly_labels": json.dumps(monthly_labels),
        "monthly_bookings": json.dumps(monthly_bookings),
        "top_caterers": top_caterers,
    })

# --- ARCHIVE SYSTEM ---

@router.get("/archives", response_class=HTMLResponse)
async def view_archives(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    archived_caterers = db.query(models.CatererProfile).join(models.User).filter(models.User.is_archived == True).all()
    archived_customers = db.query(models.User).filter(models.User.role == 'customer', models.User.is_archived == True).all()
    archived_bookings = db.query(models.Booking).filter(models.Booking.is_archived == True).all()
    archived_reviews = db.query(models.Review).filter(models.Review.is_archived == True).all()
    archived_feedback = db.query(models.PlatformFeedback).filter(models.PlatformFeedback.is_archived == True).all()
    archived_payouts = db.query(models.Payout).filter(models.Payout.is_archived == True).all()
    
    return templates.TemplateResponse("admin/archives.html", {
        "request": request,
        "user": user,
        "caterers": archived_caterers,
        "customers": archived_customers,
        "bookings": archived_bookings,
        "reviews": archived_reviews,
        "feedback": archived_feedback,
        "payouts": archived_payouts,
        "active_page": "archives"
    })

@router.post("/api/archives/{item_type}/{item_id}/archive")
async def archive_item(
    item_type: str,
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    model_map = {
        "caterers": models.User,
        "customers": models.User,
        "bookings": models.Booking,
        "reviews": models.Review,
        "feedback": models.PlatformFeedback,
        "payouts": models.Payout,
        "kyc": models.IdentityVerification
    }
    
    if item_type not in model_map:
        return {"success": False, "message": "Invalid item type"}
        
    model = model_map[item_type]
    item_id_to_audit = item_id
    
    if item_type == "caterers":
        profile = db.query(models.CatererProfile).get(item_id)
        if not profile: return {"success": False, "message": "Caterer not found"}
        item = db.query(models.User).get(profile.user_id)
    else:
        item = db.query(model).get(item_id)
        
    if not item: return {"success": False, "message": "Item not found"}
        
    item.is_archived = True
    
    # Audit Logging
    audit = models.AuditLog(
        user_id=user.id,
        action=f"ARCHIVE_{item_type.upper()}",
        notes=f"Moved {item_type} #{item_id} to system archives."
    )
    db.add(audit)
    db.commit()
    
    return {"success": True, "message": f"{item_type.capitalize()} archived successfully."}

@router.post("/api/archives/{item_type}/{item_id}/restore")
async def restore_item(
    item_type: str,
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    model_map = {
        "caterers": models.User,
        "customers": models.User,
        "bookings": models.Booking,
        "reviews": models.Review,
        "feedback": models.PlatformFeedback,
        "payouts": models.Payout,
        "kyc": models.IdentityVerification
    }
    
    if item_type not in model_map:
        return {"success": False, "message": "Invalid item type"}
        
    model = model_map[item_type]
    
    if item_type == "caterers":
        profile = db.query(models.CatererProfile).get(item_id)
        if profile:
            item = db.query(models.User).get(profile.user_id)
        else:
            item = db.query(models.User).get(item_id)
    else:
        item = db.query(model).get(item_id)
        
    if not item: return {"success": False, "message": "Item not found"}
        
    item.is_archived = False
    
    # Audit Logging
    audit = models.AuditLog(
        user_id=user.id,
        action=f"RESTORE_{item_type.upper()}",
        notes=f"Restored {item_type} #{item_id} from archives."
    )
    db.add(audit)
    db.commit()
    
    return {"success": True, "message": f"{item_type.capitalize()} restored successfully."}

@router.post("/api/archives/{item_type}/{item_id}/purge")
async def purge_item(
    item_type: str,
    item_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    model_map = {
        "caterers": models.User,
        "customers": models.User,
        "bookings": models.Booking,
        "reviews": models.Review,
        "feedback": models.PlatformFeedback,
        "payouts": models.Payout,
        "kyc": models.IdentityVerification
    }
    
    if item_type not in model_map:
        return {"success": False, "message": "Invalid item type"}
        
    model = model_map[item_type]
    
    if item_type == "caterers":
        profile = db.query(models.CatererProfile).get(item_id)
        if profile:
            item = db.query(models.User).get(profile.user_id)
            db.delete(profile)
        else:
            item = db.query(models.User).get(item_id)
    else:
        item = db.query(model).get(item_id)
        
    if not item: return {"success": False, "message": "Item not found"}
        
    db.delete(item)
    
    # Audit Logging
    audit = models.AuditLog(
        user_id=user.id,
        action=f"PURGE_{item_type.upper()}",
        notes=f"Permanently purged {item_type} #{item_id} from system."
    )
    db.add(audit)
    db.commit()
    
    return {"success": True, "message": f"{item_type.capitalize()} permanently purged."}


# ─── Notifications ────────────────────────────────────────────────────────────

@router.get("/notifications", response_class=HTMLResponse)
async def admin_notifications(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    notifications = db.query(models.Notification).filter(
        models.Notification.user_id == user.id
    ).order_by(models.Notification.created_at.desc()).all()
    
    from datetime import datetime
    now = datetime.now()
    
    return templates.TemplateResponse("admin/notifications.html", {
        "request": request,
        "user": user,
        "active_page": "notifications",
        "notifications": notifications,
        "now": now
    })

@router.get("/api/notifications/unread")
async def get_unread_notifications(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    count = db.query(models.Notification).filter(
        models.Notification.user_id == user.id,
        models.Notification.is_read == False
    ).count()
    return {"success": True, "unread_count": count}

@router.post("/api/notifications/mark-all-read")
async def mark_all_notifications_read(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    db.query(models.Notification).filter(
        models.Notification.user_id == user.id,
        models.Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"success": True, "message": "All operations resolved and archived."}

@router.post("/api/notifications/{notif_id}/mark-read")
async def mark_notification_read(
    notif_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    notif = db.query(models.Notification).filter(
        models.Notification.id == notif_id,
        models.Notification.user_id == user.id
    ).first()
    
    if notif and not notif.is_read:
        notif.is_read = True
        db.commit()
        
    return {"success": True}

@router.post("/api/notifications/{notif_id}/delete")
async def delete_notification(
    notif_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    notif = db.query(models.Notification).filter(
        models.Notification.id == notif_id,
        models.Notification.user_id == user.id
    ).first()
    
    if notif:
        db.delete(notif)
        db.commit()
        
    return {"success": True}

# ─── Booking Management ────────────────────────────────────────────────────────

@router.get("/bookings", response_class=HTMLResponse)
async def admin_bookings(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    PENDING_STATUSES = ['pending', 'pending_quotation', 'awaiting_payment', 'pending_payment', 'awaiting_caterer', 'pending_review']
    DISPUTED_STATUSES = ['disputed', 'under_dispute']
    page_size = 100
    try:
        page = max(1, int(request.query_params.get('page', '1')))
    except (TypeError, ValueError):
        page = 1
    status_filter = request.query_params.get('status', 'all')
    date_filter = request.query_params.get('date', 'all')
    caterer_id_filter = request.query_params.get('caterer_id', 'all')
    search_query = request.query_params.get('search', '').strip()[:100]

    active_booking_filter = _not_archived(models.Booking.is_archived)
    base_query = db.query(models.Booking).filter(active_booking_filter)
    if search_query:
        base_query = base_query.outerjoin(
            models.User, models.Booking.user_id == models.User.id
        ).outerjoin(
            models.CatererProfile, models.Booking.caterer_id == models.CatererProfile.id
        ).outerjoin(
            models.CateringPackage, models.Booking.package_id == models.CateringPackage.id
        )
        for search_term in search_query.split():
            search_pattern = _search_like_pattern(search_term)
            base_query = base_query.filter(or_(
                func.cast(models.Booking.id, String).ilike(search_pattern, escape="\\"),
                models.User.first_name.ilike(search_pattern, escape="\\"),
                models.User.last_name.ilike(search_pattern, escape="\\"),
                models.User.email.ilike(search_pattern, escape="\\"),
                models.Booking.customer_name.ilike(search_pattern, escape="\\"),
                models.Booking.customer_email.ilike(search_pattern, escape="\\"),
                models.Booking.customer_contact.ilike(search_pattern, escape="\\"),
                models.Booking._booking_ref.ilike(search_pattern, escape="\\"),
                models.Booking._customer_ref.ilike(search_pattern, escape="\\"),
                models.Booking.event_name.ilike(search_pattern, escape="\\"),
                models.Booking.event_type.ilike(search_pattern, escape="\\"),
                models.Booking.status.ilike(search_pattern, escape="\\"),
                models.Booking.payment_status.ilike(search_pattern, escape="\\"),
                func.cast(models.Booking.event_date, String).ilike(search_pattern, escape="\\"),
                func.cast(models.Booking.total_amount, String).ilike(search_pattern, escape="\\"),
                models.CatererProfile.business_name.ilike(search_pattern, escape="\\"),
                models.CateringPackage.name.ilike(search_pattern, escape="\\")
            ))
    if status_filter == 'pending':
        base_query = base_query.filter(models.Booking.status.in_(PENDING_STATUSES))
    elif status_filter == 'disputed':
        base_query = base_query.filter(models.Booking.status.in_(DISPUTED_STATUSES))
    elif status_filter in {'confirmed', 'completed', 'cancelled'}:
        base_query = base_query.filter(models.Booking.status == status_filter)

    today = date.today()
    if date_filter == 'today':
        base_query = base_query.filter(models.Booking.event_date == today)
    elif date_filter == 'this_week':
        week_start = today - timedelta(days=today.weekday())
        base_query = base_query.filter(models.Booking.event_date >= week_start, models.Booking.event_date < week_start + timedelta(days=7))
    elif date_filter == 'this_month':
        month_start = today.replace(day=1)
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        base_query = base_query.filter(models.Booking.event_date >= month_start, models.Booking.event_date < next_month)
    if caterer_id_filter != 'all' and str(caterer_id_filter).isdigit():
        base_query = base_query.filter(models.Booking.caterer_id == int(caterer_id_filter))

    total_filtered = base_query.count()
    total_pages = max(1, (total_filtered + page_size - 1) // page_size)
    page = min(page, total_pages)
    from sqlalchemy.orm import joinedload, selectinload
    bookings = base_query.options(
        joinedload(models.Booking.user),
        joinedload(models.Booking.caterer),
        joinedload(models.Booking.package),
        selectinload(models.Booking.payment_records),
    ).order_by(models.Booking.created_at.desc(), models.Booking.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    for booking in bookings:
        booking.admin_booking_ref = booking.booking_ref
        booking.admin_customer_ref = booking.customer_ref
        booking.admin_is_walkin = _is_walkin_booking(booking)
        booking.admin_booking_amount = _booking_total_amount(booking)
        linked_user_name = " ".join(filter(None, [
            booking.user.first_name if booking.user else None,
            booking.user.last_name if booking.user else None,
        ]))
        booking.admin_customer_name = (
            "Walk-in"
            if booking.admin_is_walkin
            else booking.customer_name or linked_user_name or "Customer"
        )
        booking.admin_customer_email = (
            None
            if booking.admin_is_walkin
            else booking.customer_email or (booking.user.email if booking.user else None) or "No customer account"
        )
        booking.admin_customer_label = (
            "Walk-in"
            if booking.admin_is_walkin
            else booking.admin_customer_name
        )
        booking.admin_payment_status = (booking.payment_status or "pending").replace("_", " ").title()

    # ─── Booking Intelligence Metrics ───
    # NOTE: "awaiting action" mirrors the statuses used by the table filters below.
    pending_bookings = db.query(func.count(models.Booking.id)).filter(active_booking_filter, models.Booking.status.in_(PENDING_STATUSES)).scalar() or 0
    completed_bookings = db.query(func.count(models.Booking.id)).filter(active_booking_filter, models.Booking.status == 'completed').scalar() or 0
    disputed_bookings = db.query(func.count(models.Booking.id)).filter(active_booking_filter, models.Booking.status.in_(DISPUTED_STATUSES)).scalar() or 0
    cancelled_bookings = db.query(func.count(models.Booking.id)).filter(active_booking_filter, models.Booking.status == 'cancelled').scalar() or 0
    total_bookings = db.query(func.count(models.Booking.id)).filter(active_booking_filter).scalar() or 0
    caterers = db.query(models.CatererProfile).join(
        models.Booking, models.Booking.caterer_id == models.CatererProfile.id
    ).filter(active_booking_filter).distinct().order_by(models.CatererProfile.business_name).all()

    metrics = {
        "total_bookings": total_bookings,
        "pending_bookings": pending_bookings,
        "completed_bookings": completed_bookings,
        "disputed_bookings": disputed_bookings,
        "cancelled_bookings": cancelled_bookings
    }

    return templates.TemplateResponse("admin/bookings.html", {
        "request": request,
        "user": user,
        "bookings": bookings,
        "metrics": metrics,
        "caterers": caterers,
        "page": page,
        "page_size": page_size,
        "total_filtered": total_filtered,
        "total_pages": total_pages,
        "status_filter": status_filter,
        "date_filter": date_filter,
        "caterer_id_filter": caterer_id_filter,
        "search_query": search_query,
        "active_page": "bookings"
    })


@router.get("/api/bookings/monitor-status")
async def get_booking_monitor_status(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    raw_ids = request.query_params.getlist("id")
    if len(raw_ids) > 100 or any(not value.isdigit() for value in raw_ids):
        raise HTTPException(status_code=400, detail="Provide up to 100 valid booking IDs.")

    booking_ids = {int(value) for value in raw_ids}
    bookings = db.query(models.Booking).filter(
        models.Booking.id.in_(booking_ids),
        models.Booking.is_archived == False,
    ).all() if booking_ids else []
    latest_booking_id = db.query(func.max(models.Booking.id)).filter(
        models.Booking.is_archived == False
    ).scalar() or 0
    return {
        "success": True,
        "latest_booking_id": latest_booking_id,
        "bookings": {
            str(booking.id): {
                "status": booking.status or "pending",
                "payment_status": booking.payment_status or "pending",
            }
            for booking in bookings
        },
    }



# ─── Customer Management ───────────────────────────────────────────────────────

@router.get("/customers", response_class=HTMLResponse)
async def admin_customers(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    # ── Customer Directory ────────────────────────────────────────────────────
    # Platform accounts and booking-only walk-in records have distinct actions
    # and are projected separately in the directory. This is the platform-wide
    # admin directory, so customer visibility and booking counts must not depend
    # on a particular caterer's profile or bookings.
    base_filters = [
        models.User.role == "customer",
        _not_archived(models.User.is_archived),
        models.User.email.isnot(None),
        func.trim(models.User.email) != "",
        func.lower(models.User.email).notlike("walkin\\_%@guest.occashare.com", escape="\\"),
        func.coalesce(models.User.auth_provider, "email") != "manual_entry",
    ]

    directory_booking_filters = [_not_archived(models.Booking.is_archived)]
    customer_booking_link = or_(
        models.Booking.user_id == models.User.id,
        and_(
            models.Booking.user_id.is_(None),
            func.lower(func.trim(models.Booking.customer_email))
            == func.lower(func.trim(models.User.email)),
        ),
    )
    customers = db.query(models.User).filter(*base_filters).order_by(
        models.User.created_at.desc()
    ).all()

    customers_by_email = {
        customer.email.strip().lower(): customer
        for customer in customers
        if customer.email
    }

    customer_refs_by_user = {}
    walkin_bookings_by_customer = {}
    from sqlalchemy.orm import joinedload
    directory_bookings = db.query(models.Booking).options(
        joinedload(models.Booking.user),
        joinedload(models.Booking.caterer),
    ).filter(
        models.Booking.status != "draft",
        *directory_booking_filters,
    ).all()

    for booking in directory_bookings:
        ref = booking.customer_ref
        if booking.user_id:
            customer_refs_by_user.setdefault(booking.user_id, set()).add(ref)
        if booking.customer_email:
            normalized_email = booking.customer_email.strip().lower()
            matching_customer = customers_by_email.get(normalized_email)
            if matching_customer:
                customer_refs_by_user.setdefault(matching_customer.id, set()).add(ref)

        if _is_walkin_booking(booking):
            key = (booking.caterer_id, ref)
            walkin_bookings_by_customer.setdefault(key, []).append(booking)

    # Include legacy bookings linked by email only when no user foreign key exists.
    booking_counts = dict(db.query(
        models.User.id,
        func.count(func.distinct(models.Booking.id)),
    ).outerjoin(
        models.Booking, customer_booking_link
    ).filter(
        *base_filters,
        *directory_booking_filters,
    ).group_by(models.User.id).all())
    for customer in customers:
        customer.admin_customer_refs = sorted(customer_refs_by_user.get(customer.id, set()))
        customer.admin_booking_count = booking_counts.get(customer.id, 0)

    walkin_customers = []
    for (caterer_id, customer_ref), bookings in walkin_bookings_by_customer.items():
        latest_booking = max(
            bookings,
            key=lambda booking: (booking.event_date or date.min, booking.id),
        )
        walkin_customers.append({
            "kind": "walkin",
            "name": latest_booking.customer_name
            or (f"{latest_booking.user.first_name or ''} {latest_booking.user.last_name or ''}".strip() if latest_booking.user else "")
            or "Walk-in",
            "customer_ref": customer_ref,
            "booking_count": len(bookings),
            "created_at": latest_booking.created_at,
            "latest_booking_id": latest_booking.id,
            "caterer_id": caterer_id,
        })
    walkin_customers.sort(key=lambda customer: customer["customer_ref"])

    verified_customers = [customer for customer in customers if customer.is_verified]
    pending_verification_customers = [customer for customer in customers if not customer.is_verified]

    # Metrics use the same records shown in the directory.
    metrics = {
        "total_customers": len(customers) + len(walkin_customers),
        "verified_customers": sum(1 for customer in customers if customer.is_verified),
        "pending_customers": sum(1 for customer in customers if not customer.is_verified),
        "suspended_customers": sum(
            1 for customer in customers
            if (customer.status or "").strip().casefold() == "suspended"
        ),
        "flagged_customers": sum(
            1 for customer in customers
            if (customer.status or "").strip().casefold() == "flagged"
        ),
        "walkin_customers": len(walkin_customers),
    }

    return templates.TemplateResponse("admin/customers.html", {
        "request": request,
        "user": user,
        "customers": customers,
        "walkin_customers": walkin_customers,
        "verified_customers": verified_customers,
        "pending_verification_customers": pending_verification_customers,
        "metrics": metrics,
        "active_page": "customers"
    })

# --- Customer Intelligence API Suite ---

@router.get("/api/customers/{customer_id}/audit")
async def get_customer_audit_data(
    customer_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    target = db.query(models.User).get(customer_id)
    if not target:
        return {"success": False, "message": "Participant not found."}
    
    # Calculate performance metrics
    darwin_profile = _get_darwin_profile(db)
    customer_booking_link = or_(
        models.Booking.user_id == target.id,
        and_(
            models.Booking.user_id.is_(None),
            func.lower(func.trim(models.Booking.customer_email))
            == func.lower(func.trim(target.email)),
        ),
    )
    booking_filters = [
        customer_booking_link,
        _not_archived(models.Booking.is_archived),
    ]
    if darwin_profile:
        booking_filters.append(models.Booking.caterer_id == darwin_profile.id)
    bookings = db.query(models.Booking).filter(*booking_filters).all()
    customer_refs = sorted({
        booking.customer_ref
        for booking in bookings
        if booking.status != "draft" and booking.customer_ref
    })
    normalized_status = lambda booking: (booking.status or "").strip().lower()
    total_completed = sum(1 for b in bookings if normalized_status(b) == "completed")
    total_spent = sum((b.total_amount or b.total_price or 0.0) for b in bookings if normalized_status(b) == "completed")
    cancellations = sum(1 for b in bookings if normalized_status(b) in {"cancelled", "canceled"})
    
    # Calculate Risk Score (0-100)
    risk_score = 0
    if len(bookings) > 0:
        cancel_rate = (cancellations / len(bookings)) * 100
        risk_score = min(100, cancel_rate + (5 if target.status == "flagged" else 0))

    return {
        "success": True,
        "data": {
            "full_name": f"{target.first_name} {target.last_name}",
            "email": target.email,
            "customer_refs": customer_refs,
            "status": target.status,
            "is_verified": target.is_verified,
            "join_date": target.created_at.strftime("%b %d, %Y") if target.created_at else None,
            "last_login": target.last_login.isoformat() if target.last_login else None,
            "phone_number": target.phone_number,
            "status_reason": target.status_reason,
            "total_bookings": len(bookings),
            "completed_bookings": total_completed,
            "cancelled_bookings": cancellations,
            "lifetime_value": float(total_spent),
            "cancellations": cancellations,
            "risk_score": round(risk_score, 1),
            "investigation_notes": target.investigation_notes
        }
    }

@router.post("/api/customers/{customer_id}/suspend")
async def suspend_customer_account(
    customer_id: int,
    reason: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    target = db.query(models.User).get(customer_id)
    if not target:
        return {"success": False, "message": "Participant not found."}
    
    target.status = "suspended"
    target.status_reason = reason
    db.commit()
    
    # Log Action
    new_log = models.AuditLog(
        user_id=user.id,
        action=f"SUSPENDED_CUSTOMER",
        details=f"Suspended User ID {customer_id}. Reason: {reason}"
    )
    db.add(new_log)
    db.commit()
    
    return {"success": True, "message": f"Account for {target.first_name} has been suspended."}

@router.post("/api/customers/{customer_id}/reactivate")
async def reactivate_customer_account(
    customer_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    target = db.query(models.User).get(customer_id)
    if not target:
        return {"success": False, "message": "Participant not found."}
    
    target.status = "active"
    target.status_reason = None
    db.commit()
    
    # Log Action
    new_log = models.AuditLog(
        user_id=user.id,
        action=f"REACTIVATED_CUSTOMER",
        details=f"Reactivated User ID {customer_id}."
    )
    db.add(new_log)
    db.commit()
    
    return {"success": True, "message": f"Account for {target.first_name} has been reactivated."}

@router.post("/api/customers/{customer_id}/flag")
async def flag_customer_account(
    customer_id: int,
    reason: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    target = db.query(models.User).get(customer_id)
    if not target:
        return {"success": False, "message": "Participant not found."}
    
    target.status = "flagged"
    target.status_reason = reason
    db.commit()
    return {"success": True, "message": f"Account for {target.first_name} has been flagged for review."}

@router.post("/api/customers/{customer_id}/unflag")
async def unflag_customer_account(
    customer_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    target = db.query(models.User).get(customer_id)
    if not target:
        return {"success": False, "message": "Participant not found."}
    
    target.status = "active"
    target.status_reason = None
    db.commit()
    return {"success": True, "message": f"Review flag cleared for {target.first_name}."}

@router.post("/api/customers/{customer_id}/send-alert")
async def send_system_alert(
    customer_id: int,
    message: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    # Logic to create a notification record for the user
    new_notif = models.Notification(
        user_id=customer_id,
        title="Administrative Alert",
        message=message,
        type="system_alert"
    )
    db.add(new_notif)
    db.commit()
    return {"success": True, "message": "System alert dispatched successfully."}


# ─── KYC Verification Terminal ────────────────────────────────────────────────

@router.post("/api/kyc/{kyc_id}/re-scan")
async def rescan_kyc_document(
    kyc_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    kyc = db.query(models.IdentityVerification).get(kyc_id)
    if not kyc or not kyc.document_url:
        return {"success": False, "message": "Verification record or document not found."}
    
    target_user = db.query(models.User).get(kyc.user_id)
    full_name = f"{target_user.first_name} {target_user.last_name}"
    
    try:
        # Re-run OCR using the improved extraction service
        result = await verification_service.verify_id_document(
            kyc.document_url, 
            full_name, 
            kyc.id_number or "", 
            kyc.verification_type or "Passport",
            db,
            target_user.id
        )
        
        if result["status"] == "error":
            return {"success": False, "message": result["failure_reason"]}
            
        # Update KYC record with new findings
        kyc.ocr_data = result.get("ocr_data", {})
        kyc.id_detected = result.get("is_likely_id", False)
        kyc.id_number = result.get("ocr_data", {}).get("id_number") or kyc.id_number
        
        # Update fraud and pattern status if available
        if "pattern_valid" in result:
            # We don't have a direct field for pattern_valid, but we can store it in notes or ocr_data
            pass
            
        db.commit()
        db.refresh(kyc)
        
        return {"success": True, "ocr_data": kyc.ocr_data}
    except Exception as e:
        print(f"[RE-SCAN ERROR] {e}")
        return {"success": False, "message": str(e)}

@router.post("/verify/manual-action")
async def kyc_manual_action(
    request: Request,
    target_user_id: int = Form(...),
    action: str = Form(...),
    reason: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    target_user = db.query(models.User).get(target_user_id)
    if not target_user:
        return {"success": False, "message": "User not found"}
        
    kyc = db.query(models.IdentityVerification).filter(
        models.IdentityVerification.user_id == target_user_id,
        models.IdentityVerification.verification_type != 'business_permit'
    ).order_by(models.IdentityVerification.id.desc()).first()

    if not kyc:
        kyc = target_user.identity_verification
    if not kyc:
        return {"success": False, "message": "KYC record not found"}
        
    if action == "approve":
        kyc.verification_status = "verified"
        valid_until = datetime.now() + relativedelta(months=6)
        if hasattr(kyc, 'id_expiry_date') and kyc.id_expiry_date:
            id_expiry = kyc.id_expiry_date
            if isinstance(id_expiry, str):
                try: id_expiry = datetime.strptime(id_expiry, '%Y-%m-%d').date()
                except: pass
            if not isinstance(id_expiry, str) and id_expiry < valid_until.date():
                valid_until = datetime.combine(id_expiry, datetime.min.time())
        kyc.verification_valid_until = valid_until
        target_user.is_verified = True
        target_user.is_kyc_complete = True
        target_user.status = "active"
        
        # Log action
        audit = models.AuditLog(
            user_id=user.id,
            action="KYC_APPROVE",
            notes=f"Approved KYC for User ID {target_user_id}. Reason: {reason}"
        )
        db.add(audit)
        
        # Send Email notification
        background_tasks.add_task(
            EmailService.send_kyc_approval_email, 
            target_user.email, 
            target_user.first_name
        )
    elif action == "resubmit":
        kyc.verification_status = "resubmission_required"
        kyc.failure_reason = reason
        target_user.status = "flagged"
        
        # Log action
        audit = models.AuditLog(
            user_id=user.id,
            action="KYC_RESUBMIT",
            notes=f"Requested KYC Resubmission for User ID {target_user_id}. Reason: {reason}"
        )
        db.add(audit)
    else:
        kyc.verification_status = "rejected"
        kyc.failure_reason = reason
        target_user.status = "suspended" # Terminate application usually means suspension
        
        # Log action
        audit = models.AuditLog(
            user_id=user.id,
            action="KYC_REJECT",
            notes=f"Rejected KYC for User ID {target_user_id}. Reason: {reason}"
        )
        db.add(audit)
        
        # Send Rejection Email
        background_tasks.add_task(
            EmailService.send_kyc_rejection_email,
            target_user.email,
            target_user.first_name,
            reason
        )
        
    # Phase 1.5: Sync Caterer Verification if applicable
    if target_user.role == "caterer" and target_user.caterer_profile:
        cat_prof = target_user.caterer_profile
        
        if action == "approve":
            cat_prof.verification_status = "Verified"
            cat_prof.is_verified = True
            cat_prof.account_status = "Active"
            if cat_prof.status == "Published":
                cat_prof.status = "Unpublished"
            target_user.is_verified = True
        elif action == "resubmit":
            cat_prof.verification_status = "Pending"
            cat_prof.is_verified = False
            cat_prof.status = "Unpublished"
        else:
            cat_prof.verification_status = "Rejected"
            cat_prof.is_verified = False
            cat_prof.status = "Unpublished"
            
        # Update specific CatererVerification record if it exists
        latest_caterer_ver = db.query(models.CatererVerification).filter_by(caterer_id=cat_prof.id).order_by(models.CatererVerification.id.desc()).first()
        if latest_caterer_ver:
            if action == "approve":
                latest_caterer_ver.status = "VERIFIED"
            elif action == "resubmit":
                latest_caterer_ver.status = "RESUBMISSION_REQUIRED"
            else:
                latest_caterer_ver.status = "REJECTED"
            latest_caterer_ver.reviewed_by = user.id
            latest_caterer_ver.reviewed_at = datetime.now()
            latest_caterer_ver.reviewer_notes = reason

    # Phase 2: Notify Customer in-app
    if action == "approve":
        notif_type = "success"
        title = "KYC Verification Approved"
        msg = "Your identity verification has been approved."
    elif action == "resubmit":
        notif_type = "warning"
        title = "Action Required: KYC Resubmission"
        msg = f"Your identity verification requires resubmission. Reason: {reason}"
    else:
        notif_type = "danger"
        title = "KYC Verification Rejected"
        msg = f"Your identity verification was rejected. Reason: {reason}"
    
    new_notif = models.Notification(
        user_id=target_user_id,
        title=title,
        message=msg,
        link="/customer/dashboard",
        type=notif_type
    )
    db.add(new_notif)
    db.commit()
    
    from ..services.realtime import manager
    import asyncio
    count = db.query(models.Notification).filter(models.Notification.user_id == target_user_id, models.Notification.is_read == False).count()
    asyncio.create_task(manager.broadcast_to_user(target_user_id, {
        "type": "new_notification",
        "message": title,
        "count": count
    }))
    db.commit()
    if "application/json" in request.headers.get("accept", ""):
        return {"success": True, "message": msg, "action": action, "account_status": target_user.status, "is_verified": target_user.is_verified}
    return RedirectResponse(url="/admin/dashboard?success_msg=Action+completed+successfully", status_code=303)


# ─── Booking Governance Terminal ──────────────────────────────────────────────

@router.get("/api/bookings/{booking_id}/details")
async def get_booking_details(
    booking_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    try:
        booking = db.query(models.Booking).get(booking_id)
        if not booking:
            return {"success": False, "message": "Booking not found"}
        
        # ─── Fraud Intelligence Risk Engine ───
        risk_score = 0
        fraud_indicators = []
        
        # Safely extract participant info
        caterer_user_id = booking.caterer.user_id if booking.caterer else None
        
        # 1. Identity Linkage (Self-Booking Check)
        if caterer_user_id and booking.user_id == caterer_user_id:
            risk_score += 90
            fraud_indicators.append("IDENTITY MATCH: Participant is booking their own service.")
        
        # 2. IP Linkage (Network Fingerprinting)
        customer_kyc = db.query(models.IdentityVerification).filter_by(user_id=booking.user_id).first()
        caterer_kyc = db.query(models.IdentityVerification).filter_by(user_id=caterer_user_id).first() if caterer_user_id else None
        
        if customer_kyc and caterer_kyc and customer_kyc.ip_address == caterer_kyc.ip_address and customer_kyc.ip_address is not None:
            risk_score += 70
            fraud_indicators.append(f"IP LINKAGE: Participants share network fingerprint ({customer_kyc.ip_address})")
            
        # 3. Communication Pattern Scanner (Platform Circumvention)
        suspicious_keywords = ["gcash", "viber", "whatsapp", "messenger", "091", "092", "093", "094", "095", "096", "097", "098", "099", "direct", "personal", "number"]
        content_to_scan = f"{booking.special_requests or ''} {booking.caterer_notes or ''}".lower()
        
        found_keywords = [word.upper() for word in suspicious_keywords if word in content_to_scan]
        if found_keywords:
            risk_score += (len(found_keywords) * 15)
            fraud_indicators.append(f"CIRCUMVENTION RISK: Suspicious keywords found: {', '.join(list(set(found_keywords)))}")

        # 4. Velocity Check (Frequent Interaction)
        # Use timezone-aware comparison to avoid database errors
        one_day_ago = datetime.now(booking.created_at.tzinfo) if booking.created_at and booking.created_at.tzinfo else datetime.now()
        one_day_ago = one_day_ago - timedelta(days=1)
        
        recent_bookings = db.query(models.Booking).filter(
            models.Booking.user_id == booking.user_id,
            models.Booking.caterer_id == booking.caterer_id,
            models.Booking.created_at >= one_day_ago
        ).count()
        
        if recent_bookings > 1:
            risk_score += 30
            fraud_indicators.append(f"VELOCITY ANOMALY: {recent_bookings} bookings between these parties in 24hrs.")

        # Cap risk score
        risk_score = min(risk_score, 100)

        try:
            from app.constants.booking_constants import entry_method_from_source
            entry_method = entry_method_from_source(booking.booking_source)
        except Exception:
            entry_method = 'online'

        return {
            "success": True,
            "booking": {
                "id": booking.id,
                "booking_ref": booking.booking_ref,
                "customer_ref": booking.customer_ref,
                "is_walkin": _is_walkin_booking(booking),
                "event_name": booking.event_name or "Standard Event",
                "event_type": booking.event_type or "Catering",
                "event_date": booking.event_date.strftime('%b %d, %Y') if booking.event_date else "TBD",
                "event_time": booking.event_time.strftime('%I:%M %p') if booking.event_time else "TBD",
                "guest_count": booking.guest_count,
                "total_amount": booking.total_amount,
                "status": booking.status,
                "payment_status": booking.payment_status,
                "amount_paid": float(booking.amount_paid or 0.0),
                "balance_due": max(float(booking.total_amount or 0.0) - float(booking.amount_paid or 0.0), 0.0),
                "booking_source": booking.booking_source or "OccaServe",
                "document_type": booking.document_type or "booking",
                "caterer_name": booking.caterer.business_name if booking.caterer else "N/A",
                "customer_name": (
                    "Walk-in"
                    if _is_walkin_booking(booking)
                    else (
                        f"{booking.user.first_name or ''} {booking.user.last_name or ''}".strip()
                        if booking.user
                        else booking.customer_name or "Customer"
                    )
                ),
                "special_requests": booking.special_requests or "None specified.",
                "payment_method": booking.payment_method,
                "payment_proof_url": booking.payment_proof_url,
                "balance_proof_url": booking.balance_proof_url,
                "created_at": booking.created_at.strftime('%b %d, %Y %I:%M %p') if booking.created_at else "Unknown",
                "history": [
                    {
                        "status": h.status,
                        "notes": h.notes,
                        "created_at": h.created_at.strftime('%b %d, %Y %I:%M %p')
                    } for h in sorted(booking.history, key=lambda x: x.created_at, reverse=True)
                ],
                "entry_method": entry_method,
                "package_name": booking.package.name if booking.package else "Custom Service",
                "downpayment_amount": float(booking.total_amount or 0) * 0.5, # Assuming 50% for display
                "risk_intelligence": {
                    "score": risk_score,
                    "indicators": fraud_indicators,
                    "level": "CRITICAL" if risk_score > 70 else ("ELEVATED" if risk_score > 30 else "LOW")
                }
            }
        }
    except Exception as e:
        print(f"[AUDIT_DETAILS_ERROR] {e}")
        return {"success": False, "message": f"Intelligence Engine Error: {str(e)}"}

@router.post("/api/bookings/{booking_id}/flag-dispute")
async def flag_booking_dispute(
    booking_id: int,
    reason: str = Form(...),
    description: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        return {"success": False, "message": "Booking not found"}
    
    word = "Order" if booking.document_type == "invoice" else "Booking"

    db.add(models.FraudFlag(
        booking_id=booking.id,
        flag_type="admin_review",
        description=f"{reason}: {description}",
    ))
    audit = models.AuditLog(
        user_id=user.id,
        action="BOOKING_FLAGGED_FOR_REVIEW",
        notes=f"Flagged {word.lower()} {booking.booking_ref} for admin review. Category: {reason}. Notes: {description}"
    )
    db.add(audit)
    db.commit()
    
    return {"success": True, "message": f"{word} {booking.booking_ref} flagged for admin review."}

@router.post("/api/bookings/{booking_id}/send-alert")
async def dispatch_booking_alert(
    booking_id: int,
    category: str = Form(...),
    message: str = Form(...),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        return {"success": False, "message": "Booking not found"}
    
    word = "Order" if booking.document_type == "invoice" else "Booking"
    reference = booking.booking_ref
    recipient_ids = {
        target_id
        for target_id in (
            None if _is_walkin_booking(booking) else booking.user_id,
            booking.caterer.user_id if booking.caterer else None,
        )
        if target_id
    }

    for target_id in recipient_ids:
        target_link = (
            f"/caterer/bookings?open_booking={booking.id}"
            if booking.caterer and target_id == booking.caterer.user_id
            else f"/customer/bookings/manage/{booking.id}"
        )
        db.add(models.Notification(
            user_id=target_id,
            title=f"System Notification: {category}",
            message=f"Regarding {reference}: {message}",
            link=target_link,
            type="info"
        ))
            
    audit = models.AuditLog(
        user_id=user.id,
        action="SEND_SYSTEM_ALERT",
        notes=f"Sent {category} alert for {reference}"
    )
    db.add(audit)
    db.commit()
    return {"success": True, "message": f"{word} alert dispatched successfully."}

@router.post("/api/notifications/{notification_id}/mark-read")
async def mark_admin_notification_read(
    notification_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    notif = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.user_id == user.id
    ).first()
    
    if not notif:
        return {"success": False, "message": "Alert record not found."}
        
    notif.is_read = True
    db.commit()
    return {"success": True, "message": "Alert marked as resolved."}

@router.post("/api/notifications/mark-all-read")
async def mark_all_admin_notifications_read(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(admin_only)
):
    db.query(models.Notification).filter(
        models.Notification.user_id == user.id,
        models.Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"success": True, "message": "All alerts marked as resolved in system logs."}

@router.get("/api/caterers/{caterer_id}/documents")
async def get_caterer_documents(
    caterer_id: int,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    profile = db.query(models.CatererProfile).filter(models.CatererProfile.id == caterer_id).first()
    if not profile:
        profile = db.query(models.CatererProfile).filter(models.CatererProfile.user_id == caterer_id).first()
    if not profile:
        return {"success": False, "message": f"Partner not found for ID {caterer_id}."}
        
    identity = db.query(models.IdentityVerification).filter(
        models.IdentityVerification.user_id == profile.user_id,
        models.IdentityVerification.verification_type != "business_permit",
    ).order_by(
        models.IdentityVerification.created_at.desc(),
        models.IdentityVerification.id.desc(),
    ).first()
    permit_identity = db.query(models.IdentityVerification).filter(
        models.IdentityVerification.user_id == profile.user_id,
        models.IdentityVerification.verification_type == "business_permit",
    ).order_by(
        models.IdentityVerification.created_at.desc(),
        models.IdentityVerification.id.desc(),
    ).first()
    business_review = db.query(models.CatererVerification).filter(
        models.CatererVerification.caterer_id == profile.id
    ).order_by(
        models.CatererVerification.submitted_at.desc(),
        models.CatererVerification.id.desc(),
    ).first()
    
    def fix_url(url):
        if url and url.startswith("/static/uploads/verification/"):
            return url.replace("/static/uploads/verification/", "/api/bookings/kyc/view/")
        return url

    # Determine gov_id_url: prefer IdentityVerification, fallback to CatererProfile
    gov_id_url_raw = None
    if identity and identity.document_url:
        gov_id_url_raw = identity.document_url
    elif profile.gov_id_url:
        gov_id_url_raw = profile.gov_id_url
    
    # Only expose an image submitted for identity verification, not the public profile photo.
    selfie_url_raw = None
    if identity and identity.selfie_url:
        selfie_url_raw = identity.selfie_url

    verified = profile.verification_status == "Verified"

    def document_status(url):
        if not url:
            return "Not submitted"
        return "Verified" if verified else "Submitted"

    permit_status = "Not submitted"
    if profile.permit_url:
        permit_status = (
            "Verified"
            if verified
            else (
                permit_identity.verification_status
                if permit_identity and permit_identity.verification_status
                else profile.permit_status or "Pending review"
            )
        )

    docs = {
        "permit_url": fix_url(profile.permit_url),
        "permit_expiry_date": str(profile.permit_expiry_date) if profile.permit_expiry_date else None,
        "dti_url": fix_url(profile.dti_url),
        "bir_url": fix_url(profile.bir_url),
        "mayors_permit_url": fix_url(profile.mayors_permit_url),
        "gov_id_url": fix_url(gov_id_url_raw),
        "gov_id_back_url": fix_url(identity.document_back_url) if identity else None,
        "id_type": identity.verification_type if identity else None,
        "selfie_url": fix_url(selfie_url_raw),
        "selfie_2_url": fix_url(identity.selfie_2_url) if identity else None,
        "selfie_3_url": fix_url(identity.selfie_3_url) if identity else None,
        "verification_summary": {
            "overall_status": profile.verification_status or "Unverified",
            "identity_status": (
                identity.verification_status
                if identity and identity.verification_status
                else ("Submitted" if gov_id_url_raw else "Not submitted")
            ),
            "id_type": identity.verification_type if identity else None,
            "business_status": (
                business_review.status
                if business_review and business_review.status
                else (profile.verification_status or "Unverified")
            ),
            "business_reviewed_at": (
                business_review.reviewed_at.isoformat()
                if business_review and business_review.reviewed_at
                else None
            ),
            "identity_reviewed_at": (
                (identity.reviewed_at or identity.verified_at).isoformat()
                if identity and (identity.reviewed_at or identity.verified_at)
                else None
            ),
            "permit_status": permit_status,
            "dti_status": document_status(profile.dti_url),
            "bir_status": document_status(profile.bir_url),
            "mayors_permit_status": document_status(profile.mayors_permit_url),
            "permit_expiry_date": str(profile.permit_expiry_date) if profile.permit_expiry_date else None,
        },
    }
    file_sources = [
        ("GOVERNMENT_ID", "Government ID (front)", gov_id_url_raw),
        ("GOVERNMENT_ID_BACK", "Government ID (back)", identity.document_back_url if identity else None),
        ("SELFIE", "Selfie photo", selfie_url_raw),
        ("SELFIE_2", "Selfie / proof of life 2", identity.selfie_2_url if identity else None),
        ("SELFIE_3", "Selfie / proof of life 3", identity.selfie_3_url if identity else None),
        ("BUSINESS_PERMIT", "Business permit", profile.permit_url),
        ("DTI_REGISTRATION", "DTI registration", profile.dti_url),
        ("BIR_REGISTRATION", "BIR registration", profile.bir_url),
        ("MAYORS_PERMIT", "Mayor's permit", profile.mayors_permit_url),
    ]
    verification_documents = {}
    if business_review:
        for document in sorted(business_review.documents, key=lambda item: item.id or 0):
            verification_documents[document.document_type] = document
    document_review_reasons = {}
    if business_review:
        audit_logs = sorted(
            business_review.audit_logs,
            key=lambda item: item.id or 0,
            reverse=True,
        )
        for document_type, document in verification_documents.items():
            latest_review = next(
                (log for log in audit_logs if document_type in (log.action or "")),
                None,
            )
            document_review_reasons[document_type] = latest_review.reason if latest_review else None
    docs["files"] = [
        {
            "type": document_type,
            "name": name,
            "url": fix_url(file_path),
            "status": (
                verification_documents[document_type].status
                if document_type in verification_documents
                and verification_documents[document_type].secure_file_path == file_path
                else "PENDING"
            ),
            "review_reason": document_review_reasons.get(document_type),
        }
        for document_type, name, file_path in file_sources
        if file_path
    ]
    docs["caterer_id"] = profile.id
    docs["caterer_name"] = profile.business_name or "Unnamed business"
    docs["caterer_email"] = profile.user.email if profile.user else None
    registrant = profile.user
    registered_address = ""
    if registrant:
        structured_address = ", ".join(
            part.strip() for part in (
                registrant.street_address,
                registrant.barangay,
                registrant.city_municipality,
                registrant.province,
            ) if part and part.strip()
        )
        registered_address = (
            (registrant.address or "").strip()
            or structured_address
            or (profile.contact_address or "").strip()
        )
    else:
        registered_address = (profile.contact_address or "").strip()
    docs["registrant"] = {
        "first_name": (registrant.first_name or "").strip() if registrant else "",
        "middle_name": (registrant.middle_name or "").strip() if registrant else "",
        "last_name": (registrant.last_name or "").strip() if registrant else "",
        "birthdate": registrant.dob.isoformat() if registrant and registrant.dob else None,
        "address": registered_address,
    }
    return {"success": True, "docs": docs}

@router.post("/api/caterers/{caterer_id}/documents/{document_type}/review")
async def review_caterer_document(
    caterer_id: int,
    document_type: str,
    action: str = Form(...),
    remarks: str = Form(""),
    review_reason: str = Form(""),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    profile = db.query(models.CatererProfile).filter(models.CatererProfile.id == caterer_id).first()
    if not profile:
        profile = db.query(models.CatererProfile).filter(models.CatererProfile.user_id == caterer_id).first()
    if not profile:
        return {"success": False, "message": f"Partner not found for ID {caterer_id}."}

    identity = db.query(models.IdentityVerification).filter(
        models.IdentityVerification.user_id == profile.user_id,
        models.IdentityVerification.verification_type != "business_permit",
    ).order_by(
        models.IdentityVerification.created_at.desc(),
        models.IdentityVerification.id.desc(),
    ).first()
    file_sources = {
        "GOVERNMENT_ID": ("Government ID (front)", (identity.document_url if identity else None) or profile.gov_id_url, "verif_id_front"),
        "GOVERNMENT_ID_BACK": ("Government ID (back)", identity.document_back_url if identity else None, "verif_id_back"),
        "SELFIE": ("Selfie photo", identity.selfie_url if identity else None, "verif_selfie"),
        "SELFIE_2": ("Selfie / proof of life 2", identity.selfie_2_url if identity else None, "verif_selfie"),
        "SELFIE_3": ("Selfie / proof of life 3", identity.selfie_3_url if identity else None, "verif_selfie"),
        "BUSINESS_PERMIT": ("Business permit", profile.permit_url, "verif_permit"),
        "DTI_REGISTRATION": ("DTI registration", profile.dti_url, "verif_dti"),
        "BIR_REGISTRATION": ("BIR registration", profile.bir_url, "verif_bir"),
        "MAYORS_PERMIT": ("Mayor's permit", profile.mayors_permit_url, "verif_permit"),
    }
    if document_type == "GOVERNMENT_ID":
        id_type_label = (identity.verification_type or "Government ID") if identity else "Government ID"
        selfie_types = [
            selfie_type for selfie_type in ("SELFIE", "SELFIE_2", "SELFIE_3")
            if file_sources[selfie_type][1]
        ]
        paired_id_files = {
            "GOVERNMENT_ID": file_sources["GOVERNMENT_ID"],
            "GOVERNMENT_ID_BACK": file_sources["GOVERNMENT_ID_BACK"],
            **{selfie_type: file_sources[selfie_type] for selfie_type in selfie_types},
        }
        if not all(paired_id_files.get(item) and paired_id_files[item][1] for item in ("GOVERNMENT_ID", "GOVERNMENT_ID_BACK", "SELFIE")):
            return {"success": False, "message": "The ID front, ID back, and selfie must all be submitted before identity review."}
        field_id = "verif_id_front"
    else:
        paired_id_files = None
    if document_type not in file_sources:
        return {"success": False, "message": "Unknown verification document."}
    if action not in {"approve", "request_revision"}:
        return {"success": False, "message": "Choose approve or request revision."}
    approval_reasons = {
        "meets_requirements": "The document is readable, complete, and matches the required details."
    }
    replacement_reasons = {
        "unreadable": "Image is blurry or unreadable",
        "missing_details": "Required details are missing or cut off",
        "wrong_document": "Wrong document type was submitted",
        "details_mismatch": "Details do not match the caterer or business profile",
        "altered_or_expired": "File appears altered, expired, or incomplete",
    }
    if action == "approve":
        if review_reason not in approval_reasons:
            return {"success": False, "message": "Choose the approval reason before approving this file."}
        remarks = f"{approval_reasons[review_reason]} {remarks.strip()}".strip()
    if action == "request_revision":
        if review_reason not in replacement_reasons:
            return {"success": False, "message": "Choose one valid replacement reason."}
        reason_summary = replacement_reasons[review_reason]
        remarks = f"{reason_summary}. {remarks.strip()}".strip()

    if paired_id_files:
        label = f"{id_type_label} and selfie"
        file_paths_to_review = paired_id_files
    else:
        label, file_path, field_id = file_sources[document_type]
        if not file_path:
            return {"success": False, "message": "This verification file has not been submitted."}
        file_paths_to_review = {document_type: (label, file_path, field_id)}

    verification = db.query(models.CatererVerification).filter(
        models.CatererVerification.caterer_id == profile.id
    ).order_by(
        models.CatererVerification.submitted_at.desc(),
        models.CatererVerification.id.desc(),
    ).first()
    if not verification:
        verification = models.CatererVerification(caterer_id=profile.id, status="PENDING_REVIEW")
        db.add(verification)
        db.flush()

    documents_to_review = []
    for doc_type, (doc_label, file_path, _field_id) in file_paths_to_review.items():
        document = db.query(models.VerificationDocument).filter_by(
            verification_id=verification.id,
            document_type=doc_type,
        ).order_by(models.VerificationDocument.id.desc()).first()
        if not document:
            document = models.VerificationDocument(
                verification_id=verification.id,
                document_type=doc_type,
                secure_file_path=file_path,
                status="PENDING",
            )
            db.add(document)
        elif document.secure_file_path != file_path:
            document.secure_file_path = file_path
            document.status = "PENDING"
        document_status = (document.status or "PENDING").upper()
        if document_status != "PENDING" and not (paired_id_files and document_status == "VALID"):
            return {"success": False, "message": "This identity review has already been decided. Refresh the document list before taking another action."}
        documents_to_review.append((doc_type, doc_label, document))

    if paired_id_files and all((document.status or "").upper() == "VALID" for _, _, document in documents_to_review) and action == "approve":
        return {"success": False, "message": "The ID and selfie have already been approved."}

    if action == "approve":
        for doc_type, _doc_label, document in documents_to_review:
            document.status = "VALID"
            db.add(models.VerificationAuditLog(
                verification_id=verification.id,
                admin_id=admin.id,
                action=f"Approved document: {doc_type}",
                reason=remarks.strip() or None,
            ))
        if paired_id_files and identity:
            identity.verification_status = "VERIFIED"
            identity.review_status = "approved"
            identity.reviewed_by = admin.id
            identity.reviewed_at = datetime.now(timezone.utc)
            identity.verified_at = identity.reviewed_at
    else:
        for doc_type, _doc_label, document in documents_to_review:
            document.status = "INVALID"
            db.add(models.VerificationAuditLog(
                verification_id=verification.id,
                admin_id=admin.id,
                action=f"Requested revision for document: {doc_type}",
                reason=remarks.strip() or None,
            ))
        if paired_id_files and identity:
            identity.verification_status = "REVERIFICATION_REQUIRED"
            identity.review_status = "requested_reverification"
            identity.reviewed_by = admin.id
            identity.reviewed_at = datetime.now(timezone.utc)
        verification.status = "RESUBMISSION_REQUIRED"
        verification.rejection_reason = f"{label}: {remarks.strip()}"
        verification.reviewed_by = admin.id
        verification.reviewed_at = datetime.now(timezone.utc)
        profile.verification_status = "Requires Revision"
        profile.admin_remarks = verification.rejection_reason
        profile.is_verified = False
        profile.account_status = "Restricted"
        if profile.status == "Published":
            profile.status = "Unpublished"
        if profile.user:
            profile.user.is_verified = False
            profile.user.is_kyc_complete = False


    if action == "request_revision" and profile.user_id:
        db.add(models.Notification(
            user_id=profile.user_id,
            title="Verification file needs an update",
            message=f"{label} needs to be replaced. Admin note: {remarks.strip()}",
            type="warning",
            link=f"/caterer/profile?verification_file={field_id}&verification_type={document_type}#verification-file",
        ))

    db.flush()
    current_files = [
        (doc_type, path)
        for doc_type, (_, path, _) in file_sources.items()
        if path
    ]
    all_files_approved = bool(current_files) and all(
        db.query(models.VerificationDocument).filter_by(
            verification_id=verification.id,
            document_type=doc_type,
            secure_file_path=path,
            status="VALID",
        ).first()
        for doc_type, path in current_files
    )
    has_files_needing_revision = any(
        db.query(models.VerificationDocument).filter_by(
            verification_id=verification.id,
            document_type=doc_type,
            secure_file_path=path,
            status="INVALID",
        ).first()
        for doc_type, path in current_files
    )

    if action == "approve" and all_files_approved:
        verification.status = "VERIFIED"
        verification.rejection_reason = None
        verification.reviewed_by = admin.id
        verification.reviewed_at = datetime.now(timezone.utc)
        profile.verification_status = "Verified"
        profile.admin_remarks = None
        profile.is_verified = True
        profile.account_status = "Active"
        if profile.user:
            profile.user.is_verified = True
            profile.user.is_kyc_complete = True
            profile.user.status = "active"
            profile.user.status_reason = None
        if profile.permit_url:
            profile.permit_status = "Verified"
        if profile.user_id:
            db.add(models.Notification(
                user_id=profile.user_id,
                title="Verification approved",
                message="All submitted verification files have been approved.",
                type="success",
                link="/caterer/profile#verification",
            ))
    elif action == "approve":
        verification.status = "RESUBMISSION_REQUIRED" if has_files_needing_revision else "PENDING_REVIEW"
        if not has_files_needing_revision:
            profile.verification_status = "Pending Review"

    db.commit()
    return {
        "success": True,
        "message": f"{label} {'approved' if action == 'approve' else 'marked for replacement'}.",
        "all_approved": all_files_approved,
        "status": verification.status,
    }

@router.post("/api/caterers/{caterer_id}/review")
async def submit_caterer_review(
    caterer_id: int,
    status: str = Form(...),
    remarks: str = Form(""),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    profile = db.query(models.CatererProfile).filter(models.CatererProfile.id == caterer_id).first()
    if not profile:
        return {"success": False, "message": "Partner not found"}
        
    profile.verification_status = status
    profile.admin_remarks = remarks
    
    identity = db.query(models.IdentityVerification).filter(
        models.IdentityVerification.user_id == profile.user_id,
        models.IdentityVerification.verification_type != "business_permit",
    ).order_by(
        models.IdentityVerification.created_at.desc(),
        models.IdentityVerification.id.desc(),
    ).first()
    if identity:
        identity.verification_status = status

    if status not in {"Verified", "Requires Revision", "Rejected", "Suspended"}:
        return {"success": False, "message": "Unsupported verification decision."}

    if status == "Verified":
        profile.is_verified = True
        profile.account_status = "Active"
        if profile.user:
            profile.user.is_verified = True
            profile.user.is_kyc_complete = True
            profile.user.status = "active"
            profile.user.status_reason = None
        if profile.permit_url:
            profile.permit_status = "Verified"
    else:
        profile.is_verified = False
        if profile.status == "Published":
            profile.status = "Unpublished"
        if profile.user:
            profile.user.is_verified = False
            profile.user.is_kyc_complete = False
            if status == "Suspended":
                profile.user.status = "suspended"
                profile.user.status_reason = remarks
                profile.account_status = "Suspended"
        if profile.permit_url and status in {"Requires Revision", "Rejected"}:
            profile.permit_status = status

    if identity:
        identity.review_status = "approved" if status == "Verified" else (
            "requested_reverification" if status == "Requires Revision" else "rejected"
        )
        identity.reviewed_by = admin.id
        identity.reviewed_at = datetime.now(timezone.utc)
        if status == "Verified":
            identity.verified_at = datetime.now(timezone.utc)
        else:
            identity.failure_reason = remarks

    latest_business_review = db.query(models.CatererVerification).filter(
        models.CatererVerification.caterer_id == profile.id
    ).order_by(
        models.CatererVerification.submitted_at.desc(),
        models.CatererVerification.id.desc(),
    ).first()
    if latest_business_review:
        latest_business_review.status = {
            "Verified": "VERIFIED",
            "Requires Revision": "RESUBMISSION_REQUIRED",
            "Rejected": "REJECTED",
            "Suspended": "REJECTED",
        }[status]
        latest_business_review.reviewed_by = admin.id
        latest_business_review.reviewed_at = datetime.now(timezone.utc)
        latest_business_review.rejection_reason = remarks or None
                
    # Log Audit
    audit = models.AuditLog(
        user_id=profile.user_id,
        action="verification_review",
        new_status=status,
        notes=f"Admin Review: {status}. Remarks: {remarks}"
    )
    db.add(audit)
    
    # Phase 2: Notify Caterer of KYC Status Change
    if profile.user_id:
        notif_type = "success" if status == "Verified" else ("danger" if status in ["Rejected", "Suspended"] else "warning")
        title = "Verification Approved" if status == "Verified" else "Verification Update"
        msg = f"Your business verification documents have been {status}."
        if remarks:
            msg += f" Remarks: {remarks}"
            
        new_notif = models.Notification(
            user_id=profile.user_id,
            title=title,
            message=msg,
            link="/caterer/profile#verification",
            type=notif_type
        )
        db.add(new_notif)
        db.commit()
        
        from ..services.realtime import manager
        import asyncio
        count = db.query(models.Notification).filter(models.Notification.user_id == profile.user_id, models.Notification.is_read == False).count()
        asyncio.create_task(manager.broadcast_to_user(profile.user_id, {
            "type": "new_notification",
            "message": title,
            "count": count
        }))
    else:
        db.commit()
    
    return {"success": True, "message": f"Partner verification updated to {status}."}
