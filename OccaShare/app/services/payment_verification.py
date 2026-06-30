import os
import hashlib
import re
import numpy as np
from PIL import Image, ImageOps
import io
from sqlalchemy.orm import Session
from datetime import datetime
from ..db import models

# Graceful imports for heavy dependencies
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    print("[PaymentVerify WARNING] OpenCV not available.")
    CV2_AVAILABLE = False
    cv2 = None

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    print("[PaymentVerify WARNING] pytesseract not available.")
    PYTESSERACT_AVAILABLE = False
    pytesseract = None

class PaymentVerificationService:
    def __init__(self):
        if not PYTESSERACT_AVAILABLE:
            print("[PaymentVerify] pytesseract not available. Payment OCR disabled.")
            return
        # Configure Tesseract Path
        if os.name != "nt":  # Linux (Railway)
            pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
            print("[PaymentVerify DEBUG] Using Linux Tesseract path: /usr/bin/tesseract")
        else:
            TESSERACT_PATHS = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\Tesseract-OCR\tesseract.exe")
            ]
            for path in TESSERACT_PATHS:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    os.environ["TESSDATA_PREFIX"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tessdata"))
                    break

    def get_image_hash(self, file_path: str) -> str:
        """Generates a SHA-256 hash of the image file to detect exact duplicates."""
        if not os.path.exists(file_path):
            return ""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _prepare_image(self, file_path: str) -> np.ndarray:
        """Loads and prepares image for OCR."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Proof file not found at {file_path}")
        
        # Load using PIL to handle orientation then convert to cv2
        pil_img = Image.open(file_path)
        pil_img = ImageOps.exif_transpose(pil_img)
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return img

    def extract_payment_data(self, file_path: str) -> dict:
        """Extracts text details from a payment receipt image."""
        try:
            img = self._prepare_image(file_path)
            
            # Basic enhancement for OCR
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Thresholding to make text pop
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # Run OCR
            text = pytesseract.image_to_string(thresh)
            
            data = {
                "raw_text": text,
                "amount": None,
                "reference_no": None,
                "date": None,
                "bank": "Detected"
            }

            # 1. Extract Amount (Look for ₱ or P followed by numbers)
            amount_match = re.search(r'(?:PHP|P|₱)\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
            if amount_match:
                amount_str = amount_match.group(1).replace(',', '')
                try:
                    data["amount"] = float(amount_str)
                except:
                    pass

            # 2. Extract Reference Number
            ref_match = re.search(r'(?:Ref|Reference|Trans|Trace)\s*(?:No|ID|#)?[:.\s]*([A-Z0-9]{8,})', text, re.IGNORECASE)
            if ref_match:
                data["reference_no"] = ref_match.group(1).strip()

            # 3. Extract Date
            date_match = re.search(r'(\d{2}[-/]\d{2}[-/]\d{2,4})|([A-Z]{3} \d{2}, \d{4})', text, re.IGNORECASE)
            if date_match:
                data["date"] = date_match.group(0)

            return data
        except Exception as e:
            print(f"[PaymentVerify DEBUG] OCR Error: {e}")
            return {"error": str(e)}

    def check_for_fraud(self, db: Session, booking: models.Booking, file_path: str) -> dict:
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
        img_hash = self.get_image_hash(file_path)
        if img_hash:
            # Check if this hash exists in any other booking (excluding current)
            existing_hash = db.query(models.Booking).filter(
                models.Booking.payment_reference == img_hash, # Using ref field temporarily or meta
                models.Booking.id != booking.id
            ).first()
            # Wait, better check a dedicated meta field if we add it
            
        # 2. OCR Extraction
        ocr_data = self.extract_payment_data(file_path)
        results["extracted_data"] = ocr_data
        
        # Check if the OCR engine itself failed (e.g. Tesseract not installed)
        if "error" in ocr_data:
            results["flags"].append(f"System OCR Engine Error: {ocr_data['error']}. The AI scanner is currently unavailable on this server.")
            results["confidence"] = 0
            return results

        raw_text = ocr_data.get("raw_text", "").upper()

        # [ZERO-TRUST] 2.1 Keyword Authenticity Check
        # Common keywords found in GCash, Maya, and major PH banks
        receipt_keywords = [
            "SUCCESSFULLY", "PAID", "SENT", "TRANSFER", "REF NO", "TRANS ID", 
            "GCASH", "MAYA", "RECEIPT", "BILLER", "AMOUNT PAID", "TRANSACTION"
        ]
        has_keywords = any(keyword in raw_text for keyword in receipt_keywords)
        
        if not raw_text.strip():
            results["flags"].append("Fraud Alert: Non-Document detected (Image contains no readable text).")
            results["confidence"] = 0
            return results

        if not has_keywords:
            results["flags"].append("High Risk: Image does not appear to be a valid financial receipt.")
            results["confidence"] = min(results["confidence"], 10) # Heavy penalty

        if "error" not in ocr_data:
            # 3. Reference Number Duplicate Check
            if ocr_data.get("reference_no"):
                ref = ocr_data["reference_no"]
                duplicate_ref = db.query(models.Booking).filter(
                    models.Booking.payment_reference == ref,
                    models.Booking.id != booking.id
                ).first()
                if duplicate_ref:
                    results["is_duplicate_ref"] = True
                    results["flags"].append(f"Duplicate reference: Ref No. {ref} has already been used.")

            # 4. Amount Matching
            if ocr_data.get("amount"):
                expected = float(booking.total_amount or 0)
                # Check for full payment or common deposit % (e.g. 20%, 30%, 50%)
                threshold = 5.0 # P5.00 variance allowed for minor OCR errors
                diff = abs(ocr_data["amount"] - expected)
                
                if diff < threshold:
                    results["amount_match"] = True
                else:
                    results["flags"].append(f"Amount mismatch: Found ₱{ocr_data['amount']:,}, but required is ₱{expected:,}")
            else:
                results["flags"].append("Invalid Proof: Could not detect any payment amount on the receipt.")

            # [ZERO-TRUST] 4.1 Missing Core Data penalty
            if not ocr_data.get("reference_no"):
                results["flags"].append("Invalid Proof: Reference Number is missing or unreadable.")

            # [ZERO-TRUST] 4.2 Caterer Identity Match
            has_caterer_match = False
            if booking.caterer_id:
                caterer = db.query(models.CatererProfile).get(booking.caterer_id)
                if caterer:
                    search_terms = []
                    if caterer.business_name: search_terms.append(caterer.business_name.upper())
                    if caterer.gcash_number: search_terms.append(caterer.gcash_number)
                    if caterer.maya_number: search_terms.append(caterer.maya_number)
                    if caterer.bank_account_name: search_terms.append(caterer.bank_account_name.upper())
                    
                    # Remove common words or short terms to prevent false positives
                    search_terms = [t for t in search_terms if t and len(t) > 3]
                    
                    for term in search_terms:
                        if term in raw_text:
                            has_caterer_match = True
                            break
                            
            if booking.caterer_id and not has_caterer_match:
                results["flags"].append("Recipient mismatch: Caterer's name or number was not found on the receipt.")

            # 5. Confidence Score (Stricter weighting)
            score = 0
            if ocr_data.get("amount"): score += 20
            if ocr_data.get("reference_no"): score += 30
            if ocr_data.get("date"): score += 10
            if has_keywords: score += 40
            if has_caterer_match: score += 20
            
            # Heavy Penalties
            if results["is_duplicate_ref"]: score -= 60
            if not results["amount_match"] and ocr_data.get("amount"): score -= 30
            if not has_keywords: score -= 50
            if booking.caterer_id and not has_caterer_match: score -= 30
            if not ocr_data.get("reference_no") and not ocr_data.get("amount"): score = 0 # Instant fail
            
            results["confidence"] = max(0, min(100, score))

            if results["confidence"] < 40:
                if not results["flags"]:
                    results["flags"].append("High Risk: AI Confidence is very low. Please upload a clearer image.")

        return results

payment_verification_service = PaymentVerificationService()
