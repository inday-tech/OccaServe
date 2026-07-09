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

    def get_image_hash(self, base64_str: str) -> str:
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
        except: return ""

    def _prepare_image(self, base64_str: str) -> np.ndarray:
        """Loads and prepares image for OCR from base64."""
        import base64
        if "," in base64_str:
            base64_str = base64_str.split(",", 1)[1]
        img_bytes = base64.b64decode(base64_str)
        pil_img = Image.open(io.BytesIO(img_bytes))
        pil_img = ImageOps.exif_transpose(pil_img)
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return img

    def extract_payment_data(self, base64_str: str) -> dict:
        """Extracts text details from a payment receipt image from base64."""
        try:
            img = self._prepare_image(base64_str)
            
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

    async def check_for_fraud(self, db: Session, booking: models.Booking, base64_str: str) -> dict:
        """Runs a holistic fraud check on the submitted proof using Gemini."""
        import os, httpx, json, asyncio
        
        results = {
            "is_duplicate_image": False,
            "is_duplicate_ref": False,
            "amount_match": False,
            "confidence": 0,
            "extracted_data": {},
            "flags": []
        }

        # 1. Image Hash Check
        img_hash = self.get_image_hash(base64_str)
        if img_hash:
            pass # TODO: Duplicate hash check logic

        # 2. Gemini OCR Validation
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            results["flags"].append("AI Verification Error: Missing Gemini API Key. Cannot verify receipt automatically.")
            return results

        caterer_name = ""
        caterer_gcash = ""
        caterer_maya = ""
        caterer_bank = ""
        if booking.caterer_id:
            caterer = db.query(models.CatererProfile).get(booking.caterer_id)
            if caterer:
                caterer_name = caterer.business_name
                caterer_gcash = caterer.gcash_number or ""
                caterer_maya = caterer.maya_number or ""
                caterer_bank = caterer.bank_account_name or ""
                
        expected_amount = booking.total_amount or 0.0
        expected_method = booking.payment_method or "GCASH"
        
        prompt = f"""You are a financial receipt verification assistant for OccaServe.
Analyze the uploaded image. We need to verify if this is a legitimate proof of payment and if the details match our booking requirements.

EXPECTED BOOKING DETAILS:
- Expected Amount: ₱{expected_amount:,.2f}
- Expected Payment Method: {expected_method}
- Expected Caterer Name: {caterer_name}
- Expected Accounts: GCash={caterer_gcash}, Maya={caterer_maya}, Bank={caterer_bank}

Verify the following:
1. Is it a valid receipt? (Not a selfie, food pic, or random screenshot)
2. Does the amount match {expected_amount}? (Allow minor discrepancies like P5.00 transfer fees, but flag if it's completely different)
3. Does the payment method on the receipt match {expected_method}? (e.g., If we expect GCASH but it's a BDO bank transfer receipt, flag it)
4. Are the caterer's details present? (Name or account number)
5. Is the receipt date recent? (It should be within the last 2 days of today. If it is old or has a future date, flag it)

Provide a JSON response strictly in this format:
{{
    "is_valid_receipt": bool,
    "extracted_amount": float or null,
    "extracted_date": "string or null",
    "extracted_reference_no": "string or null",
    "detected_payment_method": "GCASH" | "MAYA" | "BANK" | "OTHER" | null,
    "caterer_match": bool,
    "amount_match": bool,
    "confidence_score": 0 to 100 (integer),
    "flags": ["list of strings detailing EXACTLY what is wrong, e.g., 'Amount mismatch: found 100 but expected 500', 'Method mismatch: Expected GCASH but received BANK receipt', 'Date is missing']
}}
"""
        
        # Prepare image payload
        import base64
        if "," in base64_str:
            base64_str = base64_str.split(",", 1)[1]
            
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": base64_str
                        }
                    }
                ]
            }],
            "generationConfig": {
                "response_mime_type": "application/json"
            }
        }
        
        headers = {"Content-Type": "application/json"}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
        
        gemini_data = None
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(url, json=payload, headers=headers, timeout=25.0)
                if res.status_code == 200:
                    result_json = res.json()
                    text_resp = result_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
                    
                    # Clean up markdown code blocks if present
                    text_resp = text_resp.strip()
                    if text_resp.startswith("```json"):
                        text_resp = text_resp[7:]
                    if text_resp.startswith("```"):
                        text_resp = text_resp[3:]
                    if text_resp.endswith("```"):
                        text_resp = text_resp[:-3]
                        
                    gemini_data = json.loads(text_resp.strip())
                else:
                    results["flags"].append(f"AI Verification Error: Received status {res.status_code} from Gemini.")
                    return results
            except Exception as e:
                results["flags"].append(f"AI Verification Error: {str(e)}")
                return results
                
        if not gemini_data:
            results["flags"].append("AI Verification Error: Failed to parse Gemini response.")
            return results

        # Process Gemini Response
        results["extracted_data"] = {
            "amount": gemini_data.get("extracted_amount"),
            "reference_no": gemini_data.get("extracted_reference_no"),
            "date": gemini_data.get("extracted_date"),
            "bank": gemini_data.get("detected_payment_method")
        }
        
        # Build score and flags based on strict AI feedback
        score = gemini_data.get("confidence_score", 0)
        
        if not gemini_data.get("is_valid_receipt", False):
            score = 0
            if not gemini_data.get("flags"):
                results["flags"].append("Fraud Alert: Image does not appear to be a valid financial receipt.")
                
        if gemini_data.get("flags"):
            results["flags"].extend(gemini_data.get("flags"))
            
        results["amount_match"] = gemini_data.get("amount_match", False)
        
        # Check Reference Duplicate
        if results["extracted_data"].get("reference_no"):
            ref = results["extracted_data"]["reference_no"]
            duplicate_ref = db.query(models.Booking).filter(
                models.Booking.payment_reference == ref,
                models.Booking.id != booking.id
            ).first()
            if duplicate_ref:
                results["is_duplicate_ref"] = True
                results["flags"].append(f"Duplicate reference: Ref No. {ref} has already been used.")
                score -= 60
                
        results["confidence"] = max(0, min(100, score))
        
        # Ensure confidence is lowered if there are serious flags
        if results["flags"] and results["confidence"] > 40:
            results["confidence"] = 39 # Force failure if Gemini generated explicit flags
            
        return results

payment_verification_service = PaymentVerificationService()
