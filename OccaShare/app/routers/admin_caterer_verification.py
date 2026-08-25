from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List

from ..db import models, database
from ..core import security as auth
admin_only = auth.RoleChecker(["admin"])
from ..core.templates import templates

router = APIRouter(prefix="/admin", tags=["admin_caterer_verification"])

@router.get("/caterer-verification", response_class=HTMLResponse)
async def view_caterer_verifications(
    request: Request, 
    db: Session = Depends(database.get_db), 
    admin: models.User = Depends(admin_only)
):
    # Fetch all verifications
    verifications = db.query(models.CatererVerification).order_by(
        # Sort pending first
        models.CatererVerification.status == 'PENDING_REVIEW',
        desc(models.CatererVerification.submitted_at)
    ).all()
    
    # Counts for dashboard
    pending_count = sum(1 for v in verifications if v.status == 'PENDING_REVIEW')
    verified_count = sum(1 for v in verifications if v.status == 'VERIFIED')
    rejected_count = sum(1 for v in verifications if v.status == 'REJECTED')
    resubmission_count = sum(1 for v in verifications if v.status == 'RESUBMISSION_REQUIRED')

    return templates.TemplateResponse("admin/caterer_verification.html", {
        "request": request,
        "user": admin,
        "active_page": "caterer_verification",
        "verifications": verifications,
        "pending_count": pending_count,
        "verified_count": verified_count,
        "rejected_count": rejected_count,
        "resubmission_count": resubmission_count
    })

@router.get("/api/caterer-verification/{verification_id}")
async def api_get_verification_details(
    verification_id: int, 
    db: Session = Depends(database.get_db), 
    admin: models.User = Depends(admin_only)
):
    verification = db.query(models.CatererVerification).filter(models.CatererVerification.id == verification_id).first()
    if not verification:
        return JSONResponse(status_code=404, content={"success": False, "message": "Verification not found"})
        
    caterer = verification.caterer
    docs = {doc.document_type: {"path": doc.secure_file_path, "expires_at": doc.expires_at.isoformat() if doc.expires_at else None} for doc in verification.documents}
    
    return {
        "success": True,
        "data": {
            "id": verification.id,
            "caterer_name": caterer.business_name,
            "caterer_email": caterer.user.email,
            "status": verification.status,
            "submitted_at": verification.submitted_at.isoformat() if verification.submitted_at else None,
            "documents": docs,
            "rejection_reason": verification.rejection_reason
        }
    }

@router.post("/api/caterer-verification/{verification_id}/review")
async def api_review_verification(
    verification_id: int,
    action: str = Form(...), # approve, reject, resubmit
    reason: str = Form(""),
    permit_expiry: str = Form(None),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(admin_only)
):
    verification = db.query(models.CatererVerification).filter(models.CatererVerification.id == verification_id).first()
    if not verification:
        return JSONResponse(status_code=404, content={"success": False, "message": "Verification not found"})
        
    if action not in ["approve", "reject", "resubmit"]:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid action"})
        
    caterer = verification.caterer
    
    if action == "approve":
        verification.status = "VERIFIED"
        caterer.verification_status = "VERIFIED"
        caterer.account_status = "ACTIVE"
        audit_action = "Approved Verification"
        
        # Update expiry date if admin edited it
        if permit_expiry:
            from datetime import datetime
            try:
                new_expiry = datetime.strptime(permit_expiry, "%Y-%m-%d").date()
                caterer.permit_expiry_date = new_expiry
                for doc in verification.documents:
                    if doc.document_type == "BUSINESS_PERMIT":
                        doc.expires_at = new_expiry
            except:
                pass
                
    elif action == "reject":
        verification.status = "REJECTED"
        verification.rejection_reason = reason
        caterer.verification_status = "REJECTED"
        caterer.account_status = "RESTRICTED"
        audit_action = "Rejected Verification"
        
    elif action == "resubmit":
        verification.status = "RESUBMISSION_REQUIRED"
        verification.rejection_reason = reason
        caterer.verification_status = "RESUBMISSION_REQUIRED"
        caterer.account_status = "RESTRICTED"
        audit_action = "Requested Resubmission"
        
    verification.reviewed_by = admin.id
    from sqlalchemy.sql import func
    verification.reviewed_at = func.now()
    
    # Audit log
    audit_log = models.VerificationAuditLog(
        verification_id=verification.id,
        admin_id=admin.id,
        action=audit_action,
        reason=reason
    )
    db.add(audit_log)
    
    # Send notification to caterer
    notif = models.Notification(
        user_id=caterer.user_id,
        title="Verification Status Updated",
        message=f"Your caterer verification has been {audit_action.lower()}.",
        type="info" if action == "resubmit" else ("success" if action == "approve" else "danger"),
        link="/caterer/verification"
    )
    db.add(notif)
    
    db.commit()
    
    return {"success": True, "message": f"Verification {action}d successfully."}

@router.get("/api/cron/check-permit-expiration")
async def cron_check_permit_expiration(db: Session = Depends(database.get_db)):
    """
    Background Cron Job to check for expired business permits.
    Should be hit daily at midnight.
    """
    from datetime import date
    
    today = date.today()
    
    # Find all active caterers whose permit_expiry_date is less than today
    expired_caterers = db.query(models.CatererProfile).filter(
        models.CatererProfile.account_status == 'ACTIVE',
        models.CatererProfile.permit_expiry_date < today
    ).all()
    
    count = 0
    for caterer in expired_caterers:
        # Update statuses
        caterer.account_status = 'RESTRICTED'
        caterer.verification_status = 'EXPIRED'
        
        # Send notification
        if caterer.user_id:
            notif = models.Notification(
                user_id=caterer.user_id,
                title="Business Permit Expired",
                message="Your business permit has expired. Your account is now restricted. Please upload a new permit to continue offering services.",
                type="danger",
                link="/caterer/verification"
            )
            db.add(notif)
            
        count += 1
        
    db.commit()
    
    return {"success": True, "message": f"Checked permit expirations. {count} caterers expired."}

