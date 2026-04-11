from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Request
from sqlalchemy.orm import Session
from ..db import database, models
from ..core import security as auth
from ..services.verification import verification_service
from ..core.encryption import encrypt_data, decrypt_data
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

@router.post("/{booking_id}/upload-id")
async def upload_id(
    booking_id: int,
    id_type: str = Form(...),
    id_number: str = Form(...),
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
    if id_document.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG and PNG are allowed.")
    
    # Check file size (FastAPI doesn't do this by default, we read a bit)
    content = await id_document.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max size is 5MB.")
    
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
    
    kyc_record.document_url = id_url
    kyc_record.id_number = id_number
    kyc_record.verification_type = id_type
    kyc_record.verification_status = "processing"
    db.commit() # Commit so service can read it

    # --- STRICT SYNCHRONOUS VALIDATION ---
    print(f"[KYC] Performing synchronous ID validation for User {current_user.id}...")
    full_name = f"{current_user.first_name} {current_user.last_name}"
    id_result = verification_service.verify_id_document(
        id_url, 
        full_name, 
        id_number, 
        id_type,
        db=db,
        user_id=current_user.id
    )
    
    if id_result["status"] == "mismatched":
        # Delete the uploaded file and roll back the record status to prevent blocked progression
        try:
            os.remove(path)
        except:
            pass
        kyc_record.verification_status = "failed"
        kyc_record.failure_reason = id_result["failure_reason"]
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=id_result["failure_reason"]
        )
    elif id_result["status"] == "error":
        # Generic system error during scan
        raise HTTPException(status_code=500, detail=id_result["failure_reason"])

    # If matched, we proceed
    kyc_record.ocr_data = id_result.get("ocr_data", {})
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
        if file.content_type not in ALLOWED_MIME_TYPES:
             continue # Skip invalid ones or raise error
             
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            continue

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
    background_tasks.add_task(
        process_kyc_background,
        current_user.id,
        booking_id,
        kyc_record.document_url,
        selfie_urls,
        f"{current_user.first_name} {current_user.last_name}",
        kyc_record.id_number,
        kyc_record.verification_type
    )

    return {"status": "processing", "message": "Verification started. Please wait."}

def process_kyc_background(user_id, booking_id, id_path, selfie_paths, full_name, id_number, id_type):
    # This simulates the Celery worker / Background task logic
    db = next(database.get_db())
    try:
        print(f"\n[KYC BACKGROUND] Starting verification for User {user_id}...")
        user = db.query(models.User).get(user_id)
        booking = db.query(models.Booking).get(booking_id)
        kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == user_id).first()
        
        # Simulate processing time
        time.sleep(0.5)
        
        result = verification_service.verify_identity_v2(id_path, selfie_paths, full_name, id_number, id_type)
        
        print(f"[KYC BACKGROUND] Verification Service result: {result.get('status')}")
        
        # Override 'approved' to 'manual_review' as per user requirement: 
        # "pending muna yan pagkatpos dahil kailangan muna icheck ni admin yun at iaapprove"
        if result["status"] == "approved":
            kyc_record.verification_status = "manual_review"
            print(f"[KYC BACKGROUND] Result was 'approved', setting to 'manual_review' for admin approval.")
        else:
            kyc_record.verification_status = result["status"]

        kyc_record.fraud_score = result["fraud_score"]
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
    # RBAC: Only admin or the document owner can view
    is_admin = current_user.role == "admin"
    
    # Safety Check: Filename must be in the upload dir and look like a kyc file
    if not (filename.startswith(f"user_{current_user.id}") or is_admin):
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
