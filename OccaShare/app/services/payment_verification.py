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

    def _load_image_bytes(self, input_str: str) -> bytes:
        """
        Loads raw image bytes from:
        - Base64 Data URI (data:image/...) or raw base64 string
        - HTTP / HTTPS URL (Cloudinary, AWS S3, external CDN)
        - Local file path or relative upload URL (/static/uploads/...)
        """
        if not input_str:
            raise ValueError("No image input provided.")

        input_str = str(input_str).strip()

        # 1. Base64 Data URI
        if input_str.startswith("data:"):
            import base64
            base64_data = input_str.split(",", 1)[1]
            return base64.b64decode(base64_data)

        # 2. HTTP / HTTPS URL
        if input_str.startswith("http://") or input_str.startswith("https://"):
            import urllib.request
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(input_str, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                return resp.read()

        # 3. Local File System
        target_path = input_str
        if not os.path.exists(target_path):
            filename = os.path.basename(input_str.replace('\\', '/'))
            candidates = [
                input_str.lstrip('/\\'),
                os.path.join("app", input_str.lstrip('/\\')),
                os.path.join("app/static/uploads/payment_receipts", filename),
                os.path.join("app/static/uploads/payment_proofs", filename),
                os.path.join("app/static/uploads", filename),
                os.path.join("static/uploads/payment_receipts", filename),
                os.path.join("static/uploads/payment_proofs", filename),
                os.path.join("static/uploads", filename),
            ]
            for cand in candidates:
                if os.path.exists(cand):
                    target_path = cand
                    break

        if os.path.exists(target_path):
            with open(target_path, "rb") as f:
                return f.read()

        # Fallback: Raw Base64 string without data: prefix
        try:
            import base64
            return base64.b64decode(input_str)
        except Exception:
            raise FileNotFoundError(f"Payment proof image not found or invalid input: {input_str}")

    def get_image_hash(self, input_str: str) -> str:
        """Generates a SHA-256 hash of the image bytes to detect exact duplicates."""
        if not input_str: return ""
        try:
            raw_bytes = self._load_image_bytes(input_str)
            sha256_hash = hashlib.sha256()
            sha256_hash.update(raw_bytes)
            return sha256_hash.hexdigest()
        except Exception:
            return ""

    def _prepare_image(self, input_str: str) -> np.ndarray:
        """Loads and prepares image for OCR."""
        img_bytes = self._load_image_bytes(input_str)
        pil_img = Image.open(io.BytesIO(img_bytes))
        pil_img = ImageOps.exif_transpose(pil_img)
        if CV2_AVAILABLE:
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        else:
            img = np.array(pil_img)[:, :, ::-1].copy()
        return img

    def extract_payment_data(self, base64_str: str) -> dict:
        """Extracts text details from a payment receipt image from base64 or URL."""
        try:
            img = self._prepare_image(base64_str)
            
            # Basic enhancement for OCR
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # Run OCR
            text = pytesseract.image_to_string(thresh) if PYTESSERACT_AVAILABLE else ""
            
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
        import base64
        
        results = {
            "is_duplicate_image": False,
            "is_duplicate_ref": False,
            "amount_match": False,
            "confidence": 0,
            "extracted_data": {},
            "flags": []
        }

        # 1. Load Raw Image Bytes & Generate Hash
        try:
            raw_image_bytes = self._load_image_bytes(base64_str)
            b64_encoded_data = base64.b64encode(raw_image_bytes).decode('utf-8')
        except Exception as load_err:
            print(f"[PaymentVerify ERROR] Failed to load payment proof image: {load_err}")
            results["flags"].append(f"AI Check Failed: Could not load screenshot ({load_err}).")
            return results

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
        if booking and getattr(booking, 'caterer_id', None):
            caterer = db.query(models.CatererProfile).get(booking.caterer_id)
            if caterer:
                caterer_name = caterer.business_name or ""
                caterer_gcash = caterer.gcash_number or ""
                caterer_maya = caterer.maya_number or ""
                caterer_bank = caterer.bank_account_name or ""
                
        expected_amount = (getattr(booking, 'total_amount', 0.0) if booking else 0.0) or 0.0
        expected_method = (getattr(booking, 'payment_method', 'GCASH') if booking else "GCASH") or "GCASH"
        
        prompt = f"""You are an expert financial receipt verification assistant for OccaServe catering marketplace in the Philippines.
Analyze the uploaded image carefully.

EXPECTED DETAILS:
- Expected Amount: ₱{expected_amount:,.2f}
- Expected Payment Method: {expected_method}
- Expected Caterer Name: {caterer_name}
- Expected Account Details: GCash={caterer_gcash}, Maya={caterer_maya}, Bank={caterer_bank}

RULES FOR ANALYSIS:
1. "is_valid_receipt": Must be true if the image is a payment receipt, GCash/Maya transaction screenshot, or bank deposit slip. Set false ONLY if it's a selfie, food photo, wallpaper, or non-payment image.
2. "extracted_amount": Extract the numeric amount paid on the receipt.
3. "extracted_reference_no": Extract the Reference No., Ref No., Transaction ID, or Trace No.
4. "extracted_date": Extract transaction date/time if visible.
5. "amount_match": Set true if extracted_amount is greater than 0 and reasonably matches expected amount (allow downpayments/deposits e.g. 50% or full amount, or small transfer fees).
6. "flags": Include strings in this list ONLY if there is a severe fraud issue (e.g. image is fake/photo of non-receipt, or amount is completely wrong like P1 instead of P5000). Do NOT add flags for missing optional fields.

Provide a JSON response strictly in this format:
{{
    "is_valid_receipt": true or false,
    "extracted_amount": float or null,
    "extracted_date": "string or null",
    "extracted_reference_no": "string or null",
    "detected_payment_method": "GCASH" | "MAYA" | "BANK" | "OTHER" | null,
    "caterer_match": bool,
    "amount_match": bool,
    "confidence_score": integer (0 to 100),
    "flags": []
}}
"""
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": b64_encoded_data
                        }
                    }
                ]
            }],
            "generationConfig": {
                "response_mime_type": "application/json"
            }
        }
        
        headers = {"Content-Type": "application/json"}
        models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        gemini_data = None

        async with httpx.AsyncClient() as client:
            for model_name in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
                try:
                    res = await client.post(url, json=payload, headers=headers, timeout=25.0)
                    if res.status_code == 200:
                        result_json = res.json()
                        text_resp = result_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
                        
                        text_resp = text_resp.strip()
                        if text_resp.startswith("```json"):
                            text_resp = text_resp[7:]
                        if text_resp.startswith("```"):
                            text_resp = text_resp[3:]
                        if text_resp.endswith("```"):
                            text_resp = text_resp[:-3]
                            
                        gemini_data = json.loads(text_resp.strip())
                        print(f"[PaymentVerify DEBUG] Successfully called Gemini model '{model_name}'.")
                        break
                    else:
                        print(f"[PaymentVerify WARNING] Gemini model '{model_name}' returned status {res.status_code}")
                except Exception as model_err:
                    print(f"[PaymentVerify WARNING] Failed model '{model_name}': {model_err}")

        if not gemini_data:
            results["flags"].append("AI Verification Error: Could not connect to AI service.")
            return results

        # Process Gemini Response
        results["extracted_data"] = {
            "amount": gemini_data.get("extracted_amount"),
            "reference_no": gemini_data.get("extracted_reference_no"),
            "date": gemini_data.get("extracted_date"),
            "bank": gemini_data.get("detected_payment_method")
        }
        
        score = gemini_data.get("confidence_score", 85 if gemini_data.get("is_valid_receipt") else 0)
        
        if not gemini_data.get("is_valid_receipt", False):
            score = 0
            if not gemini_data.get("flags"):
                results["flags"].append("Fraud Alert: Image does not appear to be a valid financial receipt.")
                
        if gemini_data.get("flags"):
            results["flags"].extend(gemini_data.get("flags"))
            
        results["amount_match"] = gemini_data.get("amount_match", True if gemini_data.get("extracted_amount") else False)
        
        # Check Reference Duplicate
        if results["extracted_data"].get("reference_no") and booking and getattr(booking, 'id', None):
            ref = results["extracted_data"]["reference_no"]
            duplicate_ref = db.query(models.Booking).filter(
                models.Booking.payment_reference == ref,
                models.Booking.id != booking.id
            ).first()
            if duplicate_ref:
                results["is_duplicate_ref"] = True
                results["flags"].append(f"Duplicate reference: Ref No. {ref} has already been used.")
                score = min(score, 20)

        # Final Score adjustments
        if gemini_data.get("is_valid_receipt") and (results["extracted_data"].get("reference_no") or results["extracted_data"].get("amount")):
            score = max(score, 80)

        results["confidence"] = max(0, min(100, score))
        return results

payment_verification_service = PaymentVerificationService()
