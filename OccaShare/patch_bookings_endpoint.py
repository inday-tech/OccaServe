import os

# This is a standalone script to add the endpoint to bookings.py

with open(r"c:\OccaServe\OccaShare\app\routers\bookings.py", "r", encoding="utf-8") as f:
    content = f.read()

endpoint_code = """
@router.post("/alacarte/payment/{booking_id}")
async def alacarte_manage_payment_submit(
    booking_id: int,
    request: Request,
    payment_method: str = Form("GCash"),
    proof_image: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):
    user = get_current_user_from_session(request, db)
    if not user:
        return {"success": False, "message": "Unauthorized"}
        
    booking = db.query(models.Booking).get(booking_id)
    if not booking or booking.user_id != user.id:
        return {"success": False, "message": "Booking not found"}
        
    # File validation
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp", "application/pdf"]
    if proof_image.content_type not in allowed_types:
        return {"success": False, "message": "Invalid file type. Only JPG, PNG, WEBP, and PDF are allowed."}
        
    proof_image.file.seek(0, os.SEEK_END)
    if proof_image.file.tell() > 5 * 1024 * 1024:
        return {"success": False, "message": "File too large. Maximum size is 5MB."}
    proof_image.file.seek(0)
    
    import uuid
    import shutil
    ext = os.path.splitext(proof_image.filename)[1]
    filename = f"{booking.id}_alacarte_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(PROOF_UPLOAD_DIR, filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(proof_image.file, buffer)
        
    # AI Receipt Validation
    from ..services.payment_verification import payment_verification_service
    verify_results = payment_verification_service.check_for_fraud(db, booking, filepath)
    
    if verify_results["confidence"] < 40:
        if os.path.exists(filepath): os.remove(filepath)
        flags = verify_results.get("flags", [])
        error_detail = flags[0] if flags else "The uploaded image does not appear to be a valid receipt for the required amount."
        return {"success": False, "message": f"{error_detail}"}
        
    # Save extracted details
    extracted_ref = verify_results.get("extracted_data", {}).get("reference_no")
    extracted_hash = payment_verification_service.get_image_hash(filepath)
    
    if extracted_ref: booking.payment_reference = extracted_ref
    booking.proof_image_hash = extracted_hash
    
    proof_url = f"/static/uploads/payment_proofs/{filename}"
    booking.payment_proof_url = proof_url
    booking.payment_method = payment_method
    booking.payment_status = "proof_submitted"
    if booking.status in ['draft', 'pending_payment', 'awaiting_payment']:
        booking.status = "pending"
        
    # History
    history = models.BookingHistory(
        booking_id=booking.id,
        status="pending",
        notes=f"Ala Carte payment proof submitted via {payment_method}. Awaiting caterer verification."
    )
    db.add(history)
    db.commit()
    
    # Notify
    from ..services.notification import NotificationService
    import asyncio
    asyncio.create_task(NotificationService.notify_payment_received(db, booking, float(booking.total_amount or 0), "Payment"))
    
    return {"success": True}

"""

if "alacarte_manage_payment_submit" not in content:
    content = content.replace("@router.post(\"/reupload-proof/{booking_id}\")", endpoint_code + "\n@router.post(\"/reupload-proof/{booking_id}\")")
    with open(r"c:\OccaServe\OccaShare\app\routers\bookings.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Endpoint added to bookings.py")
else:
    print("Endpoint already exists.")
