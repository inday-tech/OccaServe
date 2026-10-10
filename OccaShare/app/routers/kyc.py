from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from ..db import database, models
from ..core import security as auth
from ..services.verification import verification_service
from ..core.encryption import encrypt_data, decrypt_data
from ..core.utils import validate_file_type_and_size
from fastapi.responses import Response
from ..services.notification import NotificationService
from ..services.realtime import manager
from ..services.identity_storage import (
    MAX_IDENTITY_IMAGE_BYTES,
    delete_identity_image,
    identity_image_url,
    load_identity_image,
    private_identity_filename,
    store_identity_image,
    validate_identity_image,
)
import os

import uuid
import shutil
import io
import asyncio
import time
import traceback
import random
import secrets
import hmac
from datetime import datetime, timedelta, timezone

ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"]

router = APIRouter(prefix="/api/bookings", tags=["kyc"])

UPLOAD_DIR = "app/static/uploads/verification"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/test-extract")
async def test_extract(current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")

    import glob
    files = glob.glob(os.path.join(UPLOAD_DIR, "temp_ocr_*.enc"))
    if not files:
        return {"error": "No temp_ocr files found in verification upload directory."}
    # Sort by modification time to get the latest file
    latest_file = max(files, key=os.path.getmtime)
    filename = os.path.basename(latest_file)
    id_url = f"/api/bookings/kyc/view/{filename}"
    result = await verification_service.extract_id_data(id_url, "PhilSys / PhilID")
    return {"file_tested": latest_file, "result": result}

@router.api_route("/clear-duplicate-id", methods=["GET", "POST"])
async def clear_duplicate_id_route(
    id_number: str = "7601-8372-1475-8026",
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Utility route to clear duplicate identity_verifications records matching an ID number using raw SQL."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")

    import re
    from sqlalchemy import text
    clean_target = re.sub(r'[\s\-]', '', id_number)

    rows = db.execute(text("SELECT id, user_id, id_number, verification_status FROM identity_verifications")).fetchall()
    deleted_info = []

    for row in rows:
        rec_id, u_id, r_num, status = row
        clean_r = re.sub(r'[\s\-]', '', str(r_num or ""))

        if clean_target and clean_target in clean_r and u_id != current_user.id:
            deleted_info.append(f"Record #{rec_id} (User #{u_id}, Status: '{status}')")
            db.execute(text("DELETE FROM identity_verifications WHERE id = :id"), {"id": rec_id})

    db.commit()
    return {
        "status": "success",
        "message": f"Cleared {len(deleted_info)} duplicate record(s) matching '{id_number}'.",
        "deleted_records": deleted_info
    }

@router.post("/extract-id")
async def extract_id(
    id_type: str = Form(...),
    id_document: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Endpoint for Section B: Extracts data from ID for the booking form."""
    content = await id_document.read(MAX_IDENTITY_IMAGE_BYTES + 1)
    try:
        validate_identity_image(content, id_document.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    id_url = store_identity_image(content, id_document.filename or "")
    
    try:
        result = await verification_service.extract_id_data(id_url, id_type)
    except Exception:
        raise

    
    if not result.get("success"):
        delete_identity_image(id_url)
        raise HTTPException(status_code=400, detail=result.get("error"))
        
    # Check if the extracted name matches the registered customer's name
    full_name_parts = [current_user.first_name]
    if current_user.middle_name: full_name_parts.append(current_user.middle_name)
    full_name_parts.append(current_user.last_name)
    user_full_name = " ".join(full_name_parts)
    
    extracted_data = result["data"]
    fields = extracted_data.get("fields", {})
    
    def get_field_val(f_key):
        f_val = fields.get(f_key)
        if isinstance(f_val, dict):
            return f_val.get("value", "")
        return str(f_val) if f_val is not None else ""
        
    ocr_full_name = extracted_data.get("full_name", "")
    ocr_last_name = get_field_val("last_name")
    ocr_first_name = get_field_val("first_name") or get_field_val("given_names")
    ocr_middle_name = get_field_val("middle_name")
    raw_ocr = extracted_data.get("raw_text", "")
        
    name_matched = verification_service.match_name(
        user_full_name,
        ocr_full_name,
        ocr_last_name,
        ocr_first_name,
        ocr_middle_name,
        raw_ocr
    )
    
    if not ocr_first_name.strip() and not ocr_last_name.strip():
        delete_identity_image(id_url)
        raise HTTPException(
            status_code=400,
            detail="Extraction Error | Could not read your ID. Please make sure the photo is clear and not blurry."
        )
        
    if not name_matched:
        delete_identity_image(id_url)
        raise HTTPException(
            status_code=400,
            detail="The name on your ID does not match your account details. Please upload your own valid ID or update your account information."
        )
    
    # Update/Create verification record as pending_confirmation
    kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).order_by(models.IdentityVerification.created_at.desc(), models.IdentityVerification.id.desc()).first()
    if not kyc_record or kyc_record.verification_status in ['VERIFIED', 'EXPIRED', 'rejected', 'blocked', 'verified']:
        kyc_record = models.IdentityVerification(user_id=current_user.id)
        db.add(kyc_record)
    
    kyc_record.verification_status = "pending_confirmation"
    # Use cropped URL if auto-crop succeeded
    # Cropped previews may be returned as data URIs; persist only the encrypted
    # original upload, never a base64 image or a public CDN URL in the database.
    final_doc_url = id_url
    kyc_record.document_url = final_doc_url
    kyc_record.verification_type = id_type
    db.commit()
    
    return {
        "success": True,
        "extracted_data": result["data"],
        "quality": result["quality"],
        "temp_id_url": identity_image_url(id_url),
        "cropped_id_url": result.get("cropped_id_url", id_url),
        "autocrop_succeeded": result.get("autocrop_succeeded", False)
    }


@router.post("/{booking_id}/upload-id")
async def upload_id(
    booking_id: int,
    id_type: str = Form(...),
    id_number: str = Form(...),
    first_name: str = Form(None),
    middle_name: str = Form(None),
    last_name: str = Form(None),
    dob: str = Form(None),
    address: str = Form(None),
    id_address_extracted: str = Form(None),
    id_document: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Fintech Attempt Limiter
    if current_user.kyc_attempts >= 3:
        # Check if they already have an IdentityVerification record to block
        kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).order_by(models.IdentityVerification.created_at.desc(), models.IdentityVerification.id.desc()).first()
        if kyc_record:
            kyc_record.verification_status = "blocked"
            kyc_record.failure_reason = "Maximum KYC attempts (3) reached. Please contact support."
        else:
            # Create a blocked record if none exists
            kyc_record = models.IdentityVerification(
                user_id=current_user.id,
                verification_status="blocked",
                failure_reason="Maximum KYC attempts (3) reached. Please contact support.",
                document_url="N/A",
                selfie_url="N/A"
            )
            db.add(kyc_record)
        
        db.commit()
        raise HTTPException(status_code=403, detail="Maximum KYC attempts reached. Your account has been blocked for verification. Please contact support.")

    content = await id_document.read(MAX_IDENTITY_IMAGE_BYTES + 1)
    try:
        validate_identity_image(content, id_document.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Only a valid, decodable image consumes a KYC attempt.
    current_user.kyc_attempts += 1
    id_url = store_identity_image(content, id_document.filename or "")


    # Create/Update Verification Record
    kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).order_by(models.IdentityVerification.created_at.desc(), models.IdentityVerification.id.desc()).first()
    if not kyc_record or kyc_record.verification_status in ['VERIFIED', 'EXPIRED', 'rejected', 'blocked', 'verified']:
        kyc_record = models.IdentityVerification(user_id=current_user.id, booking_id=booking_id)
        db.add(kyc_record)
    else:
        kyc_record.booking_id = booking_id
    
    # Check if the submitted name matches the registered customer's name
    reg_name_parts = [current_user.first_name]
    if current_user.middle_name: reg_name_parts.append(current_user.middle_name)
    reg_name_parts.append(current_user.last_name)
    user_full_name = " ".join(reg_name_parts)
    
    submitted_full_name = f"{first_name or ''} {middle_name + ' ' if middle_name else ''}{last_name or ''}".strip()
    
    submitted_name_matched = verification_service.match_name(
        user_full_name,
        submitted_full_name,
        last_name,
        first_name,
        middle_name,
        user_full_name
    )
    
    if not submitted_name_matched:
        delete_identity_image(id_url)
        kyc_record.verification_status = "failed"
        kyc_record.failure_reason = "Name Mismatch | Ang pangalan sa iyong in-upload na ID ay hindi tugma sa iyong registered name."
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Identity Verification Failed | Ang pangalan sa iyong in-upload na ID ay hindi tugma sa iyong registered name. Mangyaring i-upload ang sarili mong valid ID."
        )

    # Validate DOB
    if current_user.dob and dob:
        from datetime import datetime
        try:
            submitted_dob_obj = datetime.strptime(dob, '%Y-%m-%d').date()
            if submitted_dob_obj != current_user.dob:
                delete_identity_image(id_url)
                kyc_record.verification_status = "failed"
                kyc_record.failure_reason = "DOB Mismatch | The date of birth on your ID does not match the date of birth registered on your account."
                db.commit()
                raise HTTPException(
                    status_code=400,
                    detail="Identity Verification Failed | The date of birth on your ID does not match the date of birth registered on your account. Please review your information."
                )
            
            # Age Calculation from verified ID DOB
            import math
            age = (datetime.now().date() - submitted_dob_obj).days / 365.2425
            if age < 18:
                delete_identity_image(id_url)
                kyc_record.verification_status = "blocked"
                kyc_record.failure_reason = "Age Eligibility Failed | Based on the information extracted from your ID, you do not meet the minimum age requirement of 18 years old."
                current_user.kyc_attempts = 3 # Max out attempts to lock the verification
                db.commit()
                raise HTTPException(
                    status_code=400,
                    detail="Booking unavailable | Based on the information extracted from your ID, you do not meet the minimum age requirement of 18 years old."
                )
        except ValueError:
            pass # Ignore invalid date formats

    kyc_record.document_url = id_url
    kyc_record.id_number = id_number
    kyc_record.verification_type = id_type
    
    # Update Booking specific address fields
    booking.id_address = id_address_extracted
    booking.current_address = address
    
    # Update OCR record if it exists
    ocr_record = db.query(models.OCRVerification).filter(models.OCRVerification.user_id == current_user.id).first()
    if not ocr_record:
        ocr_record = models.OCRVerification(user_id=current_user.id)
        db.add(ocr_record)
    
    ocr_record.full_name = f"{first_name} {middle_name + ' ' if middle_name else ''}{last_name}".strip()
    ocr_record.id_address_extracted = id_address_extracted
    try:
        ocr_record.birthdate = datetime.strptime(dob, '%Y-%m-%d').date()
    except:
        pass
    
    db.commit() 

    # --- Run OCR Matching to populate ocr_data (but NEVER auto-reject or block) ---
    print(f"[KYC] Running ID document matching for User {current_user.id} to save data...")
    # Compare OCR output with the account as it existed before this request.
    # KYC cannot be used to overwrite account identity fields.
    full_name = user_full_name
    account_dob = current_user.dob.strftime('%Y-%m-%d') if current_user.dob else None
    account_address = current_user.address or None

    id_result = await verification_service.verify_id_document(
        id_url, 
        full_name, 
        id_number, 
        id_type,
        db=db,
        user_id=current_user.id,
        dob=account_dob,
        address=account_address
    )
    
    if id_result.get("status") in ["rejected", "mismatched", "error"]:
        delete_identity_image(id_url)
        kyc_record.verification_status = "failed"
        kyc_record.failure_reason = id_result.get("failure_reason") or "ID document could not be verified."
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Identity Verification Failed | {kyc_record.failure_reason}"
        )

    if id_result.get("status") == "needs_review":
        ocr_data = id_result.get("ocr_data") or {}
        extracted_fields = ocr_data.get("fields") if isinstance(ocr_data, dict) else None
        if (not extracted_fields or id_result.get("name_matched") is False
                or id_result.get("id_number_matched") is False):
            delete_identity_image(id_url)
            kyc_record.verification_status = "failed"
            kyc_record.ocr_status = "failed"
            kyc_record.failure_reason = "We could not verify the extracted ID details. Please check the information and upload a clear ID image again."
            db.commit()
            raise HTTPException(status_code=400, detail=kyc_record.failure_reason)

        # Structured OCR and the key identity fields matched. Move directly to
        # liveness; do not stop the customer at a manual-review screen.
        kyc_record.ocr_data = ocr_data
        kyc_record.ocr_status = "passed"
        kyc_record.verification_status = "pending_liveliness"
        kyc_record.failure_reason = None
        db.commit()
        return {"success": True, "status": "pending_liveliness",
                "message": "ID details were extracted and saved. Proceeding to liveness detection."}

    if id_result.get("name_matched") == False:
        ocr_data = id_result.get("ocr_data", {})
        ocr_first = ocr_data.get("first_name", "") or ocr_data.get("given_names", "")
        ocr_last = ocr_data.get("last_name", "")
        
        # Resolve dict values if needed
        if isinstance(ocr_first, dict): ocr_first = ocr_first.get("value", "")
        if isinstance(ocr_last, dict): ocr_last = ocr_last.get("value", "")
        
        if not str(ocr_first).strip() and not str(ocr_last).strip():
            delete_identity_image(id_url)
            kyc_record.verification_status = "failed"
            kyc_record.failure_reason = "Extraction Error | Could not read your ID. Please make sure the photo is clear and not blurry."
            db.commit()
            raise HTTPException(
                status_code=400,
                detail=kyc_record.failure_reason
            )
            
        delete_identity_image(id_url)
        kyc_record.verification_status = "failed"
        kyc_record.failure_reason = "Identity Verification Failed | The name on your ID does not match your registered name. Please upload your own valid ID."
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=kyc_record.failure_reason
        )
        
    # Never send an unreadable ID to manual review at this stage. If OCR did not
    # extract fields, ask the customer to retry; successful extraction continues
    # straight to liveness below.
    ocr_data = id_result.get("ocr_data", {})
    if not ocr_data or not isinstance(ocr_data, dict) or not ocr_data.get("fields"):
        delete_identity_image(id_url)
        kyc_record.ocr_data = {}
        kyc_record.ocr_status = "failed"
        kyc_record.verification_status = "failed"
        kyc_record.failure_reason = "Extraction Error | Could not read the required ID details. Please upload a clear, well-lit image and try again."
        db.commit()
        raise HTTPException(status_code=400, detail=kyc_record.failure_reason)
    
    kyc_record.ocr_data = ocr_data
    kyc_record.ocr_status = "passed"
    kyc_record.verification_status = "pending_liveliness"
    kyc_record.failure_reason = None
    db.commit()

    return {"success": True, "message": "ID details saved successfully. Proceeding to liveness detection."}

@router.post("/{booking_id}/kyc/session/init")
async def init_kyc_session(
    booking_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Create a booking-bound liveness attempt for the authenticated customer."""
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking or booking.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    kyc_record = db.query(models.IdentityVerification).filter(
        models.IdentityVerification.user_id == current_user.id,
        models.IdentityVerification.booking_id == booking_id
    ).order_by(models.IdentityVerification.created_at.desc(), models.IdentityVerification.id.desc()).first()
    if not kyc_record or kyc_record.verification_status != "pending_liveliness":
        raise HTTPException(status_code=400, detail="ID verification is not ready for liveness verification.")

    session = db.query(models.VerificationSession).filter(
        models.VerificationSession.user_id == current_user.id
    ).order_by(models.VerificationSession.created_at.desc()).first()
    session_data = (session.verification_result or {}) if session else {}
    prior_face_audit_count = int(session_data.get("face_obstruction_audit_count", 0) or 0)
    if session and session.status == "processing" and session_data.get("booking_id") == booking_id:
        raise HTTPException(status_code=409, detail="Verification is already processing.")
    if (not session or session.status != "pending_liveness"
            or session_data.get("booking_id") != booking_id):
        session = models.VerificationSession(user_id=current_user.id)
        db.add(session)
        db.commit()
        db.refresh(session)

    challenges = ["blink"]
    session.status = "pending_liveness"
    session.created_at = datetime.now(timezone.utc)
    session.liveness_score = 0.0
    session.anti_spoof_score = 0.0
    session.face_match_score = 0.0
    session_token = secrets.token_urlsafe(32)
    session.verification_result = {
        "assigned_challenges": challenges,
        "booking_id": booking_id,
        "session_token": session_token,
        "face_obstruction_audit_count": prior_face_audit_count,
    }

    db.commit()
    return {
        "success": True,
        "session_id": session.id,
        "session_token": session_token,
        "challenges": challenges
    }


@router.post("/{booking_id}/verify-full")
async def verify_full(
    booking_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    selfies: list[UploadFile] = File(...),
    completed_challenges: str = Form(None), # e.g. "blink,smile,turn_left"
    session_token: str = Form(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking or booking.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    kyc_record = db.query(models.IdentityVerification).filter(
        models.IdentityVerification.user_id == current_user.id,
        models.IdentityVerification.booking_id == booking_id
    ).order_by(models.IdentityVerification.created_at.desc(), models.IdentityVerification.id.desc()).first()
    if not kyc_record or kyc_record.verification_status != "pending_liveliness":
        raise HTTPException(status_code=400, detail="KYC process not initialized or blocked.")

    session = db.query(models.VerificationSession).filter(
        models.VerificationSession.user_id == current_user.id
    ).order_by(models.VerificationSession.created_at.desc()).with_for_update().first()
    if not session:
        raise HTTPException(status_code=400, detail="Liveness session not initialized. Please call init first.")

    session_data = session.verification_result or {}
    stored_token = session_data.get("session_token", "")
    session_created_at = session.created_at
    if session_created_at and session_created_at.tzinfo is None:
        session_created_at = session_created_at.replace(tzinfo=timezone.utc)
    session_expired = (
        not session_created_at
        or datetime.now(timezone.utc) - session_created_at > timedelta(minutes=10)
    )
    if (session.status != "pending_liveness"
            or session_data.get("booking_id") != booking_id
            or session_expired
            or not stored_token
            or not hmac.compare_digest(stored_token, session_token)):
        raise HTTPException(status_code=409, detail="Verification session is invalid or expired. Please restart verification.")

    attempt_window_start = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_attempts = db.query(func.count(models.AuditLog.id)).filter(
        models.AuditLog.user_id == current_user.id,
        models.AuditLog.action == "kyc_verification",
        models.AuditLog.timestamp >= attempt_window_start,
    ).scalar() or 0
    if recent_attempts >= 3:
        review_reason = "Verification Attempts Exceeded | You've reached the maximum number of verification attempts. Please wait or wait for manual review."
        kyc_record.verification_status = "pending_manual_review"
        kyc_record.failure_reason = review_reason
        session.status = "pending_manual_review"
        session.verification_result = {**session_data, "failure_reason": review_reason}
        db.commit()
        return {
            "status": "pending_manual_review",
            "message": "Verification requires manual review."
        }

    expected_names = ["selfie_open_1.jpg", "selfie_closed.jpg", "selfie_open_2.jpg"]
    if len(selfies) != len(expected_names):
        raise HTTPException(status_code=400, detail="Exactly three blink verification frames are required.")

    from PIL import Image
    validated_contents = []
    for index, file in enumerate(selfies):
        if (file.filename or "").lower() != expected_names[index]:
            raise HTTPException(status_code=400, detail="Blink verification frames are missing or out of order.")
        content = await file.read()
        file_error = validate_file_type_and_size(content, file.filename)
        if file_error:
            raise HTTPException(status_code=400, detail=file_error)
        try:
            with Image.open(io.BytesIO(content)) as image:
                if image.format not in {"JPEG", "PNG"} or image.width < 160 or image.height < 160:
                    raise ValueError("Unsupported image dimensions or format")
                image.verify()
        except Exception:
            raise HTTPException(status_code=400, detail="A verification frame is not a valid image.")
        validated_contents.append(content)

    selfie_urls = []
    for content in validated_contents:
        selfie_urls.append(store_identity_image(content, file.filename or "selfie.jpg"))

    if len(selfie_urls) != 3:
        raise HTTPException(status_code=502, detail="Verification frames could not be securely uploaded. Please try again.")


    kyc_record.selfie_url = selfie_urls[0]
    if len(selfie_urls) > 1: kyc_record.selfie_2_url = selfie_urls[1]
    if len(selfie_urls) > 2: kyc_record.selfie_3_url = selfie_urls[2]
    kyc_record.ip_address = request.client.host if request.client else None
    kyc_record.verification_status = "processing"
    
    session.status = "processing"
    db.commit()

    # Parse completed and assigned challenges
    completed_list = [c.strip() for c in completed_challenges.split(",") if c.strip()] if completed_challenges else []
    assigned_list = session.verification_result.get("assigned_challenges", []) if session.verification_result else []

    dob_str = current_user.dob.strftime('%Y-%m-%d') if current_user.dob else None
    
    full_name_parts = [current_user.first_name]
    if current_user.middle_name: full_name_parts.append(current_user.middle_name)
    full_name_parts.append(current_user.last_name)
    full_name = " ".join(full_name_parts)

    background_tasks.add_task(
        process_kyc_background,
        current_user.id,
        booking_id,
        kyc_record.id,
        session.id,
        kyc_record.document_url,
        selfie_urls,
        full_name,
        kyc_record.id_number,
        kyc_record.verification_type,
        dob_str,
        current_user.address,
        completed_list,
        assigned_list
    )

    return {"status": "processing", "message": "Verification started. Please wait."}


@router.post("/{booking_id}/kyc/obstruction-check")
async def check_live_face_obstruction(
    booking_id: int,
    frame: UploadFile = File(...),
    session_token: str = Form(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Check a transient camera frame before the alignment guide may turn green."""
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking or booking.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    session = db.query(models.VerificationSession).filter(
        models.VerificationSession.user_id == current_user.id
    ).order_by(models.VerificationSession.created_at.desc()).with_for_update().first()
    if not session:
        raise HTTPException(status_code=409, detail="Verification session is invalid or expired.")
    session_data = session.verification_result or {}
    stored_token = session_data.get("session_token", "")
    session_created_at = session.created_at
    if session_created_at and session_created_at.tzinfo is None:
        session_created_at = session_created_at.replace(tzinfo=timezone.utc)
    expired = (
        not session_created_at
        or datetime.now(timezone.utc) - session_created_at > timedelta(minutes=10)
    )
    if (session.status != "pending_liveness"
            or session_data.get("booking_id") != booking_id
            or expired
            or not stored_token
            or not hmac.compare_digest(stored_token, session_token)):
        raise HTTPException(status_code=409, detail="Verification session is invalid or expired.")

    content = await frame.read(512 * 1024 + 1)
    if len(content) > 512 * 1024:
        raise HTTPException(status_code=413, detail="Camera frame is too large.")
    if not content or (frame.content_type or "").lower() not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="A valid camera image is required.")
    from PIL import Image
    try:
        with Image.open(io.BytesIO(content)) as image:
            if (image.format not in {"JPEG", "PNG"}
                    or image.width < 160 or image.height < 120
                    or image.width > 4096 or image.height > 4096
                    or image.width * image.height > 16_000_000):
                raise ValueError("Unsupported image size or format")
            image.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="A valid camera image is required.")

    now = datetime.now(timezone.utc)
    last_check = session_data.get("face_obstruction_checked_at")
    if last_check:
        try:
            last_check_at = datetime.fromisoformat(last_check)
            if last_check_at.tzinfo is None:
                last_check_at = last_check_at.replace(tzinfo=timezone.utc)
            if now - last_check_at < timedelta(seconds=2):
                cached = session_data.get("face_obstruction_result")
                if isinstance(cached, dict):
                    return {**cached, "cached": True}
        except (TypeError, ValueError):
            pass

    audit_count = int(session_data.get("face_obstruction_audit_count", 0) or 0)
    if audit_count >= 10:
        return {
            "status": "uncertain",
            "title": "Face Check Unavailable",
            "message": "We couldn't confirm face visibility. Your verification may require manual review.",
        }

    session_data = {
        **session_data,
        "face_obstruction_checked_at": now.isoformat(),
        "face_obstruction_result": {
            "status": "checking",
            "title": "Checking face visibility",
            "message": "Please wait while we check your face.",
        },
        "face_obstruction_audit_count": audit_count + 1,
    }
    session.verification_result = session_data
    db.commit()

    session_id = session.id
    try:
        audit_result = await verification_service.audit_live_face_obstruction(content)
    except Exception:
        audit_result = {
            "status": "uncertain",
            "title": "Face Check Unavailable",
            "message": "We couldn't check your face right now. This verification may require manual review.",
        }

    session = db.query(models.VerificationSession).filter(
        models.VerificationSession.id == session_id,
        models.VerificationSession.user_id == current_user.id,
    ).with_for_update().first()
    latest_data = (session.verification_result or {}) if session else {}
    if (not session or session.status != "pending_liveness"
            or latest_data.get("booking_id") != booking_id
            or not hmac.compare_digest(latest_data.get("session_token", ""), session_token)):
        return {
            "status": "uncertain",
            "title": "Face Check Unavailable",
            "message": "Please restart identity verification.",
        }
    session.verification_result = {
        **latest_data,
        "face_obstruction_result": audit_result,
    }
    db.commit()
    return audit_result


async def process_kyc_background(user_id, booking_id, kyc_record_id, session_id, id_path, selfie_paths, full_name, id_number, id_type, dob, address, completed_challenges, assigned_challenges):
    # This simulates the Celery worker / Background task logic
    db = database.SessionLocal()
    try:
        print(f"\n[KYC BACKGROUND] Starting verification for User {user_id}...")
        user = db.query(models.User).get(user_id)
        booking = db.query(models.Booking).filter(
            models.Booking.id == booking_id,
            models.Booking.user_id == user_id
        ).first()
        kyc_record = db.query(models.IdentityVerification).filter(
            models.IdentityVerification.id == kyc_record_id,
            models.IdentityVerification.user_id == user_id,
            models.IdentityVerification.booking_id == booking_id
        ).first()
        session = db.query(models.VerificationSession).filter(
            models.VerificationSession.id == session_id,
            models.VerificationSession.user_id == user_id
        ).first()
        if not user or not booking or not kyc_record or not session:
            raise RuntimeError("Verification attempt records are no longer valid.")
        
        # Simulate processing time
        await asyncio.sleep(0.5)
        result = await verification_service.verify_identity_v2(
            id_path, selfie_paths, full_name, id_number, id_type, db, user_id, dob, address,
            completed_challenges=completed_challenges,
            assigned_challenges=assigned_challenges
        )
        
        status = result.get("status")
        print(f"[KYC BACKGROUND] Verification Service result status: {status}")
        
        if status == "verified":
            print("[KYC BACKGROUND] Auto-verification passed. Customer is verified.")
        
        # Update VerificationSession
        if session:
            session.status = status
            session.liveness_score = float(result.get("liveness_score", 0.0))
            session.anti_spoof_score = float(result.get("anti_spoof_score", 0.0))
            session.face_match_score = float(result.get("face_match_score", 0.0))
            # Merge dictionary
            current_res = session.verification_result or {}
            # Keep the session payload limited to routing and customer-safe state.
            # Numeric scores and extracted ID data already belong in their restricted
            # verification records and must not be duplicated in a JSON status blob.
            session.verification_result = {
                "booking_id": booking_id,
                "assigned_challenges": current_res.get("assigned_challenges", []),
                "failure_reason": result.get("failure_reason"),
            }
            db.commit()
            
        # Update User & IdentityVerification records if verified
        if status == "verified":
            user.is_verified = True
            user.is_kyc_complete = True
            if kyc_record:
                kyc_record.verification_status = "VERIFIED"
                kyc_record.verified_at = func.now()
                kyc_record.failure_reason = None
                
                # Calculate expiry: 6 months from now
                from datetime import datetime
                from dateutil.relativedelta import relativedelta
                valid_until = datetime.now() + relativedelta(months=6)
                
                # Check if ID expires earlier
                if kyc_record.id_expiry_date:
                    if isinstance(kyc_record.id_expiry_date, str):
                        try:
                            id_expiry = datetime.strptime(kyc_record.id_expiry_date, '%Y-%m-%d').date()
                        except:
                            id_expiry = kyc_record.id_expiry_date
                    else:
                        id_expiry = kyc_record.id_expiry_date
                        
                    if id_expiry < valid_until.date():
                        valid_until = datetime.combine(id_expiry, datetime.min.time())
                
                kyc_record.verification_valid_until = valid_until
                
            db.query(models.Booking).filter(
                models.Booking.id == booking_id,
                models.Booking.user_id == user_id
            ).update({"ocr_verified": True, "liveness_verified": True})
            
            # Send Notification
            await NotificationService.notify_status_update(
                db, user_id, 
                "Identity Approved!", 
                f"Your identity has been verified. You may now proceed with your booking.",
                f"/bookings/step/quotation/{booking.id}",
                "kyc_update"
            )
            
        elif status == "pending_manual_review":
            if kyc_record:
                kyc_record.verification_status = "pending_manual_review"
                kyc_record.failure_reason = result.get("failure_reason") or "Identity Verification Pending | Your verification is pending evaluation by the system administrator."
                
            # Send Notification for pending evaluation
            await NotificationService.notify_status_update(
                db, user_id, 
                "Verification Pending", 
                f"Your identity verification is pending manual evaluation by the system administrator.",
                f"/bookings/step/kyc/{booking.id}",
                "kyc_update"
            )
                
        elif result.get("status") == "liveliness_failed":
            if kyc_record:
                kyc_record.verification_status = "liveliness_failed"
                kyc_record.failure_reason = result.get("failure_reason")
                
        elif result.get("status") == "rejected":
            if kyc_record:
                kyc_record.verification_status = "rejected"
                kyc_record.failure_reason = result.get("failure_reason")
            user.is_verified = False
            
            # Send Notification
            await NotificationService.notify_status_update(
                db, user_id, 
                "Identity Action Required", 
                f"Your identity verification was rejected. Reason: {result.get('failure_reason')}",
                f"/bookings/step/kyc/{booking.id}",
                "kyc_update"
            )
            
        if kyc_record:
            kyc_record.fraud_score = result.get("fraud_score", 0)
            kyc_record.match_score = result.get("face_match_confidence", 0.0)
            kyc_record.face_detected = result.get("liveness_score", 0.0) > 0 or result.get("face_match_confidence", 0.0) > 0
            
            # Conditionally save ocr_data only if result has valid ocr_data with fields
            new_ocr = result.get("ocr_data")
            if new_ocr and isinstance(new_ocr, dict) and new_ocr.get("fields"):
                new_ocr = {
                    key: value for key, value in new_ocr.items()
                    if key not in {"raw_text", "raw_ocr", "extracted_text_preview"}
                }
                kyc_record.ocr_data = new_ocr
            # Fallback in case ocr_data is currently None in the DB (initialize as empty dict)
            elif kyc_record.ocr_data is None:
                kyc_record.ocr_data = {}
                
            kyc_record.id_detected = result.get("ocr_match", False) or (isinstance(kyc_record.ocr_data, dict) and kyc_record.ocr_data.get("full_name") is not None)
            if result.get("status") == "verified":
                kyc_record.liveness_status = "passed"
            elif result.get("status") == "pending_manual_review":
                kyc_record.liveness_status = "needs_review"
            else:
                kyc_record.liveness_status = "failed"
            
        # Log to Audit
        audit = models.AuditLog(
            user_id=user_id,
            action="kyc_verification",
            old_status="processing",
            new_status=result.get("status", "failed"),
        )
        db.add(audit)
        db.commit()
        
        # Real-time WebSocket Notification
        try:
            await manager.broadcast_to_user(user_id, {
                "type": "kyc_update",
                "status": result.get("status"),
                "reason": result.get("failure_reason")
            })
        except Exception as e:
            print(f"[KYC BACKGROUND WS ERROR] {e}")
            
    except Exception as e:
        print(f"[KYC BACKGROUND ERROR] {e}")
        traceback.print_exc()
        try:
            # Mark session and KYC record as failed so the frontend does not get stuck
            session = db.query(models.VerificationSession).filter(
                models.VerificationSession.id == session_id,
                models.VerificationSession.user_id == user_id
            ).first()
            if session:
                session.status = "failed"
            kyc_record = db.query(models.IdentityVerification).filter(
                models.IdentityVerification.id == kyc_record_id,
                models.IdentityVerification.user_id == user_id,
                models.IdentityVerification.booking_id == booking_id
            ).first()
            
            # Map exception / system failure to professional connection/interruption message
            interruption_msg = "Verification Interrupted | The verification process was interrupted due to a connection issue. Please check your internet connection and try again."
            
            if kyc_record:
                kyc_record.verification_status = "failed"
                kyc_record.failure_reason = interruption_msg
            db.commit()
            
            # Broadcast to WebSocket
            await manager.broadcast_to_user(user_id, {
                "type": "kyc_update",
                "status": "failed",
                "reason": interruption_msg
            })
        except Exception as db_err:
            print(f"[KYC BACKGROUND DB ERROR IN EXCEPT] {db_err}")
            
    finally:
        db.close()

@router.post("/kyc/reset")
async def reset_kyc_status(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).order_by(models.IdentityVerification.created_at.desc(), models.IdentityVerification.id.desc()).first()
    if kyc_record:
        kyc_record.verification_status = "pending"
        kyc_record.failure_reason = None
        
    # Also reset any active VerificationSession status to avoid client-side polling hang
    session = db.query(models.VerificationSession).filter(models.VerificationSession.user_id == current_user.id).order_by(models.VerificationSession.created_at.desc()).first()
    if session:
        session.status = "failed"
        
    db.commit()
    return {"success": True}

@router.post("/kyc/reset-liveness")
async def reset_liveness_status(
    booking_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Reset only this customer's failed liveness attempt for the selected booking."""
    kyc_record = db.query(models.IdentityVerification).filter(
        models.IdentityVerification.user_id == current_user.id,
        models.IdentityVerification.booking_id == booking_id
    ).order_by(models.IdentityVerification.created_at.desc(), models.IdentityVerification.id.desc()).first()
    if kyc_record and kyc_record.verification_status == "liveliness_failed":
        kyc_record.verification_status = "pending_liveliness"
        kyc_record.failure_reason = None
        kyc_record.liveness_status = None
        db.commit()
    return {"success": True}

@router.get("/{booking_id}/status")
async def get_kyc_status(
    booking_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking or booking.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    sessions = db.query(models.VerificationSession).filter(
        models.VerificationSession.user_id == current_user.id
    ).order_by(models.VerificationSession.created_at.desc()).all()
    session = next((candidate for candidate in sessions
                    if (candidate.verification_result or {}).get("booking_id") == booking_id), None)
    kyc_record = db.query(models.IdentityVerification).filter(
        models.IdentityVerification.user_id == current_user.id,
        models.IdentityVerification.booking_id == booking_id
    ).order_by(models.IdentityVerification.created_at.desc(), models.IdentityVerification.id.desc()).first()

    # Manual approval is account-level and may not update an older booking's
    # verification session. Treat the completed account verification as final
    # so the KYC page can show success and advance to quotation.
    if current_user.is_verified and current_user.is_kyc_complete:
        return {"status": "verified"}
    
    # If blocked or rejected on the main compliance record, yield that
    if kyc_record and kyc_record.verification_status in ["blocked", "rejected"]:
        return {
            "status": kyc_record.verification_status,
            "reason": kyc_record.failure_reason
        }
        
    if session:
        return {
            "status": session.status,
            "reason": session.verification_result.get("failure_reason") if session.verification_result else None
        }
        
    if kyc_record:
        return {
            "status": kyc_record.verification_status,
            "reason": kyc_record.failure_reason
        }
        
    return {"status": "pending"}

@router.get("/kyc/private/{filename}")
async def view_private_kyc_document(
    filename: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Serve encrypted identity files only to their owner or an administrator."""
    try:
        safe_filename = private_identity_filename(f"/api/bookings/kyc/private/{filename}")
    except ValueError:
        raise HTTPException(status_code=404, detail="Document not found.")
    reference = f"/api/bookings/kyc/private/{safe_filename}"

    record = db.query(models.IdentityVerification).filter(or_(
        models.IdentityVerification.document_url == reference,
        models.IdentityVerification.document_back_url == reference,
        models.IdentityVerification.selfie_url == reference,
        models.IdentityVerification.selfie_2_url == reference,
        models.IdentityVerification.selfie_3_url == reference,
    )).first()
    if not record or (current_user.role != "admin" and record.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        image_data = load_identity_image(reference)
    except (ValueError, OSError):
        raise HTTPException(status_code=404, detail="Document not found.")

    mime_type = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(os.path.splitext(filename)[1].lower(), "application/octet-stream")
    return Response(
        content=image_data,
        media_type=mime_type,
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'inline; filename="identity{os.path.splitext(filename)[1].lower()}"',
        },
    )


@router.get("/kyc/view/{filename}")
async def view_kyc_document(
    filename: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Secure proxy to decrypt and view KYC documents."""
    if filename != os.path.basename(filename.replace("\\", "/")) or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=404, detail="Document not found.")
    # RBAC: Only admin, the document owner, or their caterer can view
    is_admin = current_user.role == "admin"
    is_owner = (
        filename.startswith(f"user_{current_user.id}_") or
        filename.startswith(f"temp_ocr_{current_user.id}_") or
        filename.startswith(f"cropped_temp_ocr_{current_user.id}_") or
        filename.startswith(f"cropped_user_{current_user.id}_") or
        f"_{current_user.id}_" in filename or
        filename.startswith(f"selfie_{current_user.id}_")
    )
    
    # Check IdentityVerification record for ownership (handles registration-uploaded files)
    if not is_owner:
        file_url = f"/static/uploads/verification/{filename}"
        proxy_url = f"/api/bookings/kyc/view/{filename}"
        identity = db.query(models.IdentityVerification).filter(
            models.IdentityVerification.user_id == current_user.id
        ).order_by(models.IdentityVerification.created_at.desc()).first()
        if identity:
            identity_urls = [identity.document_url, identity.selfie_url,
                           getattr(identity, 'selfie_2_url', None), getattr(identity, 'selfie_3_url', None)]
            if file_url in identity_urls or proxy_url in identity_urls:
                is_owner = True
    
    if current_user.role == "caterer" and current_user.caterer_profile:
        file_url = f"/static/uploads/verification/{filename}"
        proxy_url = f"/api/bookings/kyc/view/{filename}"
        profile = current_user.caterer_profile
        identity = current_user.identity_verification
        doc_urls = [
            profile.permit_url, profile.dti_url, profile.bir_url, 
            profile.mayors_permit_url, profile.gov_id_url
        ]
        if identity:
            doc_urls.extend([identity.document_url, identity.document_back_url, identity.selfie_url])
            
        if file_url in doc_urls or proxy_url in doc_urls:
            is_owner = True
    
    # Caterers are no longer authorized to view customer IDs (Platform handled)
    is_caterer_authorized = False

    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Unauthorized access to this document.")

    path = os.path.join(UPLOAD_DIR, filename)
    file_data = None
    if os.path.exists(path):
        with open(path, "rb") as f:
            file_data = f.read()
    else:
        # Check valid_ids or alternate directories or Cloudinary fallback
        try:
            file_data = verification_service._load_image_bytes(filename)
        except Exception:
            raise HTTPException(status_code=404, detail="Document not found.")
    
    if not file_data:
        raise HTTPException(status_code=404, detail="Document is empty or not found.")
    
    # Infer MIME type from the original filename extension
    ext = os.path.splitext(filename)[1].lower()
    mime_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
        ".pdf": "application/pdf", ".enc": "image/jpeg"
    }
    media_type = mime_map.get(ext, "image/jpeg")
    
    # Try decryption first (most files are encrypted)
    try:
        decrypted_data = decrypt_data(file_data)
        return Response(content=decrypted_data, media_type=media_type)
    except Exception as e:
        # Decryption failed — check if the file is actually a valid raw image
        # (uploaded before encryption was enabled, or key has changed)
        image_signatures = {
            b'\xff\xd8\xff': "image/jpeg",      # JPEG
            b'\x89PNG': "image/png",             # PNG
            b'RIFF': "image/webp",               # WebP
            b'%PDF': "application/pdf",          # PDF
        }
        for sig, detected_mime in image_signatures.items():
            if file_data[:len(sig)] == sig:
                print("[KYC VIEW] A legacy verification file was read without encryption.")
                return Response(content=file_data, media_type=detected_mime)
        
        # If not matched above, we can fallback to standard checking
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = "application/octet-stream"
            
        if (file_data.startswith(b'\xff\xd8') or 
            file_data.startswith(b'\x89PNG') or 
            file_data.startswith(b'GIF8') or 
            file_data.startswith(b'RIFF')):
            return Response(content=file_data, media_type=mime_type)
        
        # Neither valid decryption nor valid raw image — file is truly corrupted
        print("[KYC VIEW ERROR] Unable to decrypt or read a verification document.")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail="Document cannot be displayed. The file may be corrupted or the encryption key has changed. Please ask the user to re-upload."
        )
