import os
import re

def patch_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Normalize line endings
    content = content.replace('\r\n', '\n')
    
    modified = False
    for target, replacement in replacements:
        target = target.replace('\r\n', '\n')
        replacement = replacement.replace('\r\n', '\n')
        if target in content:
            content = content.replace(target, replacement)
            modified = True
        else:
            print(f"Warning: Target block not found in {filepath}")
    
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Patched {filepath}")

# 1. Patch payment_verification_service.py
pv_file = r'c:\OccaServe\OccaShare\app\services\payment_verification.py'
pv_replacements = [
    (
        '''    def get_image_hash(self, file_path: str) -> str:
        """Generates a SHA-256 hash of the image file to detect exact duplicates."""
        if not os.path.exists(file_path):
            return ""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()''',
        '''    def get_image_hash(self, base64_str: str) -> str:
        """Generates a SHA-256 hash of the image base64 data to detect exact duplicates."""
        if not base64_str: return ""
        import base64
        if "," in base64_str:
            base64_str = base64_str.split(",", 1)[1]
        try:
            raw_bytes = base64.b64decode(base64_str)
            sha256_hash = hashlib.sha256()
            sha256_hash.update(raw_bytes)
            return sha256_hash.hexdigest()
        except: return ""'''
    ),
    (
        '''    def _prepare_image(self, file_path: str) -> np.ndarray:
        """Loads and prepares image for OCR."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Proof file not found at {file_path}")
        
        # Load using PIL to handle orientation then convert to cv2
        pil_img = Image.open(file_path)
        pil_img = ImageOps.exif_transpose(pil_img)
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return img''',
        '''    def _prepare_image(self, base64_str: str) -> np.ndarray:
        """Loads and prepares image for OCR from base64."""
        import base64
        if "," in base64_str:
            base64_str = base64_str.split(",", 1)[1]
        img_bytes = base64.b64decode(base64_str)
        pil_img = Image.open(io.BytesIO(img_bytes))
        pil_img = ImageOps.exif_transpose(pil_img)
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return img'''
    ),
    (
        '''    def extract_payment_data(self, file_path: str) -> dict:
        """Extracts text details from a payment receipt image."""
        try:
            img = self._prepare_image(file_path)''',
        '''    def extract_payment_data(self, base64_str: str) -> dict:
        """Extracts text details from a payment receipt image from base64."""
        try:
            img = self._prepare_image(base64_str)'''
    ),
    (
        '''    def check_for_fraud(self, db: Session, booking: models.Booking, file_path: str) -> dict:
        """Runs a holistic fraud check on the submitted proof."""
        results = {
            "is_duplicate_image": False,
            "is_duplicate_ref": False,
            "amount_match": False,
            "confidence": 0,
            "extracted_data": {},
            "flags": []
        }

        # 1. Image Hash Check
        img_hash = self.get_image_hash(file_path)''',
        '''    def check_for_fraud(self, db: Session, booking: models.Booking, base64_str: str) -> dict:
        """Runs a holistic fraud check on the submitted proof using base64 data."""
        results = {
            "is_duplicate_image": False,
            "is_duplicate_ref": False,
            "amount_match": False,
            "confidence": 0,
            "extracted_data": {},
            "flags": []
        }

        # 1. Image Hash Check
        img_hash = self.get_image_hash(base64_str)'''
    ),
    (
        '''        # 2. OCR Extraction
        ocr_data = self.extract_payment_data(file_path)''',
        '''        # 2. OCR Extraction
        ocr_data = self.extract_payment_data(base64_str)'''
    )
]

patch_file(pv_file, pv_replacements)

# 2. Patch bookings.py remaining occurrences
bookings_file = r'c:\OccaServe\OccaShare\app\routers\bookings.py'
b_replacements = [
    (
        '''    import uuid
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
    
    booking.payment_proof_url = f"/static/uploads/payment_proofs/{filename}"''',
        '''    import base64
    content_bytes = await proof_image.read()
    b64_encoded = base64.b64encode(content_bytes).decode('utf-8')
    mime = proof_image.content_type or 'image/jpeg'
    proof_data_url = f"data:{mime};base64,{b64_encoded}"
        
    # AI Receipt Validation
    from ..services.payment_verification import payment_verification_service
    verify_results = payment_verification_service.check_for_fraud(db, booking, proof_data_url)
    
    if verify_results["confidence"] < 40:
        flags = verify_results.get("flags", [])
        error_detail = flags[0] if flags else "The uploaded image does not appear to be a valid receipt for the required amount."
        return {"success": False, "message": f"{error_detail}"}
        
    # Save extracted details
    extracted_ref = verify_results.get("extracted_data", {}).get("reference_no")
    extracted_hash = payment_verification_service.get_image_hash(proof_data_url)
    
    booking.payment_proof_url = proof_data_url'''
    ),
    (
        '''    import uuid
    import shutil
    import os
    
    # Upload proof of payment logic
    ext = os.path.splitext(payment_proof.filename)[1]
    filename = f"{booking.id}_balance_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(PROOF_UPLOAD_DIR, filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(payment_proof.file, buffer)
        
    is_valid_receipt = await _validate_receipt_with_gemini(filepath, payment_method, expected_amount=expected_fee)

    if not is_valid_receipt:
        if os.path.exists(filepath):
            os.remove(filepath)
        # Fallback to flash error redirection
        request.session["flash_error"] = "Invalid Receipt Detected: Our AI could not verify the Reference Number or Amount."
        return RedirectResponse(url=f"/bookings/manage/{booking.id}?error=invalid_receipt", status_code=303)
        
    proof_url = f"/static/uploads/payment_proofs/{filename}"''',
        '''    import base64
    content_bytes = await payment_proof.read()
    b64 = base64.b64encode(content_bytes).decode('utf-8')
    mime = payment_proof.content_type or 'image/jpeg'
    proof_url = f"data:{mime};base64,{b64}"
        
    is_valid_receipt = await _validate_receipt_with_gemini(proof_url, payment_method, expected_amount=expected_fee)

    if not is_valid_receipt:
        # Fallback to flash error redirection
        request.session["flash_error"] = "Invalid Receipt Detected: Our AI could not verify the Reference Number or Amount."
        return RedirectResponse(url=f"/bookings/manage/{booking.id}?error=invalid_receipt", status_code=303)'''
    )
]
patch_file(bookings_file, b_replacements)
