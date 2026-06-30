from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..db import database, models
from ..core import security as auth
from ..services.verification import verification_service
from ..core.encryption import encrypt_data, decrypt_data
from ..core.utils import validate_file_type_and_size
from fastapi.responses import Response
from ..services.notification import NotificationService
from ..services.realtime import manager
import os
import uuid
import shutil
import io
import asyncio
import time
import traceback
import random

# Security Constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_MIME_TYPES = ["image/jpeg", "image/png"]

router = APIRouter(prefix="/api/bookings", tags=["kyc"])

UPLOAD_DIR = "app/static/uploads/verification"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/test-extract")
async def test_extract():
    import glob
    files = glob.glob(os.path.join(UPLOAD_DIR, "temp_ocr_*.enc"))
    if not files:
        return {"error": "No temp_ocr files found in verification upload directory."}
    # Sort by modification time to get the latest file
    latest_file = max(files, key=os.path.getmtime)
    filename = os.path.basename(latest_file)
    id_url = f"/api/bookings/kyc/view/{filename}"
    print(f"[TEST OCR] Extracting data from latest file: {latest_file} via {id_url}")
    result = await verification_service.extract_id_data(id_url, "PhilSys / PhilID")
    return {
        "file_tested": latest_file,
        "result": result
    }

@router.post("/extract-id")
async def extract_id(
    id_type: str = Form(...),
    id_document: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Endpoint for Section B: Extracts data from ID for the booking form."""
    content = await id_document.read()
    
    # 1. File Type Validation
    import os
    ext = os.path.splitext(id_document.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload JPG or PNG image only.")
    
    # 2. File Size Validation (Max 10MB)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File is too large. Maximum size is 10MB.")
    
    # Save file temporarily or permanently
    filename = f"temp_ocr_{current_user.id}_{uuid.uuid4()}.enc"
    path = os.path.join(UPLOAD_DIR, filename)
    encrypted_content = encrypt_data(content)
    with open(path, "wb") as f:
        f.write(encrypted_content)
    
    id_url = f"/api/bookings/kyc/view/{filename}"
    
    result = await verification_service.extract_id_data(id_url, id_type)
    
    if not result["success"]:
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
    
    # Log variables to ocr_debug.log to see why name matching failed
    try:
        with open("ocr_debug.log", "a", encoding="utf-8") as f:
            f.write(f"\n--- KYC MATCH DEBUG ---\n")
            f.write(f"current_user.id: {current_user.id}\n")
            f.write(f"current_user.first_name: {current_user.first_name!r}\n")
            f.write(f"current_user.middle_name: {current_user.middle_name!r}\n")
            f.write(f"current_user.last_name: {current_user.last_name!r}\n")
            f.write(f"user_full_name: {user_full_name!r}\n")
            f.write(f"ocr_full_name: {ocr_full_name!r}\n")
            f.write(f"ocr_first_name: {ocr_first_name!r}\n")
            f.write(f"ocr_middle_name: {ocr_middle_name!r}\n")
            f.write(f"ocr_last_name: {ocr_last_name!r}\n")
    except Exception as log_err:
        pass
        
    name_matched = verification_service.match_name(
        user_full_name,
        ocr_full_name,
        ocr_last_name,
        ocr_first_name,
        ocr_middle_name,
        raw_ocr
    )
    
    print(f"[KYC EXTRACT] Name matching - Registered: '{user_full_name}', Extracted: '{ocr_full_name}', Matched: {name_matched}")
    
    if not ocr_first_name.strip() and not ocr_last_name.strip():
        raise HTTPException(
            status_code=400,
            detail="Extraction Error | Could not read your ID. Please make sure the photo is clear and not blurry."
        )
        
    if not name_matched:
        debug_info = f"Registered: '{user_full_name}', OCR Extracted First: '{ocr_first_name}', Middle: '{ocr_middle_name}', Last: '{ocr_last_name}'"
        raise HTTPException(
            status_code=400,
            detail=f"Identity Verification Failed | The name on your ID does not match your registered name. Please upload your own valid ID.\n\n[DEBUG INFO]: {debug_info}"
        )
    
    # Update/Create verification record as pending_confirmation
    kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).first()
    if not kyc_record:
        kyc_record = models.IdentityVerification(user_id=current_user.id)
        db.add(kyc_record)
    
    kyc_record.verification_status = "pending_confirmation"
    # Use cropped URL if auto-crop succeeded
    final_doc_url = result.get("cropped_id_url") if result.get("autocrop_succeeded") else id_url
    kyc_record.document_url = final_doc_url
    kyc_record.verification_type = id_type
    db.commit()
    
    return {
        "success": True,
        "extracted_data": result["data"],
        "quality": result["quality"],
        "temp_id_url": id_url,
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
    if not booking or (booking.user_id != current_user.id and current_user.role != 'admin'):
        raise HTTPException(status_code=404, detail="Booking not found")

    # Fintech Attempt Limiter (Temporary higher limit for testing)
    if current_user.kyc_attempts >= 100:
        # Check if they already have an IdentityVerification record to block
        kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).first()
        if kyc_record:
            kyc_record.verification_status = "blocked"
            kyc_record.failure_reason = "Maximum KYC attempts (3) reached."
        else:
            # Create a blocked record if none exists
            kyc_record = models.IdentityVerification(
                user_id=current_user.id,
                verification_status="blocked",
                failure_reason="Maximum KYC attempts (3) reached.",
                document_url="N/A",
                selfie_url="N/A"
            )
            db.add(kyc_record)
        
        db.commit()
        raise HTTPException(status_code=403, detail="Maximum KYC attempts reached. Your account has been blocked for verification.")

    # Increment attempts
    current_user.kyc_attempts += 1

    # Read file content
    content = await id_document.read()

    # 1. File Type Validation
    import os
    ext = os.path.splitext(id_document.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload JPG or PNG image only.")
    
    # 2. File Size Validation (Max 10MB)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File is too large. Maximum size is 10MB.")
    
    # Encrypt data
    encrypted_content = encrypt_data(content)

    # Save Encrypted File
    filename = f"user_{current_user.id}_id_{uuid.uuid4()}.enc"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(encrypted_content)
    
    id_url = f"/api/bookings/kyc/view/{filename}"

    # Create/Update Verification Record
    kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).first()
    if not kyc_record:
        kyc_record = models.IdentityVerification(user_id=current_user.id)
        db.add(kyc_record)
    
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
    
    print(f"[KYC UPLOAD] Submitted name matching - Registered: '{user_full_name}', Submitted: '{submitted_full_name}', Matched: {submitted_name_matched}")
    
    if not submitted_name_matched:
        raise HTTPException(
            status_code=400,
            detail="Identity Verification Failed | Ang pangalan sa iyong in-upload na ID ay hindi tugma sa iyong registered name. Mangyaring i-upload ang sarili mong valid ID."
        )

    # Update User Profile with provided KYC data if available
    if first_name: current_user.first_name = first_name
    if middle_name: current_user.middle_name = middle_name
    if last_name: current_user.last_name = last_name
    if address: 
        current_user.address = address
        booking.current_address = address
    
    if dob:
        try:
            from datetime import datetime
            current_user.dob = datetime.strptime(dob, '%Y-%m-%d').date()
        except Exception:
            pass # Ignore invalid date format if it was empty

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
    full_name_parts = [first_name]
    if middle_name: full_name_parts.append(middle_name)
    full_name_parts.append(last_name)
    full_name = " ".join(full_name_parts)

    id_result = await verification_service.verify_id_document(
        id_url, 
        full_name, 
        id_number, 
        id_type,
        db=db,
        user_id=current_user.id,
        dob=dob,
        address=address
    )
    
    if id_result.get("status") in ["rejected", "mismatched", "error"] and id_result.get("failure_reason"):
        raise HTTPException(
            status_code=400,
            detail=f"Identity Verification Failed | {id_result.get('failure_reason')}"
        )

    if id_result.get("name_matched") == False:
        ocr_data = id_result.get("ocr_data", {})
        ocr_first = ocr_data.get("first_name", "") or ocr_data.get("given_names", "")
        ocr_last = ocr_data.get("last_name", "")
        
        # Resolve dict values if needed
        if isinstance(ocr_first, dict): ocr_first = ocr_first.get("value", "")
        if isinstance(ocr_last, dict): ocr_last = ocr_last.get("value", "")
        
        if not str(ocr_first).strip() and not str(ocr_last).strip():
            raise HTTPException(
                status_code=400,
                detail="Extraction Error | Could not read your ID. Please make sure the photo is clear and not blurry."
            )
            
        raise HTTPException(
            status_code=400,
            detail="Identity Verification Failed | The name on your ID does not match your registered name. Please upload your own valid ID."
        )
        
    # Ensure ocr_data is populated even if verification service fails to extract it
    ocr_data = id_result.get("ocr_data", {})
    if not ocr_data or not isinstance(ocr_data, dict) or not ocr_data.get("fields"):
        fallback_fields = {
            "id_number": {"value": id_number, "confidence": 100},
            "last_name": {"value": last_name or "", "confidence": 100},
            "first_name": {"value": first_name or "", "confidence": 100},
            "middle_name": {"value": middle_name or "", "confidence": 100},
            "date_of_birth": {"value": dob or "", "confidence": 100},
            "address": {"value": address or "", "confidence": 100}
        }
        
        # Add ID type specific fields
        if id_type in ["PhilSys / PhilID", "PhilID (National ID)", "philsys", "PhilID"]:
            fallback_fields["given_names"] = {"value": first_name or "", "confidence": 100}
        elif id_type == "Driver's License":
            fallback_fields["license_number"] = {"value": id_number, "confidence": 100}
        elif id_type == "Passport":
            fallback_fields["passport_number"] = {"value": id_number, "confidence": 100}
            fallback_fields["given_names"] = {"value": first_name or "", "confidence": 100}

        ocr_data = {
            "id_type": id_type,
            "extraction_method": "manual_input",
            "document_type_detected": id_type,
            "confidence_score": 1.0,
            "face_visible": True,
            "fields": fallback_fields,
            "full_name": f"{first_name or ''} {middle_name + ' ' if middle_name else ''}{last_name or ''}".strip(),
            "id_number": id_number,
            "birth_date": dob,
            "address": address,
            "raw_text": f"MANUAL_FALLBACK: {first_name} {last_name} {id_number}"
        }
    
    kyc_record.ocr_data = ocr_data
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
    """Initializes/resets the liveness verification session with randomized challenges."""
    # Find existing session or create a new one
    session = db.query(models.VerificationSession).filter(models.VerificationSession.user_id == current_user.id).order_by(models.VerificationSession.created_at.desc()).first()
    
    if not session or session.status in ["verified", "rejected"]:
        session = models.VerificationSession(user_id=current_user.id)
        db.add(session)
        db.commit()
        db.refresh(session)
        
    # Use only eye-blink detection for liveness verification
    challenges = ["blink"]
    
    session.status = "pending_liveness"
    session.liveness_score = 0.0
    session.anti_spoof_score = 0.0
    session.face_match_score = 0.0
    session.verification_result = {"assigned_challenges": challenges}
    
    db.commit()
    return {
        "success": True,
        "session_id": session.id,
        "challenges": challenges
    }


@router.post("/{booking_id}/verify-full")
async def verify_full(
    booking_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    selfies: list[UploadFile] = File(...),
    completed_challenges: str = Form(None), # e.g. "blink,smile,turn_left"
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).first()
    if not kyc_record or kyc_record.verification_status == "blocked":
        raise HTTPException(status_code=400, detail="KYC process not initialized or blocked.")

    # Get active VerificationSession
    session = db.query(models.VerificationSession).filter(models.VerificationSession.user_id == current_user.id).order_by(models.VerificationSession.created_at.desc()).first()
    if not session:
        raise HTTPException(status_code=400, detail="Liveness session not initialized. Please call init first.")

    # Save selfie frames (Encrypted)
    selfie_urls = []
    for i, file in enumerate(selfies[:3]):
        content = await file.read()
        file_error = validate_file_type_and_size(content, file.filename)
        if file_error:
             continue # Skip invalid ones

        encrypted_content = encrypt_data(content)
        filename = f"user_{current_user.id}_selfie_{i+1}_{uuid.uuid4()}.enc"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as f:
            f.write(encrypted_content)
        selfie_urls.append(f"/api/bookings/kyc/view/{filename}")
    
    kyc_record.selfie_url = selfie_urls[0]
    if len(selfie_urls) > 1: kyc_record.selfie_2_url = selfie_urls[1]
    if len(selfie_urls) > 2: kyc_record.selfie_3_url = selfie_urls[2]
    kyc_record.ip_address = request.client.host
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


async def process_kyc_background(user_id, booking_id, id_path, selfie_paths, full_name, id_number, id_type, dob, address, completed_challenges, assigned_challenges):
    # This simulates the Celery worker / Background task logic
    db = database.SessionLocal()
    try:
        print(f"\n[KYC BACKGROUND] Starting verification for User {user_id}...")
        user = db.query(models.User).get(user_id)
        booking = db.query(models.Booking).get(booking_id)
        kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == user_id).first()
        session = db.query(models.VerificationSession).filter(models.VerificationSession.user_id == user_id).order_by(models.VerificationSession.created_at.desc()).first()
        
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        result = await verification_service.verify_identity_v2(
            id_path, selfie_paths, full_name, id_number, id_type, db, user_id, dob, address,
            completed_challenges=completed_challenges,
            assigned_challenges=assigned_challenges
        )
        
        print(f"[KYC BACKGROUND] Verification Service result status: {result.get('status')}")
        
        # Update VerificationSession
        if session:
            session.status = result.get("status", "failed")
            session.liveness_score = float(result.get("liveness_score", 0.0))
            session.anti_spoof_score = float(result.get("anti_spoof_score", 0.0))
            session.face_match_score = float(result.get("face_match_score", 0.0))
            # Merge dictionary
            current_res = session.verification_result or {}
            session.verification_result = {**current_res, **result}
            db.commit()
            
        # Update User & IdentityVerification records if verified
        if result.get("status") == "verified":
            user.is_verified = True
            user.is_kyc_complete = True
            if kyc_record:
                kyc_record.verification_status = "verified"
                kyc_record.verified_at = func.now()
                kyc_record.failure_reason = None
                
            db.query(models.Booking).filter(
                models.Booking.user_id == user_id,
                models.Booking.caterer_id == booking.caterer_id
            ).update({"ocr_verified": True, "liveness_verified": True})
            
            # Send Notification
            await NotificationService.notify_status_update(
                db, user_id, 
                "Identity Approved!", 
                f"Your identity has been verified. You may now proceed with your booking.",
                f"/bookings/step/quotation/{booking.id}",
                "kyc_update"
            )
            
        elif result.get("status") == "pending_manual_review":
            if kyc_record:
                kyc_record.verification_status = "pending_manual_review"
                kyc_record.failure_reason = result.get("failure_reason")
                
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
                kyc_record.ocr_data = new_ocr
            # Fallback in case ocr_data is currently None in the DB (initialize as empty dict)
            elif kyc_record.ocr_data is None:
                kyc_record.ocr_data = {}
                
            kyc_record.id_detected = result.get("ocr_match", False) or (isinstance(kyc_record.ocr_data, dict) and kyc_record.ocr_data.get("full_name") is not None)
            kyc_record.liveness_status = "passed" if result["status"] not in ["liveliness_failed", "failed"] else "failed"
            
        # Log to Audit
        audit = models.AuditLog(
            user_id=user_id,
            action="kyc_verification",
            old_status="processing",
            new_status=result.get("status", "failed"),
            notes=f"Fraud Score: {result.get('fraud_score', 0)}, OCR Match: {result.get('ocr_match', False)}, Liveness Score: {result.get('liveness_score', 0)}"
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
            session = db.query(models.VerificationSession).filter(models.VerificationSession.user_id == user_id).order_by(models.VerificationSession.created_at.desc()).first()
            if session:
                session.status = "failed"
            kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == user_id).first()
            
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
            
        try:
            with open("ocr_debug.log", "a", encoding="utf-8") as f:
                f.write(f"\n--- KYC BACKGROUND TASK FATAL ERROR AT {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                f.write(f"User ID: {user_id}, Booking ID: {booking_id}\n")
                f.write(f"Error: {str(e)}\n")
                f.write(f"Traceback: {traceback.format_exc()}\n")
                f.write("-" * 50 + "\n")
        except Exception:
            pass
    finally:
        db.close()

@router.post("/kyc/reset")
async def reset_kyc_status(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).first()
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
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Resets KYC status back to pending_liveliness so the customer can retake selfies.
    Called automatically by the frontend when liveness fails, before showing the retry UI."""
    kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).first()
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
    session = db.query(models.VerificationSession).filter(models.VerificationSession.user_id == current_user.id).order_by(models.VerificationSession.created_at.desc()).first()
    kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).first()
    
    # If blocked or rejected on the main compliance record, yield that
    if kyc_record and kyc_record.verification_status in ["blocked", "rejected"]:
        return {
            "status": kyc_record.verification_status,
            "fraud_score": kyc_record.fraud_score,
            "reason": kyc_record.failure_reason
        }
        
    if session:
        return {
            "status": session.status,
            "fraud_score": int(session.anti_spoof_score),
            "reason": session.verification_result.get("failure_reason") if session.verification_result else None
        }
        
    if kyc_record:
        return {
            "status": kyc_record.verification_status,
            "fraud_score": kyc_record.fraud_score,
            "reason": kyc_record.failure_reason
        }
        
    return {"status": "pending"}

@router.get("/kyc/view/{filename}")
async def view_kyc_document(
    filename: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Secure proxy to decrypt and view KYC documents."""
    # RBAC: Only admin, the document owner, or their caterer can view
    is_admin = current_user.role == "admin"
    is_owner = (
        filename.startswith(f"user_{current_user.id}_") or
        filename.startswith(f"temp_ocr_{current_user.id}_") or
        filename.startswith(f"cropped_temp_ocr_{current_user.id}_") or
        filename.startswith(f"cropped_user_{current_user.id}_") or
        filename.startswith(f"selfie_{current_user.id}_")
    )
    
    # Check IdentityVerification record for ownership (handles registration-uploaded files)
    if not is_owner:
        file_url = f"/static/uploads/verification/{filename}"
        proxy_url = f"/api/bookings/kyc/view/{filename}"
        identity = db.query(models.IdentityVerification).filter(
            models.IdentityVerification.user_id == current_user.id
        ).first()
        if identity:
            identity_urls = [identity.document_url, identity.selfie_url,
                           getattr(identity, 'selfie_2_url', None), getattr(identity, 'selfie_3_url', None)]
            if file_url in identity_urls or proxy_url in identity_urls:
                is_owner = True
    
    if current_user.role == "caterer" and current_user.caterer_profile:
        file_url = f"/static/uploads/verification/{filename}"
        proxy_url = f"/api/bookings/kyc/view/{filename}"
        profile = current_user.caterer_profile
        doc_urls = [
            profile.permit_url, profile.dti_url, profile.bir_url, 
            profile.mayors_permit_url, profile.gov_id_url
        ]
        if file_url in doc_urls or proxy_url in doc_urls:
            is_owner = True
    
    is_caterer_authorized = False
    if current_user.role == "caterer":
        # Check if this caterer has a booking with the user whose ID this is
        try:
            parts = filename.split("_")
            target_user_id = None
            if filename.startswith("cropped_"):
                if len(parts) > 2 and parts[1] == "user":
                    target_user_id = int(parts[2])
                elif len(parts) > 3 and parts[1] == "temp" and parts[2] == "ocr":
                    target_user_id = int(parts[3])
            else:
                if len(parts) > 1 and parts[0] == "user":
                    target_user_id = int(parts[1])
                elif len(parts) > 2 and parts[0] == "temp" and parts[1] == "ocr":
                    target_user_id = int(parts[2])

            if target_user_id is not None:
                booking = db.query(models.Booking).filter(
                    models.Booking.caterer_id == current_user.caterer_profile.id,
                    models.Booking.user_id == target_user_id
                ).first()
                if booking:
                    is_caterer_authorized = True
        except Exception as parse_err:
            print(f"[KYC VIEW] Caterer authorization parsing failed: {parse_err}")

    if not (is_owner or is_admin or is_caterer_authorized):
        raise HTTPException(status_code=403, detail="Unauthorized access to this document.")

    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Document not found.")

    with open(path, "rb") as f:
        file_data = f.read()
    
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
        from cryptography.fernet import InvalidToken
        decrypted_data = decrypt_data(file_data)
        return Response(content=decrypted_data, media_type=media_type)
    except (InvalidToken, Exception) as e:
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
                print(f"[KYC VIEW] File '{filename}' is not encrypted, serving raw {detected_mime}")
                return Response(content=file_data, media_type=detected_mime)
        
        # Neither valid decryption nor valid raw image — file is truly corrupted
        print(f"[KYC VIEW ERROR] Cannot decrypt or read file '{filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail="Document cannot be displayed. The file may be corrupted or the encryption key has changed. Please ask the user to re-upload."
        )
