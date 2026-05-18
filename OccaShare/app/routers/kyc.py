from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Request
from sqlalchemy.orm import Session
from ..db import database, models
from ..core import security as auth
from ..services.verification import verification_service
from ..core.encryption import encrypt_data, decrypt_data
from ..core.utils import validate_file_type_and_size
from fastapi.responses import Response
import os
import uuid
import shutil
import io
import asyncio
import time
import traceback

# Security Constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_MIME_TYPES = ["image/jpeg", "image/png"]

router = APIRouter(prefix="/api/bookings", tags=["kyc"])

UPLOAD_DIR = "app/static/uploads/verification"
os.makedirs(UPLOAD_DIR, exist_ok=True)
@router.post("/extract-id")
async def extract_id(
    id_type: str = Form(...),
    id_document: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Endpoint for Section B: Extracts data from ID for the booking form."""
    content = await id_document.read()
    file_error = validate_file_type_and_size(content, id_document.filename)
    if file_error:
        raise HTTPException(status_code=400, detail=f"❌ {file_error}")
    
    # Save file temporarily or permanently
    filename = f"temp_ocr_{current_user.id}_{uuid.uuid4()}.enc"
    path = os.path.join(UPLOAD_DIR, filename)
    encrypted_content = encrypt_data(content)
    with open(path, "wb") as f:
        f.write(encrypted_content)
    
    id_url = f"/api/bookings/kyc/view/{filename}"
    
    result = await verification_service.extract_id_data(id_url, id_type)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"OCR extraction failed: {result.get('error')}")
    
    return {
        "success": True,
        "extracted_data": result["data"],
        "quality": result["quality"],
        "temp_id_url": id_url
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

    # Security: File Validation
    content = await id_document.read()
    file_error = validate_file_type_and_size(content, id_document.filename)
    if file_error:
        raise HTTPException(status_code=400, detail=f"❌ {file_error}")
    
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
    
    # Always reset status to pending when starting a new upload attempt
    kyc_record.verification_status = "pending"
    kyc_record.failure_reason = None
    
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

    # --- STRICT SYNCHRONOUS VALIDATION ---
    print(f"[KYC] Performing synchronous ID validation for User {current_user.id}...")
    
    # Construct full name as per user's pseudo-code logic: Given + Middle + Last
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
    
    if id_result["status"] in ["mismatched", "rejected"]:
        # Delete the uploaded file and roll back the record status to prevent blocked progression
        try:
            os.remove(path)
        except:
            pass
        kyc_record.verification_status = "failed"
        kyc_record.failure_reason = id_result["failure_reason"]
        kyc_record.document_url = None # Clear the URL so they can't "resume" with a bad ID
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=id_result["failure_reason"]
        )
    elif id_result["status"] == "error":
        # Generic system error during scan
        raise HTTPException(status_code=500, detail=id_result["failure_reason"])

    # If matched, we proceed
    kyc_record.document_url = id_url
    kyc_record.id_number = id_number
    kyc_record.verification_type = id_type
    kyc_record.ocr_data = id_result.get("ocr_data", {})
    kyc_record.verification_status = "pending" # Keep as pending until full verification (selfie) is done
    db.commit()

    return {"success": True, "message": "ID uploaded and verified. You may now proceed to liveness check."}

@router.post("/{booking_id}/verify-full")
async def verify_full(
    booking_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    selfies: list[UploadFile] = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).first()
    if not kyc_record or kyc_record.verification_status == "blocked":
        raise HTTPException(status_code=400, detail="KYC process not initialized or blocked.")

    # Save 3 selfie frames (Encrypted)
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
    db.commit()

    # Add background task for fintech logic
    # Retrieve data from user profile for background comparison
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
        current_user.address
    )

    return {"status": "processing", "message": "Verification started. Please wait."}

async def process_kyc_background(user_id, booking_id, id_path, selfie_paths, full_name, id_number, id_type, dob, address):
    # This simulates the Celery worker / Background task logic
    db = next(database.get_db())
    try:
        print(f"\n[KYC BACKGROUND] Starting verification for User {user_id}...")
        user = db.query(models.User).get(user_id)
        booking = db.query(models.Booking).get(booking_id)
        kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == user_id).first()
        
        # Simulate processing time
        time.sleep(0.5)
        
        result = await verification_service.verify_identity_v2(id_path, selfie_paths, full_name, id_number, id_type, db, user_id, dob, address)
        
        print(f"[KYC BACKGROUND] Verification Service result: {result.get('status')}")
        
        # Override 'approved' to 'manual_review' as per user requirement: 
        # "this should be pending after because it needs to be checked and approved by the caterer first"
        if result["status"] == "approved":
            kyc_record.verification_status = "manual_review"
            print(f"[KYC BACKGROUND] Result was 'approved', setting to 'manual_review' for caterer approval.")
        else:
            kyc_record.verification_status = result["status"]

        kyc_record.fraud_score = result["fraud_score"]
        kyc_record.match_score = result.get("face_match_confidence", 0.0)
        kyc_record.face_detected = result.get("liveness_score", 0.0) > 0 or result.get("face_match_confidence", 0.0) > 0
        kyc_record.id_detected = result.get("ocr_match", False) or result.get("ocr_data", {}).get("full_name") is not None
        kyc_record.failure_reason = result["failure_reason"]
        kyc_record.ocr_data = result.get("ocr_data", {})
        kyc_record.liveness_status = "passed" if result.get("liveness_score", 0.0) >= 0.4 else "failed"
        
        if result["status"] == "approved":
            user.is_verified = True
            user.is_kyc_complete = True
            booking.ocr_verified = True
            booking.liveness_verified = True
            
        # Log to Audit
        audit = models.AuditLog(
            user_id=user_id,
            action="kyc_verification",
            old_status="processing",
            new_status=result.get("status", "failed"),
            notes=f"Fraud Score: {result.get('fraud_score', 0)}, OCR: {result.get('ocr_match', False)}"
        )
        db.add(audit)
        db.commit()

        # Terminal Logging for the background process
        print(f"\n[KYC BACKGROUND] Verification Complete for User {user_id}")
        print(f" - Status: {result.get('status')}")
        print(f" - Fraud Score: {result.get('fraud_score')}")
        print(f" - OCR Match: {result.get('ocr_match')}")
        print(f" - Liveness PASSED: {'passed' if result.get('liveness_score', 0.0) >= 0.4 else 'failed'}")
        if result.get('failure_reason'):
            print(f" - Failure Reason: {result.get('failure_reason')}")
        print("-" * 40 + "\n")

    except Exception as e:
        print(f"[KYC DEBUG] Error in background KYC: {e}")
        traceback.print_exc()
        try:
            db = next(database.get_db())
            kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == user_id).first()
            if kyc_record:
                kyc_record.verification_status = "failed"
                kyc_record.failure_reason = f"System error during processing: {str(e)}"
                db.commit()
        except:
            pass

@router.post("/kyc/reset")
async def reset_kyc_status(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).first()
    if kyc_record:
        kyc_record.verification_status = "pending"
        kyc_record.failure_reason = None
        db.commit()
    return {"success": True}

@router.get("/{booking_id}/status")
async def get_kyc_status(
    booking_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).first()
    if not kyc_record:
        return {"status": "pending"}
    return {
        "status": kyc_record.verification_status,
        "fraud_score": kyc_record.fraud_score,
        "reason": kyc_record.failure_reason
    }

@router.get("/kyc/view/{filename}")
async def view_kyc_document(
    filename: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Secure proxy to decrypt and view KYC documents."""
    # RBAC: Only admin, the document owner, or their caterer can view
    is_admin = current_user.role == "admin"
    is_owner = filename.startswith(f"user_{current_user.id}")
    
    is_caterer_authorized = False
    if current_user.role == "caterer":
        # Check if this caterer has a booking with the user whose ID this is
        # Extract user_id from filename like "user_123_id_..."
        try:
            target_user_id = int(filename.split("_")[1])
            booking = db.query(models.Booking).filter(
                models.Booking.caterer_id == current_user.caterer_profile.id,
                models.Booking.user_id == target_user_id
            ).first()
            if booking:
                is_caterer_authorized = True
        except:
            pass

    if not (is_owner or is_admin or is_caterer_authorized):
        raise HTTPException(status_code=403, detail="Unauthorized access to this document.")

    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Document not found.")

    with open(path, "rb") as f:
        encrypted_data = f.read()
    
    try:
        from cryptography.fernet import InvalidToken
        decrypted_data = decrypt_data(encrypted_data)
    except InvalidToken:
        # This happens if the KYC_ENCRYPTION_KEY in .env was changed
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail="Document decryption failed. The encryption key has changed since this file was uploaded. Please ask the user to re-upload."
        )
    except Exception as e:
        print(f"Decryption error: {e}")
        raise HTTPException(status_code=500, detail="Failed to decrypt document.")

    # Infer MIME type from filename or just use image/jpeg as default
    # Real app would store MIME in DB
    return Response(content=decrypted_data, media_type="image/jpeg")
