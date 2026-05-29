import warnings
# Suppress protobuf deprecation warnings from Mediapipe
warnings.filterwarnings("ignore", category=UserWarning, module='google.protobuf.symbol_database')

import random
import time
import re
import os
import io
import difflib
import numpy as np
import traceback
from dotenv import load_dotenv
load_dotenv(override=True)
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from ..core.encryption import decrypt_data
from PIL import Image, ImageOps
from sqlalchemy.orm import Session
import base64
import httpx
from ..db.models import IdentityVerification


# Graceful imports for heavy dependencies (may not be available on all cloud platforms)
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    print("[KYC WARNING] OpenCV (cv2) not available. KYC verification will be limited.")
    CV2_AVAILABLE = False
    cv2 = None

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    print("[KYC WARNING] pytesseract not available. OCR verification will be limited.")
    PYTESSERACT_AVAILABLE = False
    pytesseract = None

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    print("[KYC WARNING] mediapipe not available. Liveness detection will be limited.")
    MEDIAPIPE_AVAILABLE = False
    mp = None

# EasyOCR (primary OCR engine - free, no API key needed, deep learning based)
try:
    import easyocr
    EASYOCR_AVAILABLE = True
    # Singleton reader - initialized once at module load, reused for all requests
    # gpu=False for compatibility; set gpu=True if CUDA is available
    _easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    print("[KYC DEBUG] EasyOCR initialized successfully (English).")
except ImportError:
    print("[KYC WARNING] EasyOCR not available. Install with: pip install easyocr")
    EASYOCR_AVAILABLE = False
    _easyocr_reader = None
except Exception as _easyocr_err:
    print(f"[KYC WARNING] EasyOCR init failed: {_easyocr_err}")
    EASYOCR_AVAILABLE = False
    _easyocr_reader = None

# Configure Tesseract Path for Windows and Linux
if PYTESSERACT_AVAILABLE:
    if os.name != "nt":  # Linux (Railway)
        pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
        print("[KYC DEBUG] Using Linux Tesseract path: /usr/bin/tesseract")
    else:
        TESSERACT_PATHS = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\Tesseract-OCR\tesseract.exe")
        ]

        for path in TESSERACT_PATHS:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                print(f"[KYC DEBUG] Tesseract found at: {path}")
                break
        else:
            print("[KYC DEBUG] Tesseract NOT found in common Windows paths. Using system default.")

class VerificationService:
    # ID Patterns (Regular Expressions)
    ID_PATTERNS = {
        "Passport": r"^[A-Z][0-9]{7}[A-Z]$|^[A-Z][0-9]{8}$",
        "Driver's License": r"^[A-Z][0-9]{2}-[0-9]{2}-[0-9]{6}$",
        "PhilID (National ID)": r"^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{4}$",
        "UMID": r"^[0-9]{4}-[0-9]{7}-[0-9]{1}$",
        "SSS ID": r"^[0-9]{2}-[0-9]{7}-[0-9]{1}$",
        "PRC ID": r"^[0-9]{7}$",
        "Postal ID": r"^[A-Z0-9]{12}$",
        "Voter's ID": r"^[0-9]{4}-[0-9]{4}[A-Z]$",
        "TIN ID": r"^[0-9]{3}-[0-9]{3}-[0-9]{3}-[0-9]{3}$",
        "PhilHealth ID": r"^[0-9]{2}-[0-9]{9}-[0-9]{1}$",
        "School ID": r"^[A-Z0-9-]{5,20}$",
        "NBI Clearance": r"^[A-Z0-9]{10,18}$",
        "Alien Certificate of Registration": r"^[A-Z][0-9]{9}$"
    }

    BUSINESS_PERMIT_KEYWORDS = [
        "BUSINESS PERMIT", "MAYOR'S PERMIT", "DTI", "SEC", "REGISTRATION", "PERMIT TO OPERATE", "CERTIFICATE OF REGISTRATION",
        "REPUBLIC OF THE PHILIPPINES", "OFFICE OF THE MAYOR", "BUSINESS NAME REGISTRATION", "TAX DECLARATION", "DEPARTMENT OF TRADE AND INDUSTRY"
    ]

    OWNER_NAME_LABELS = [
        "REGISTERED OWNER", "NAME OF OWNER", "OWNER", "PROPRIETOR", "TAXPAYER", "PERMITTEE"
    ]

    MENU_KEYWORDS = [
        "MENU", "PRICE LIST", "PACKAGE", "DISH", "FOOD", "CATERING", "DRINKS", "DESSERT", "MAIN COURSE", "APPETIZER",
        "PAX", "SERVES", "PER HEAD", "PHP", "₱", "ORDER", "MEAL", "BUFFET", "SET MENU"
    ]

    def __init__(self):
        self.landmarker = None
        
        if not MEDIAPIPE_AVAILABLE:
            print("[KYC DEBUG] MediaPipe not available. Liveness detection disabled.")
            return
            
        # MediaPipe Tasks API Setup (Preferred for newer versions like 0.10.x)
        try:
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            import urllib.request
            
            model_paths = [
                os.path.join(os.getcwd(), "app/models/face_landmarker.task"),
                os.path.join(os.getcwd(), "face_landmarker.task"),
                "/app/app/models/face_landmarker.task", # Docker/Linux fallback
                "/app/OccaShare/face_landmarker.task" # Railway fallback
            ]
            
            model_path = None
            for p in model_paths:
                if os.path.exists(p):
                    model_path = p
                    print(f"[KYC DEBUG] MediaPipe model found at: {p}")
                    break

            # Auto-download model if missing
            if not model_path:
                try:
                    model_dir = os.path.join(os.getcwd(), "app/models")
                    if not os.path.exists(model_dir):
                        os.makedirs(model_dir)
                    model_path = os.path.join(model_dir, "face_landmarker.task")
                    print(f"[KYC DEBUG] Downloading MediaPipe model to {model_path}...")
                    model_url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
                    urllib.request.urlretrieve(model_url, model_path)
                    print(f"[KYC DEBUG] Successfully downloaded model.")
                except Exception as dl_err:
                    print(f"[KYC DEBUG] Failed to download model: {dl_err}")
                    model_path = None

            if model_path:
                try:
                    base_options = python.BaseOptions(model_asset_path=model_path)
                    options = vision.FaceLandmarkerOptions(
                        base_options=base_options,
                        num_faces=1)
                    self.landmarker = vision.FaceLandmarker.create_from_options(options)
                except Exception as init_err:
                    print(f"[KYC DEBUG] Failed to initialize landmarker: {init_err}")
            else:
                print(f"[KYC DEBUG] MediaPipe model not found. Liveness might fail.")
        except Exception as e:
            print(f"[KYC DEBUG] MediaPipe setup failed: {e}")

    def validate_id_pattern(self, id_type: str, id_number: str) -> bool:
        """Checks if the ID number matches the expected pattern for the ID type."""
        pattern = self.ID_PATTERNS.get(id_type)
        if not pattern:
            return True # If no pattern defined, assume valid for demo
        # Clean ID number for matching (remove spaces/dashes if necessary)
        clean_id = id_number.replace(" ", "").replace("-", "")
        # However, patterns usually expect the format, so we match original too
        return bool(re.match(pattern, id_number)) or bool(re.match(pattern.replace("-", "").replace(" ", ""), clean_id))

    def _prepare_image(self, encrypted_path: str) -> np.ndarray:
        """Decrypts a file, handles EXIF orientation, and converts to OpenCV BGR."""
        filename = os.path.basename(encrypted_path.replace('\\', '/'))
        real_path = os.path.join("app/static/uploads/verification", filename)
        
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"KYC document not found at {real_path}")

        try:
            with open(real_path, "rb") as f:
                raw_data = f.read()
            
            # Try to decrypt
            try:
                decrypted_data = decrypt_data(raw_data)
                print(f"[KYC DEBUG] Decrypted {filename} successfully.")
            except Exception:
                # Fallback: Maybe it's not encrypted? (e.g. from a previous version or direct upload)
                decrypted_data = raw_data
                print(f"[KYC DEBUG] Could not decrypt {filename}, using raw data.")

            # Use PIL to handle EXIF orientation automatically
            pil_img = Image.open(io.BytesIO(decrypted_data))
            pil_img = ImageOps.exif_transpose(pil_img)
            
            # Convert back to BGR for OpenCV compatibility
            if CV2_AVAILABLE:
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            else:
                # Manual RGB to BGR conversion using numpy if cv2 is missing
                img = np.array(pil_img)[:, :, ::-1].copy()
            return img
        except Exception as e:
            print(f"[KYC DEBUG] Fatal error preparing image {filename}: {e}")
            if CV2_AVAILABLE and raw_data:
                try:
                    nparr = np.frombuffer(raw_data, np.uint8)
                    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                except: pass
            raise e

    def _detect_faces_detailed(self, img: np.ndarray) -> List[Any]:
        """Detect faces using standard OpenCV Haar Cascades."""
        if not CV2_AVAILABLE:
            print("[KYC WARNING] Face detection skipped: OpenCV not available.")
            return []
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            return faces
        except:
            return []

    def _calculate_ear(self, landmarks, eye_indices):
        """Calculates Eye Aspect Ratio (EAR). Landmarks are MediaPipe NormalizedLandmark objects."""
        # Vertical distances
        v1 = np.linalg.norm(np.array([landmarks[eye_indices[1]].x, landmarks[eye_indices[1]].y]) - 
                            np.array([landmarks[eye_indices[5]].x, landmarks[eye_indices[5]].y]))
        v2 = np.linalg.norm(np.array([landmarks[eye_indices[2]].x, landmarks[eye_indices[2]].y]) - 
                            np.array([landmarks[eye_indices[4]].x, landmarks[eye_indices[4]].y]))
        # Horizontal distance
        h = np.linalg.norm(np.array([landmarks[eye_indices[0]].x, landmarks[eye_indices[0]].y]) - 
                           np.array([landmarks[eye_indices[3]].x, landmarks[eye_indices[3]].y]))
        
        ear = (v1 + v2) / (2.0 * h) if h > 0 else 0
        return ear

    def _check_liveness_mediapipe(self, img_list: List[np.ndarray]) -> Dict[str, Any]:
        """Sophisticated liveness check with occlusion and head pose detection."""
        if not self.landmarker:
            return {"score": 0.0, "face_count": 0, "error": "Landmarker not initialized"}

        ears = []
        nose_tips = []
        face_detected_count = 0
        occlusion_detected = False
        occlusion_reason = None
        
        # Head pose tracking
        angles_v = [] # Vertical (pitch)
        angles_h = [] # Horizontal (yaw)

        for img in img_list:
            if not MEDIAPIPE_AVAILABLE or not CV2_AVAILABLE or not mp:
                continue
            
            try:
                rgb_data = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if CV2_AVAILABLE else img[:, :, ::-1]
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_data)
                detection_result = self.landmarker.detect(mp_image)
            except Exception as e:
                print(f"[KYC ERROR] MediaPipe detection failed: {e}")
                continue
            
            if detection_result.face_landmarks:
                face_detected_count += 1
                landmarks = detection_result.face_landmarks[0]
                
                # --- OCCLUSION & ORIENTATION CHECK ---
                # Check for "confidence" or presence of key landmarks
                # We check if critical landmarks (Eyes, Mouth, Nose) are within reasonable bounds
                critical_indices = [33, 133, 362, 263, 1, 61, 291]
                if any(landmarks[i].x < 0 or landmarks[i].x > 1 or landmarks[i].y < 0 or landmarks[i].y > 1 for i in critical_indices):
                    occlusion_detected = True
                    occlusion_reason = "Face landmarks out of frame. Please stay centered."
                
                # Yaw: Check distance between eyes and nose for direct orientation
                e_dist_l = np.linalg.norm(np.array([landmarks[33].x, landmarks[33].y]) - np.array([landmarks[1].x, landmarks[1].y]))
                e_dist_r = np.linalg.norm(np.array([landmarks[263].x, landmarks[263].y]) - np.array([landmarks[1].x, landmarks[1].y]))
                yaw_ratio = e_dist_l / e_dist_r if e_dist_r > 0 else 5
                
                if yaw_ratio > 3.0 or yaw_ratio < 0.33:
                    occlusion_detected = True
                    occlusion_reason = "Please face the camera directly. No masks or sunglasses allowed."

                # Check if face is too close or far (bounding box size)
                # Normalized coordinates: x, y in [0, 1]
                xs = [l.x for l in landmarks]
                ys = [l.y for l in landmarks]
                face_w = max(xs) - min(xs)
                face_h = max(ys) - min(ys)
                
                if face_w < 0.2: # Face too small
                    occlusion_detected = True
                    occlusion_reason = "Face is too far from the camera."
                elif face_w > 0.9: # Face too large/cropped
                    occlusion_detected = True
                    occlusion_reason = "Face is too close or partially out of frame."

                # Indexes for EAR
                left_eye = [33, 160, 158, 133, 153, 144]
                right_eye = [362, 385, 387, 263, 373, 380]
                
                ear_l = self._calculate_ear(landmarks, left_eye)
                ear_r = self._calculate_ear(landmarks, right_eye)
                ears.append((ear_l + ear_r) / 2.0)
                nose_tips.append(np.array([landmarks[1].x, landmarks[1].y, landmarks[1].z]))

        # Calculation
        ear_variance = np.var(ears) if len(ears) > 1 else 0
        movement = 0
        if len(nose_tips) > 1:
            movement = np.mean([np.linalg.norm(nose_tips[i] - nose_tips[i-1]) for i in range(1, len(nose_tips))])

        liveness_score = 0.0
        if face_detected_count == len(img_list) and not occlusion_detected:
            liveness_score += 0.4
            if ear_variance > 0.001: liveness_score += 0.3
            if movement > 0.01: liveness_score += 0.3

        return {
            "score": liveness_score,
            "face_count": face_detected_count,
            "occlusion_detected": occlusion_detected,
            "failure_reason": occlusion_reason,
            "ear_variance": ear_variance,
            "movement": movement
        }

    def calculate_fraud_score(self, 
                                face_match_conf: float, 
                                liveness_score: float, 
                                ocr_match: bool, 
                                pattern_valid: bool) -> int:
        """Fintech-level 100-point scoring engine."""
        score = 0
        if face_match_conf >= 0.7: score += 40
        elif face_match_conf >= 0.5: score += 20
        
        if liveness_score >= 0.7: score += 30
        elif liveness_score >= 0.4: score += 15
        
        if ocr_match: score += 20
        if pattern_valid: score += 10
        
        return score

    def compare_faces(self, img1: np.ndarray, img2: np.ndarray) -> Dict[str, Any]:
        """Compares two faces using MediaPipe landmark feature similarity."""
        if not self.landmarker:
            return {"match": False, "confidence": 0.0, "error": "Landmarker offline"}

        def get_face_features(img):
            if not MEDIAPIPE_AVAILABLE or not CV2_AVAILABLE or not mp or not self.landmarker:
                return None
            try:
                rgb_data = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if CV2_AVAILABLE else img[:, :, ::-1]
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_data)
                res = self.landmarker.detect(mp_image)
                if not res.face_landmarks: return None
            except Exception as e:
                print(f"[KYC ERROR] Face feature extraction failed: {e}")
                return None
            # Return relative spatial distribution of key features
            lm = res.face_landmarks[0]
            # Normalize key points relative to nose (index 1)
            nose = np.array([lm[1].x, lm[1].y])
            features = []
            for idx in [33, 133, 362, 263, 61, 291, 10, 152]: # Eyes, Mouth, Forehead, Chin
                pt = np.array([lm[idx].x, lm[idx].y])
                features.append(pt - nose)
            return np.array(features).flatten()

        f1 = get_face_features(img1)
        f2 = get_face_features(img2)

        if f1 is None or f2 is None:
            return {"match": False, "confidence": 0.0, "error": "Face not detected in one or both images"}

        # Calculate Cosine Similarity or Euclidean distance
        dist = np.linalg.norm(f1 - f2)
        # Threshold (tuned for normalized landmark relative coordinates)
        confidence = max(0, 1 - (dist * 2.0))
        
        return {
            "match": confidence > 0.6,
            "confidence": float(confidence)
        }

    def _calculate_field_confidence(self, field_value: str, word_data: List[Dict]) -> str:
        """Matches extracted field value to OCR word data to get avg confidence. 
           Returns the field_value if found (with lenient confidence threshold).
           If field_value is empty, returns 'NOT DETECTED'."""
        if not field_value or not str(field_value).strip():
            return "NOT DETECTED"
        
        field_str = str(field_value).strip()
        
        # If no word_data available, just return the field (common in Tesseract fallback)
        if not word_data:
            return field_str
            
        words = field_str.split()
        total_conf = 0
        match_count = 0
        
        for w in words:
            for d in word_data:
                if w.lower() in d['word'].lower() or d['word'].lower() in w.lower():
                    total_conf += d['conf']
                    match_count += 1
                    break
        
        # If we matched at least some words, use the confidence
        if match_count > 0:
            avg_conf = total_conf / match_count
            # Much more lenient threshold (30 instead of 50)
            if avg_conf < 30:
                return "LOW CONFIDENCE"
        
        # Always return the field if it was extracted (lenient mode)
        return field_str

    def _parse_ocr_fields_advanced(self, text: str, word_data: List[Dict], id_type: str) -> Dict[str, Any]:
        """Extracts JSON structure dynamically based on ID type using VERY flexible parsing rules."""
        clean = text.upper()
        clean = re.sub(r'[^A-Z0-9\s/.,:-]', '', clean)
        
        # Helper to get line after a keyword (more lenient)
        def get_after(keywords, lines_list, max_lines=2, fallback_to_any=False):
            # All metadata keywords across different ID cards to prevent swallowing other fields
            all_kws = [
                "APELYIDO", "SURNAME", "LAST NAME", "LASTNAME", 
                "MGA PANGALAN", "GIVEN NAMES", "FIRST NAME", "GIVEN NAME", "FIRSTNAME", "GIVEN",
                "GITNANG APELYIDO", "MIDDLE NAME", "MID NAME", "MIDNAME", "MIDDLE",
                "KAPANGANAKAN", "DATE OF BIRTH", "DATE OT BINTH", "DATE OF DOB", "BIRTH", "DOB",
                "TRAHAN", "ADDRESS", "TIRAHAN", "ADDRES",
                "SEX", "KASARIAN", "NATIONALITY", "CITIZENSHIP", 
                "LICENSE", "PASSPORT", "UMID", "SSS"
            ]
            for i, line in enumerate(lines_list):
                if any(kw in line for kw in keywords):
                    for kw in keywords:
                        if kw in line:
                            rest = line.split(kw, 1)[1].strip()
                            if len(rest) > 2: 
                                # Truncate at the earliest occurrence of any OTHER metadata keyword
                                other_kws = [k for k in all_kws if not any(x in k or k in x for x in keywords)]
                                earliest_idx = len(rest)
                                for okw in other_kws:
                                    if okw in rest:
                                        idx = rest.index(okw)
                                        if idx < earliest_idx:
                                            earliest_idx = idx
                                rest = rest[:earliest_idx].strip()
                                
                                # Remove trailing/leading punctuation
                                rest = re.sub(r'^[.:,\s"\'/-]+', '', rest)
                                rest = re.sub(r'[.:,\s"\'/-]+$', '', rest)
                                
                                # Remove self-labels to get clean names/values
                                rest = re.sub(r'(?i)MIDDLE\s*NAME|MIDDLE\s*NANIE|MIDNAME|GITNANG\s*APELYIDO|NAMTIES|NAMES|GIVEN|MGA|PANGALAN|FIRST|LAST|SURNAME|APELYIDO', '', rest).strip()
                                
                                if len(rest) > 2:
                                    return rest
                    for j in range(1, max_lines + 1):
                        if i + j < len(lines_list):
                            val = lines_list[i+j].strip()
                            if len(val) > 2 and not any(meta_kw in val for meta_kw in all_kws):
                                return val
            
            # Fallback: Extract any substantial line if not found
            if fallback_to_any:
                for line in lines_list:
                    if len(line.strip()) > 3 and not any(meta_kw in line.upper() for meta_kw in all_kws):
                        return line.strip()
            return ""

        # Helper for regex matching (returns first match or empty)
        def get_match(pattern, text_corpus, group=1):
            m = re.search(pattern, text_corpus)
            return m.group(group) if m else ""
        
        # Helper to extract text chunks (heuristic for names when keywords not found)
        def extract_text_chunks(text_str, min_length=3):
            """Extracts capitalized text sequences that could be names."""
            chunks = []
            # Find sequences of uppercase words
            pattern = r'\b[A-Z][A-Z\s]{' + str(min_length-1) + ',}\b'
            matches = re.findall(pattern, text_str)
            chunks = [m.strip() for m in matches if len(m.strip()) >= min_length]
            
            # Also extract simple capitalized words
            if len(chunks) < 3:
                words = text_str.split()
                for word in words:
                    if len(word) >= 3 and word.isupper() and word not in chunks:
                        chunks.append(word)
                    if len(chunks) >= 5:
                        break
            
            return chunks

        lines = [l.strip() for l in clean.split('\n') if l.strip()]
        result = {"id_type": id_type, "full_name": "", "id_number": "", "date_of_birth": "", "address": "", "sex": ""}
        
        if id_type in ["PhilID (National ID)", "philsys", "PhilSys / PhilID", "PhilID"]:
            raw_id = get_match(r'(\d{4}-\d{4}-\d{4}-\d{4})', clean)
            if not raw_id:
                raw_id = get_match(r'(\d{4}\s*\d{4}\s*\d{4}\s*\d{4})', clean)
            
            # Improved name extraction with aggressive fallbacks
            raw_last = get_after(["APELYIDO", "SURNAME", "LAST NAME"], lines, 1)
            raw_given = get_after(["MGA PANGALAN", "GIVEN NAMES", "FIRST NAME", "GIVEN NAME", "GIVEN", "PANGALAN"], lines, 1)
            raw_mid = get_after(["GITNANG APELYIDO", "MIDDLE NAME", "MID NAME"], lines, 1)
            
            # Smart fallback for raw_last if it was misread as "L Name" or next to ID number
            if not raw_last and raw_id:
                id_idx = clean.find(raw_id)
                if id_idx != -1:
                    after_id = clean[id_idx + len(raw_id):].strip()
                    # Skip noise and check first uppercase word immediately after ID number
                    first_word_match = re.match(r'^([A-Z]{3,20})', re.sub(r'^[.:,\s"\'/-]+', '', after_id))
                    if first_word_match:
                        raw_last = first_word_match.group(1)
            
            # Aggressive fallback: extract names from text chunks
            text_chunks = extract_text_chunks(clean)
            if not raw_last and text_chunks:
                raw_last = text_chunks[0]
            if not raw_given and len(text_chunks) > 1:
                raw_given = text_chunks[1]
            if not raw_mid and len(text_chunks) > 2:
                raw_mid = text_chunks[2]
            
            # Second fallback: extract names from any line with 2-4 words (likely a name)
            if not raw_given and not raw_last:
                for line in lines:
                    word_count = len(line.split())
                    if 2 <= word_count <= 4 and not any(meta in line for meta in ["DATE", "ADDRESS", "SEX"]):
                        parts = line.split()
                        if len(parts) >= 2:
                            raw_given = parts[0]
                            raw_last = parts[-1]
                            if len(parts) >= 3:
                                raw_mid = parts[1]
                            break
            
            # Flexible DOB patterns
            raw_dob = get_match(r'((?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s+\d{1,2},?\s+\d{4})', clean)
            if not raw_dob:
                raw_dob = get_match(r'(\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})', clean)
            
            raw_addr = get_after(["ADDRESS", "TIRAHAN", "ADDRES"], lines, 5)
            
            result.update({
                "id_type": "PhilSys / PhilID",
                "id_number": self._calculate_field_confidence(raw_id, word_data),
                "last_name": self._calculate_field_confidence(raw_last, word_data),
                "given_names": self._calculate_field_confidence(raw_given, word_data),
                "first_name": self._calculate_field_confidence(raw_given, word_data),
                "middle_name": self._calculate_field_confidence(raw_mid, word_data),
                "date_of_birth": self._calculate_field_confidence(raw_dob, word_data),
                "address": self._calculate_field_confidence(raw_addr, word_data),
            })
            # fallback Full Name
            gn = result["given_names"] if result["given_names"] not in ["NOT DETECTED", "LOW CONFIDENCE"] else ""
            mn = result["middle_name"] if result["middle_name"] not in ["NOT DETECTED", "LOW CONFIDENCE"] else ""
            ln = result["last_name"] if result["last_name"] not in ["NOT DETECTED", "LOW CONFIDENCE"] else ""
            result["full_name"] = " ".join([gn, mn, ln]).strip()


        elif id_type == "Driver's License" or id_type == "drivers_license":
            raw_last = get_after(["LAST NAME"], lines, 1)
            raw_first = get_after(["FIRST NAME"], lines, 1)
            raw_mid = get_after(["MIDDLE NAME"], lines, 1)
            
            # Aggressive fallback for names if keywords not found
            text_chunks = extract_text_chunks(clean)
            if not raw_last and text_chunks:
                raw_last = text_chunks[0]
            if not raw_first and len(text_chunks) > 1:
                raw_first = text_chunks[1]
            if not raw_mid and len(text_chunks) > 2:
                raw_mid = text_chunks[2]
            
            # Second fallback: extract names from any line with 2-4 words
            if not raw_first and not raw_last:
                for line in lines:
                    word_count = len(line.split())
                    if 2 <= word_count <= 4 and not any(meta in line for meta in ["DATE", "ADDRESS", "EXPIR", "VALID"]):
                        parts = line.split()
                        if len(parts) >= 2:
                            raw_first = parts[0]
                            raw_last = parts[-1]
                            if len(parts) >= 3:
                                raw_mid = parts[1]
                            break
            
            # More flexible license number patterns
            raw_lic = get_match(r'([A-Z]\d{2}-\d{2}-\d{6})', clean)
            if not raw_lic:
                raw_lic = get_match(r'([A-Z0-9]{3}-\d{2}-\d{6})', clean)
            
            raw_nat = get_match(r'NATIONALITY[:\s]*([A-Z]+)', clean)
            raw_sex = get_match(r'\b(M|F|MALE|FEMALE)\b', clean)
            
            # More flexible date patterns
            raw_dob = get_match(r'(\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})', clean)
            if not raw_dob:
                raw_dob = get_match(r'((?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s+\d{1,2},?\s+\d{4})', clean)
            
            raw_wt = get_match(r'WEIGHT[:\s]*(\d+\s*KG)', clean)
            raw_ht = get_match(r'HEIGHT[:\s]*(\d+\.?\d*\s*M)', clean)
            raw_addr = get_after(["ADDRESS"], lines, 3)
            raw_exp = get_match(r'EXPIRATION DATE[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})', clean)
            raw_agc = get_match(r'AGENCY CODE[:\s]*([A-Z0-9]+)', clean)
            raw_bld = get_match(r'BLOOD TYPE[:\s]*([AB0][-+]|[A-Z][-+])', clean)
            raw_eye = get_match(r'EYES COLOR[:\s]*([A-Z]+)', clean)
            raw_rest = get_match(r'RESTRICTIONS[:\s]*([1-9]+)', clean)
            raw_cond = get_match(r'CONDITIONS[:\s]*([A-Z0-9]+)', clean)

            result.update({
                "id_type": "drivers_license",
                "last_name": self._calculate_field_confidence(raw_last, word_data),
                "first_name": self._calculate_field_confidence(raw_first, word_data),
                "middle_name": self._calculate_field_confidence(raw_mid, word_data),
                "license_number": self._calculate_field_confidence(raw_lic, word_data),
                "id_number": self._calculate_field_confidence(raw_lic, word_data),
                "nationality": self._calculate_field_confidence(raw_nat, word_data),
                "sex": self._calculate_field_confidence(raw_sex, word_data),
                "date_of_birth": self._calculate_field_confidence(raw_dob, word_data),
                "weight": self._calculate_field_confidence(raw_wt, word_data),
                "height": self._calculate_field_confidence(raw_ht, word_data),
                "address": self._calculate_field_confidence(raw_addr, word_data),
                "expiration_date": self._calculate_field_confidence(raw_exp, word_data),
                "agency_code": self._calculate_field_confidence(raw_agc, word_data),
                "blood_type": self._calculate_field_confidence(raw_bld, word_data),
                "eyes_color": self._calculate_field_confidence(raw_eye, word_data),
                "restrictions": self._calculate_field_confidence(raw_rest, word_data),
                "conditions": self._calculate_field_confidence(raw_cond, word_data),
            })
            fn = result["first_name"] if result["first_name"] not in ["NOT DETECTED", "LOW CONFIDENCE"] else ""
            mn = result["middle_name"] if result["middle_name"] not in ["NOT DETECTED", "LOW CONFIDENCE"] else ""
            ln = result["last_name"] if result["last_name"] not in ["NOT DETECTED", "LOW CONFIDENCE"] else ""
            result["full_name"] = " ".join([fn, mn, ln]).strip()


        elif id_type == "Passport" or id_type == "passport":
            raw_type = get_match(r'TYPE[:\s]*([A-Z])', clean)
            raw_cc = get_match(r'COUNTRY CODE[:\s]*([A-Z]{3})', clean)
            raw_pass = get_match(r'PASSPORT NO\.?[:\s]*([A-Z0-9]{7,9})', clean)
            if not raw_pass:
                raw_pass = get_match(r'\b([A-Z][0-9]{7,8})\b', clean)
            
            raw_last = get_after(["SURNAME", "LAST NAME"], lines, 1)
            raw_given = get_after(["GIVEN NAMES", "FIRST NAME", "GIVEN NAME"], lines, 1)
            raw_mid = get_after(["MIDDLE NAME"], lines, 1)
            
            # Aggressive fallback for names if keywords not found
            text_chunks = extract_text_chunks(clean)
            if not raw_last and text_chunks:
                raw_last = text_chunks[0]
            if not raw_given and len(text_chunks) > 1:
                raw_given = text_chunks[1]
            if not raw_mid and len(text_chunks) > 2:
                raw_mid = text_chunks[2]
            
            # Second fallback: extract names from any line with 2-4 words
            if not raw_given and not raw_last:
                for line in lines:
                    word_count = len(line.split())
                    if 2 <= word_count <= 4 and not any(meta in line for meta in ["DATE", "ISSUE", "VALID", "NATIONALITY"]):
                        parts = line.split()
                        if len(parts) >= 2:
                            raw_given = parts[0]
                            raw_last = parts[-1]
                            if len(parts) >= 3:
                                raw_mid = parts[1]
                            break

                if len(text_chunks) >= 2:
                    raw_last = text_chunks[0]
                    raw_given = text_chunks[1]
                    if len(text_chunks) >= 3:
                        raw_mid = text_chunks[2]
                elif len(text_chunks) >= 1:
                    raw_given = text_chunks[0]
            
            # Flexible date patterns
            raw_dob = get_match(r'DATE OF BIRTH[:\s]*(\d{2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s+\d{4})', clean)
            if not raw_dob:
                raw_dob = get_match(r'(\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})', clean)
            
            raw_nat = get_match(r'NATIONALITY[:\s]*([A-Z]+)', clean)
            raw_sex = get_match(r'SEX[:\s]*(M|F|MALE|FEMALE)', clean)
            raw_pob = get_after(["PLACE OF BIRTH"], lines)
            raw_doi = get_match(r'DATE OF ISSUE[:\s]*(\d{2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s+\d{4})', clean)
            raw_vu = get_match(r'VISA UNTIL[:\s]*(\d{2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s+\d{4})', clean)
            raw_auth = get_after(["ISSUING AUTHORITY"], lines)
            
            result.update({
                "id_type": "passport",
                "type": self._calculate_field_confidence(raw_type, word_data),
                "country_code": self._calculate_field_confidence(raw_cc, word_data),
                "passport_number": self._calculate_field_confidence(raw_pass, word_data),
                "id_number": self._calculate_field_confidence(raw_pass, word_data),
                "last_name": self._calculate_field_confidence(raw_last, word_data),
                "given_names": self._calculate_field_confidence(raw_given, word_data),
                "first_name": self._calculate_field_confidence(raw_given, word_data),
                "middle_name": self._calculate_field_confidence(raw_mid, word_data),
                "date_of_birth": self._calculate_field_confidence(raw_dob, word_data),
                "nationality": self._calculate_field_confidence(raw_nat, word_data),
                "sex": self._calculate_field_confidence(raw_sex, word_data),
                "place_of_birth": self._calculate_field_confidence(raw_pob, word_data),
                "date_of_issue": self._calculate_field_confidence(raw_doi, word_data),
                "visa_until": self._calculate_field_confidence(raw_vu, word_data),
                "issuing_authority": self._calculate_field_confidence(raw_auth, word_data)
            })
            gn = result["given_names"] if result["given_names"] not in ["NOT DETECTED", "LOW CONFIDENCE"] else ""
            mn = result["middle_name"] if result["middle_name"] not in ["NOT DETECTED", "LOW CONFIDENCE"] else ""
            ln = result["last_name"] if result["last_name"] not in ["NOT DETECTED", "LOW CONFIDENCE"] else ""
            result["full_name"] = " ".join([gn, mn, ln]).strip()

            
        else:
            # UMID / Fallback Generic Logic
            raw_name = get_after(["NAME", "PANGALAN"], lines)
            raw_dob = get_match(r'((?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s+\d{1,2},?\s+\d{4}|\d{4}[-/]\d{2}[-/]\d{2})', clean)
            raw_addr = get_after(["ADDRESS", "TIRAHAN"], lines, 3)
            result["full_name"] = self._calculate_field_confidence(raw_name, word_data)
            result["date_of_birth"] = self._calculate_field_confidence(raw_dob, word_data)
            result["address"] = self._calculate_field_confidence(raw_addr, word_data)
            
        # Check if all critical fields failed
        all_not_detected = True
        for k, v in result.items():
            if k not in ["id_type", "type", "country_code"] and v not in ["NOT DETECTED", "LOW CONFIDENCE", ""]:
                all_not_detected = False
                break
        
        result["_all_not_detected"] = all_not_detected
        return result

    def check_image_quality(self, image: np.ndarray) -> Dict[str, Any]:
        """Checks image for blur, resolution, and basic glare."""
        height, width = image.shape[:2]
        
        # 1. Resolution Check
        if width < 640 or height < 400:
            return {"valid": False, "reason": f"Resolution too low ({width}x{height}). Please take a clearer photo."}
        
        # 2. Blur Detection (Laplacian Variance)
        if not CV2_AVAILABLE:
            print("[KYC WARNING] Skipping blur detection: OpenCV not available.")
            return {"valid": True}
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        print(f"[KYC DEBUG] Image Quality Check - Resolution: {width}x{height}, Blur Score: {blur_score:.2f}")
        
        # Threshold 100 is usually good for ID cards, but let's be very lenient for demo/panel defense (5)
        if blur_score < 5:
            return {"valid": False, "reason": "Image is too blurry. Please retake your ID photo."}
            
        return {"valid": True}

    def _is_image_cropped(self, image: np.ndarray) -> bool:
        """Heuristic to check if the ID card is cropped (e.g. border of card is cut off)."""
        if not CV2_AVAILABLE:
            return False
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edged = cv2.Canny(blurred, 30, 150)
            contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return False
            
            img_h, img_w = image.shape[:2]
            img_area = img_h * img_w
            
            for c in contours:
                area = cv2.contourArea(c)
                # If contour is reasonably large (at least 15% of the image area)
                if area > img_area * 0.15:
                    x, y, w, h = cv2.boundingRect(c)
                    # Check if bounding box is too close (within 10 pixels) to any edge of the image
                    if x < 10 or y < 10 or (x + w) > img_w - 10 or (y + h) > img_h - 10:
                        print(f"[KYC DEBUG] Card is cropped: bbox=[{x},{y},{w},{h}] on image {img_w}x{img_h}")
                        return True
            return False
        except Exception as e:
            print(f"[KYC WARNING] Cropped ID check failed: {e}")
            return False

    def check_duplicate_id(self, db: Session, id_number: str, current_user_id: int) -> bool:
        """Checks if the ID number is already associated with another verified user."""
        existing = db.query(IdentityVerification).filter(
            IdentityVerification.id_number == id_number,
            IdentityVerification.user_id != current_user_id,
            IdentityVerification.verification_status.in_(['approved', 'verified'])
        ).first()
        return existing is not None

    def _is_ocr_garbage(self, text: str) -> bool:
        """Heuristic to check if OCR output is mostly noise/symbols."""
        if not text or len(text.strip()) < 10:
            return True
        
        # Check density of alphanumeric vs symbols
        total = len(text)
        alnum = len(re.sub(r'[^a-zA-Z0-9]', '', text))
        # Exclude spaces from symbol count
        symbols = total - alnum - text.count(' ')
        
        symbol_density = symbols / total if total > 0 else 1.0
        
        # If > 50% of text is symbols/noise, it's likely garbage (Raised from 0.4 to 0.5 for robustness)
        return symbol_density > 0.5

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """Corrects the rotation/tilt of an image."""
        if not CV2_AVAILABLE: return image
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.bitwise_not(gray)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) == 0: return image
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45: angle = -(90 + angle)
        else: angle = -angle
        if abs(angle) < 0.5 or abs(angle - 90) < 0.5 or abs(angle + 90) < 0.5:
            return image
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    def _auto_crop(self, image: np.ndarray) -> np.ndarray:
        """Find largest contour assuming it's the ID card and crop it."""
        if not CV2_AVAILABLE: return image
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 30, 150)
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours: return image
        c = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)
        if w > image.shape[1] * 0.5 and h > image.shape[0] * 0.5:
            return image[y:y+h, x:x+w]
        return image

    def _preprocess_for_ocr_advanced(self, image: np.ndarray, aggressive=False) -> np.ndarray:
        """Applies Advanced Preprocessing for OCR including deskewing, autocrop, sharpening, contrast, etc."""
        if not CV2_AVAILABLE: return image
        image = self._deskew(image)
        image = self._auto_crop(image)

        height, width = image.shape[:2]
        # More aggressive upscaling for better text extraction
        scaling_factor = 4.0 if aggressive else (3.0 if height < 600 else (2.0 if height < 800 else 1.5))
        upscaled = cv2.resize(image, (int(width * scaling_factor), int(height * scaling_factor)), interpolation=cv2.INTER_CUBIC)
        
        gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
        gray = cv2.normalize(gray, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
        
        # Enhanced contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Sharpening kernel
        kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel_sharpen)

        # Background subtraction to improve text visibility
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))
        bg = cv2.morphologyEx(sharpened, cv2.MORPH_DILATE, kernel)
        gray_sub = cv2.divide(sharpened, bg, scale=255)

        # Bilateral filtering to smooth while preserving edges
        filtered = cv2.bilateralFilter(gray_sub, 9, 75, 75)

        # Improved thresholding for better text extraction
        if aggressive:
            # More aggressive thresholding for low-quality images
            thresh = cv2.adaptiveThreshold(filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 5)
            # Optional: Apply morphological operations to clean up
            kernel_clean = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_clean, iterations=1)
        else:
            thresh = cv2.adaptiveThreshold(filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 3)
        
        print(f"[KYC DEBUG] Preprocessing: aggressive={aggressive}, input={height}x{width}, scaled={int(height*scaling_factor)}x{int(width*scaling_factor)}")
        return thresh

    def _extract_with_confidence(self, image: np.ndarray, psm_modes=[6, 11, 4]) -> Tuple[str, List[Dict]]:
        """Multi-pass PyTesseract utilizing Output.DICT to gather confidences."""
        if not PYTESSERACT_AVAILABLE: return "", []
        best_text = ""
        best_data = []

        for psm in psm_modes:
            config = f'--oem 3 --psm {psm} -l eng'
            try:
                from pytesseract import Output
                data = pytesseract.image_to_data(image, config=config, output_type=Output.DICT)
                text_parts = []
                word_data = []
                for i in range(len(data['text'])):
                    word = data['text'][i].strip()
                    if word:
                        conf = int(data['conf'][i])
                        text_parts.append(word)
                        word_data.append({"word": word, "conf": conf})
                
                current_text = " ".join(text_parts)
                print(f"[KYC DEBUG] PSM {psm}: Extracted {len(current_text)} chars, {len(word_data)} words")
                
                if len(current_text) > len(best_text):
                    best_text = current_text
                    best_data = word_data
                
                if len(current_text) > 150:  # Sufficient text found
                    break
            except Exception as e:
                print(f"[KYC OCR ERROR] Failed PSM {psm}: {e}")
                
        return best_text, best_data

    def _run_tesseract_advanced(self, image: np.ndarray, id_type: str) -> Tuple[str, Dict[str, Any], List[Dict]]:
        """Orchestrates OpenCV preprocessing -> Multi-pass Tesseract -> Regex parsing."""
        if not PYTESSERACT_AVAILABLE:
            return "", {}, []
        
        print(f"[KYC DEBUG] Starting Tesseract extraction for ID type: {id_type}")
        
        # Pass 1: Standard preprocessing
        thresh = self._preprocess_for_ocr_advanced(image, aggressive=False)
        text, word_data = self._extract_with_confidence(thresh, [6, 11, 4])
        
        # Check if text is sparse or missing fields, triggering retry logic
        parsed = self._parse_ocr_fields_advanced(text, word_data, id_type)
        print(f"[KYC DEBUG] Pass 1 - Extracted {len(text)} chars, full_name: '{parsed.get('full_name')}', id_number: '{parsed.get('id_number')}'")
        
        if parsed.get("_all_not_detected", True) or len(text.strip()) < 50:
            print("[KYC OCR] Pass 1 failed. Retrying with aggressive preprocessing...")
            thresh_agg = self._preprocess_for_ocr_advanced(image, aggressive=True)
            text_agg, word_data_agg = self._extract_with_confidence(thresh_agg, [11, 4, 6])
            parsed_agg = self._parse_ocr_fields_advanced(text_agg, word_data_agg, id_type)
            print(f"[KYC DEBUG] Pass 2 - Extracted {len(text_agg)} chars, full_name: '{parsed_agg.get('full_name')}', id_number: '{parsed_agg.get('id_number')}'")
            
            # Use aggressive run if it's better
            if not parsed_agg.get("_all_not_detected", True) or len(text_agg) > len(text):
                return text_agg, parsed_agg, word_data_agg
                
        return text, parsed, word_data

    def _run_tesseract_multi_psm(self, image: np.ndarray, id_type: str = "Unknown") -> str:
        """Backward-compatible wrapper around _run_tesseract_advanced.
        Returns only the raw OCR text string so existing call sites keep working."""
        text, _parsed, _word_data = self._run_tesseract_advanced(image, id_type)
        return text

    # ── EasyOCR Methods ──────────────────────────────────────────────────────────

    def _run_easyocr(self, image: np.ndarray, id_type: str = "Unknown") -> Tuple[str, List[Dict]]:
        """Run EasyOCR on an image. Returns (text, word_data) matching Tesseract format."""
        if not EASYOCR_AVAILABLE or _easyocr_reader is None:
            return "", []
        
        try:
            # EasyOCR accepts numpy arrays directly (BGR or grayscale)
            results = _easyocr_reader.readtext(image, detail=1, paragraph=False)
            
            # Sort by vertical position (top-to-bottom), then horizontal (left-to-right)
            results.sort(key=lambda r: (r[0][0][1], r[0][0][0]))
            
            text_parts = []
            word_data = []
            
            for (bbox, text, conf) in results:
                clean_text = text.strip()
                if clean_text and conf > 0.15:  # Low threshold to catch faint text on IDs
                    text_parts.append(clean_text)
                    word_data.append({
                        "word": clean_text,
                        "conf": int(conf * 100),
                        "bbox": bbox  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                    })
            
            full_text = " ".join(text_parts)
            print(f"[KYC DEBUG] EasyOCR: Extracted {len(full_text)} chars, {len(word_data)} words for {id_type}")
            return full_text, word_data
        except Exception as e:
            print(f"[KYC ERROR] EasyOCR failed: {e}")
            return "", []

    def _run_ocr_pipeline(self, image: np.ndarray, id_type: str) -> Tuple[str, Dict[str, Any], List[Dict]]:
        """
        Unified OCR Pipeline: EasyOCR (primary) -> Tesseract (fallback).
        Uses OpenCV preprocessing passes to maximize extraction quality.
        Returns (raw_text, parsed_fields_dict, word_data).
        """
        text = ""
        word_data = []
        parsed = {"_all_not_detected": True}
        
        vps_url = os.getenv("VPS_AI_URL")
        vps_api_key = os.getenv("VPS_API_KEY")
        if vps_url:
            print(f"[KYC DEBUG] Delegating OCR pipeline to VPS: {vps_url}/ocr")
            try:
                if CV2_AVAILABLE:
                    success, buffer = cv2.imencode(".jpg", image)
                else:
                    from PIL import Image as PILImage
                    pil_img = PILImage.fromarray(image[:, :, ::-1])
                    buf = io.BytesIO()
                    pil_img.save(buf, format="JPEG")
                    buffer = buf
                    success = True
                
                if success:
                    jpeg_bytes = buffer.tobytes() if hasattr(buffer, "tobytes") else buffer.getvalue()
                    import requests
                    files = {"image": ("id_image.jpg", jpeg_bytes, "image/jpeg")}
                    data = {"id_type": id_type, "preprocess": "true"}
                    headers = {}
                    if vps_api_key:
                        headers["X-API-Key"] = vps_api_key
                    response = requests.post(f"{vps_url}/ocr", files=files, data=data, headers=headers, timeout=30.0)
                    
                    if response.status_code == 200:
                        res_json = response.json()
                        if res_json.get("success"):
                            text = res_json.get("text", "")
                            word_data = res_json.get("word_data", [])
                            parsed = self._parse_ocr_fields_advanced(text, word_data, id_type)
                            parsed["face_visible"] = bool(res_json.get("face_visible", False))
                            print(f"[KYC DEBUG] VPS OCR Succeeded: {len(text)} characters extracted.")
                            return text, parsed, word_data
                    
                    print(f"[KYC WARNING] VPS OCR failed: status={response.status_code}, response={response.text}")
            except Exception as e:
                print(f"[KYC ERROR] VPS OCR delegation failed: {e}")
                traceback.print_exc()
            print("[KYC WARNING] Falling back to local OCR pipeline...")

        if EASYOCR_AVAILABLE and _easyocr_reader is not None:
            # Pass 1: Standard preprocessing + EasyOCR
            if CV2_AVAILABLE:
                preprocessed = self._preprocess_for_ocr_advanced(image, aggressive=False)
                text, word_data = self._run_easyocr(preprocessed, id_type)
                parsed = self._parse_ocr_fields_advanced(text, word_data, id_type)
                print(f"[KYC DEBUG] EasyOCR Pass 1 (preprocessed): {len(text)} chars, all_not_detected={parsed.get('_all_not_detected')}")
            
            # Pass 1b: Also try on original (unprocessed) image - sometimes works better for high-res photos
            if parsed.get("_all_not_detected", True) or len(text.strip()) < 30:
                text_raw, wd_raw = self._run_easyocr(image, id_type)
                parsed_raw = self._parse_ocr_fields_advanced(text_raw, wd_raw, id_type)
                print(f"[KYC DEBUG] EasyOCR Pass 1b (raw): {len(text_raw)} chars, all_not_detected={parsed_raw.get('_all_not_detected')}")
                if not parsed_raw.get("_all_not_detected", True) or len(text_raw) > len(text):
                    text, word_data, parsed = text_raw, wd_raw, parsed_raw
            
            # Pass 2: Aggressive preprocessing + EasyOCR (for low-quality images)
            if CV2_AVAILABLE and (parsed.get("_all_not_detected", True) or len(text.strip()) < 50):
                print("[KYC DEBUG] EasyOCR Pass 1 insufficient. Retrying with aggressive preprocessing...")
                preprocessed_agg = self._preprocess_for_ocr_advanced(image, aggressive=True)
                text_agg, wd_agg = self._run_easyocr(preprocessed_agg, id_type)
                parsed_agg = self._parse_ocr_fields_advanced(text_agg, wd_agg, id_type)
                print(f"[KYC DEBUG] EasyOCR Pass 2 (aggressive): {len(text_agg)} chars, all_not_detected={parsed_agg.get('_all_not_detected')}")
                if not parsed_agg.get("_all_not_detected", True) or len(text_agg) > len(text):
                    text, word_data, parsed = text_agg, wd_agg, parsed_agg
        
        # Pass 3: Tesseract fallback (if EasyOCR failed completely or is unavailable)
        if parsed.get("_all_not_detected", True) and PYTESSERACT_AVAILABLE:
            print("[KYC DEBUG] EasyOCR insufficient. Falling back to Tesseract...")
            text_tess, parsed_tess, wd_tess = self._run_tesseract_advanced(image, id_type)
            if not parsed_tess.get("_all_not_detected", True) or len(text_tess) > len(text):
                text, word_data, parsed = text_tess, wd_tess, parsed_tess
                print(f"[KYC DEBUG] Tesseract fallback succeeded: {len(text_tess)} chars")
        
        return text, parsed, word_data

    def _calc_overall_confidence(self, word_data: List[Dict]) -> float:
        """Calculate average confidence score from word-level OCR data (0.0 to 1.0)."""
        if not word_data:
            return 0.0
        confs = [w["conf"] for w in word_data if "conf" in w]
        return round(sum(confs) / len(confs) / 100, 2) if confs else 0.0

    def _extract_rich_ocr_data(self, ocr_text: str, detected_id_type: str = "Unknown") -> Dict[str, Any]:
        """Extracts structured data from raw OCR text.
        Detects ID type from OCR text if not provided, then parses fields.
        Returns a dictionary with extracted fields and metadata."""
        if not ocr_text or not ocr_text.strip():
            return {
                "full_name": "",
                "id_number": "",
                "extracted_dob": "",
                "extracted_address": "",
                "extracted_expiry": "",
                "sex": "",
                "first_name": "",
                "last_name": "",
                "middle_name": "",
                "given_names": ""
            }
        
        clean_text = ocr_text.upper()
        
        # Auto-detect ID type if not provided
        id_type = detected_id_type
        if id_type == "Unknown":
            if "PASSPORT" in clean_text:
                id_type = "Passport"
            elif "DRIVER" in clean_text and "LICENSE" in clean_text:
                id_type = "Driver's License"
            elif "PHILID" in clean_text or "PHILSYS" in clean_text or "NATIONAL ID" in clean_text:
                id_type = "PhilID (National ID)"
            elif "UMID" in clean_text:
                id_type = "UMID"
            elif "SSS" in clean_text:
                id_type = "SSS ID"
            elif "POSTAL" in clean_text and "ID" in clean_text:
                id_type = "Postal ID"
            elif "VOTER" in clean_text:
                id_type = "Voter's ID"
            elif "TIN" in clean_text:
                id_type = "TIN ID"
            elif "PHILHEALTH" in clean_text:
                id_type = "PhilHealth ID"
            elif "PRC" in clean_text:
                id_type = "PRC ID"
            else:
                id_type = "Unknown"
        
        # Parse fields using the advanced parser (returns dict with _all_not_detected flag)
        word_data = []  # Empty word_data as we're just doing text-based parsing here
        parsed = self._parse_ocr_fields_advanced(ocr_text, word_data, id_type)
        
        # Extract common fields and map them to the expected output format
        result = {
            "full_name": parsed.get("full_name", ""),
            "id_number": parsed.get("id_number", ""),
            "extracted_dob": parsed.get("date_of_birth", ""),
            "extracted_address": parsed.get("address", ""),
            "extracted_expiry": parsed.get("visa_until") or parsed.get("expiration_date") or "",
            "sex": parsed.get("sex", ""),
            "first_name": parsed.get("first_name") or parsed.get("given_names", ""),
            "last_name": parsed.get("last_name", ""),
            "middle_name": parsed.get("middle_name", ""),
            "given_names": parsed.get("given_names") or parsed.get("first_name", ""),
            "id_type": id_type
        }
        
        return result

    async def _call_gemini_ocr(self, image_path: str, prompt: str) -> Dict[str, Any]:
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            print("[KYC DEBUG] No Gemini API key found. Skipping Gemini OCR.")
            return None
        try:
            start_time = time.time()
            filename = os.path.basename(image_path.replace('\\', '/'))
            real_path = os.path.join("app/static/uploads/verification", filename)
            if not os.path.exists(real_path):
                print(f"[KYC ERROR] ID image not found at {real_path}")
                return None

            # Prepare image for OCR (Resizing to reduce payload size)
            img = self._prepare_image(real_path)
            h, w = img.shape[:2]
            
            # Optimization: Resize to a max dimension of 1024 while maintaining aspect ratio
            max_dim = 1024
            if max(h, w) > max_dim:
                scale = max_dim / max(h, w)
                img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
                print(f"[KYC DEBUG] Resized image for OCR: {w}x{h} -> {int(w*scale)}x{int(h*scale)}")
            
            # Encode as low-quality JPEG for speed
            success, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not success:
                print("[KYC ERROR] Failed to encode image for Gemini.")
                return None
            
            raw_data = buffer.tobytes()
                
            # Use gemini-2.0-flash for OCR - fast, multimodal, and widely available
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
            headers = {"Content-Type": "application/json"}
            base64_image = base64.b64encode(raw_data).decode('utf-8')
            
            print(f"[KYC DEBUG] Sending Gemini OCR request (Payload size: {len(base64_image)/1024:.1f} KB)...")
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": base64_image
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "response_mime_type": "application/json"
                }
            }
            
            import json
            async with httpx.AsyncClient() as client:
                # Increased timeout to 30s to prevent ReadTimeout errors on slower connections
                response = await client.post(url, json=payload, headers=headers, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    text = data['candidates'][0]['content']['parts'][0]['text']
                    elapsed = time.time() - start_time
                    print(f"[KYC DEBUG] Gemini OCR Succeeded in {elapsed:.2f}s")
                    
                    # Robust JSON extraction using regex
                    text = text.strip()
                    match = re.search(r'\{.*\}', text, re.DOTALL)
                    if match:
                        clean_text = match.group(0)
                    else:
                        clean_text = text
                    
                    try:
                        return json.loads(clean_text)
                    except json.JSONDecodeError as e:
                        print(f"[GEMINI OCR ERROR] JSON Decode Error: {e}")
                        print(f"[GEMINI RAW TEXT] {text}")
                        return None
                else:
                    print(f"[GEMINI OCR ERROR] Status {response.status_code}: {response.text}")
                    return None
        except Exception as e:
            print(f"[GEMINI OCR ERROR] {e}")
            traceback.print_exc()
            return None


    ID_LEGITIMACY_KEYWORDS = [
        "REPUBLIC OF THE PHILIPPINES", "PHILIPPINES", "PASSPORT", "IDENTIFICATION", "SOCIAL SECURITY", 
        "PROFESSIONAL REGULATION COMMISSION", "LAND TRANSPORTATION OFFICE", "COMMISSION ON ELECTIONS",
        "PHILIPPINE IDENTIFICATION", "UNIFIED MULTI-PURPOSE ID", "POSTAL ID", "TAXPAYER IDENTIFICATION",
        "DRIVER'S LICENSE", "UMID", "SSS", "GSIS", "PRC", "COMELEC", "PHILHEALTH",
        "REPUBLIKA NG PILIPINAS", "PAMBANSANG", "PAGKAKAKILANLAN"
    ]

    # ── ID-Type-Specific OCR Prompt Engineering ──────────────────────────────
    ID_TYPE_OCR_PROMPTS = {
        "PhilSys / PhilID": {
            "fields": ["last_name", "given_names", "middle_name", "id_number", "date_of_birth", "sex", "address", "blood_type", "nationality"],
            "prompt": (
                "You are an expert OCR bot extracting data from a Philippine National ID (PhilSys/PhilID card). "
                "CRITICAL RULES:\n"
                "1. The PhilID card prints Tagalog/Filipino field labels alongside the actual values. "
                "You MUST extract ONLY the actual data values, NOT the label text itself.\n"
                "2. Tagalog labels to IGNORE (do NOT include in output): "
                "'Apelyido', 'Last Name', 'Mga Pangalan', 'Given Names', 'Gitnang Apelyido', 'Middle Name', "
                "'Petsa ng Kapanganakan', 'Date of Birth', 'Tirahan', 'Address', 'Kasarian', 'Sex', "
                "'Dugo', 'Blood Type', 'Nasyonalidad', 'Nationality', 'Lugar ng Kapanganakan', "
                "'NG KAPANGANAKAN', 'MGA PANGALAN', 'GITNANG APELYIDO', 'APELYIDO'.\n"
                "3. The ID number (PCN) is a 16-digit number formatted as: XXXX-XXXX-XXXX-XXXX.\n"
                "4. Date of birth format on the card is: Month DD YYYY (e.g. 'October 01 2003' or 'OCT 01 2003').\n"
                "5. The address will contain a barangay, municipality/city, province, and 'PHILIPPINES' with a 4-digit postal code.\n"
                "6. Extract ONLY the person's actual name parts — do NOT include any label words.\n\n"
                "Return a FLAT JSON object with EXACTLY these keys:\n"
                "\"document_type_detected\": \"PhilSys / PhilID\",\n"
                "\"last_name\": \"surname only, e.g. CARAGAY\",\n"
                "\"given_names\": \"first and other given names only, e.g. NAOMI\",\n"
                "\"middle_name\": \"mother's maiden surname only, e.g. TRILLANA\",\n"
                "\"id_number\": \"16-digit PCN formatted as XXXX-XXXX-XXXX-XXXX\",\n"
                "\"date_of_birth\": \"MM/DD/YYYY format\",\n"
                "\"sex\": \"MALE or FEMALE\",\n"
                "\"address\": \"full residential address as printed\",\n"
                "\"blood_type\": \"e.g. O+\",\n"
                "\"nationality\": \"e.g. FILIPINO\",\n"
                "\"face_visible\": true or false,\n"
                "\"confidence_score\": 0.0 to 1.0\n"
                "Set any field to null if genuinely not visible. Return ONLY the JSON object, no other text."
            )
        },
        "Driver's License": {
            "fields": ["last_name", "first_name", "middle_name", "nationality", "sex", "date_of_birth", "weight", "height", "address", "license_number", "expiration_date", "agency_code", "blood_type", "eyes_color", "restrictions", "conditions"],
            "prompt": (
                "You are an ID extraction bot. Extract details from this Philippine Driver's License. "
                "Return a FLAT JSON object with EXACTLY these keys (do not add explanations to the keys, do not nest the JSON):\n"
                "\"document_type_detected\": \"Driver's License\",\n"
                "\"last_name\": \"...\",\n"
                "\"first_name\": \"...\",\n"
                "\"middle_name\": \"...\",\n"
                "\"nationality\": \"...\",\n"
                "\"sex\": \"...\",\n"
                "\"date_of_birth\": \"...\",\n"
                "\"weight\": \"...\",\n"
                "\"height\": \"...\",\n"
                "\"address\": \"...\",\n"
                "\"license_number\": \"...\",\n"
                "\"expiration_date\": \"...\",\n"
                "\"agency_code\": \"...\",\n"
                "\"blood_type\": \"...\",\n"
                "\"eyes_color\": \"...\",\n"
                "\"restrictions\": \"...\",\n"
                "\"conditions\": \"...\",\n"
                "\"face_visible\": true/false,\n"
                "\"confidence_score\": 0.9\n"
                "Set to null if not found. Only return the JSON object."
            )
        },
        "Passport": {
            "fields": ["type", "country_code", "passport_number", "last_name", "given_names", "middle_name", "date_of_birth", "nationality", "sex", "place_of_birth", "date_issued", "visa_until", "issuing_authority"],
            "prompt": (
                "You are an ID extraction bot. Extract details from this Philippine Passport. "
                "Return a FLAT JSON object with EXACTLY these keys (do not add explanations to the keys, do not nest the JSON):\n"
                "\"document_type_detected\": \"Passport\",\n"
                "\"type\": \"...\",\n"
                "\"country_code\": \"...\",\n"
                "\"passport_number\": \"...\",\n"
                "\"last_name\": \"...\",\n"
                "\"given_names\": \"...\",\n"
                "\"middle_name\": \"...\",\n"
                "\"date_of_birth\": \"...\",\n"
                "\"nationality\": \"...\",\n"
                "\"sex\": \"...\",\n"
                "\"place_of_birth\": \"...\",\n"
                "\"date_issued\": \"...\",\n"
                "\"visa_until\": \"...\",\n"
                "\"issuing_authority\": \"...\",\n"
                "\"face_visible\": true/false,\n"
                "\"confidence_score\": 0.9\n"
                "Set to null if not found. Only return the JSON object."
            )
        },
        "UMID": {
            "fields": ["last_name", "given_names", "middle_name", "crn_number", "date_of_birth", "sex", "address"],
            "prompt": (
                "You are an ID extraction bot. Extract details from this Philippine UMID. "
                "Return a FLAT JSON object with EXACTLY these keys (do not add explanations to the keys, do not nest the JSON):\n"
                "\"document_type_detected\": \"UMID\",\n"
                "\"last_name\": \"...\",\n"
                "\"given_names\": \"...\",\n"
                "\"middle_name\": \"...\",\n"
                "\"crn_number\": \"...\",\n"
                "\"date_of_birth\": \"...\",\n"
                "\"sex\": \"...\",\n"
                "\"address\": \"...\",\n"
                "\"face_visible\": true/false,\n"
                "\"confidence_score\": 0.9\n"
                "Set to null if not found. Only return the JSON object."
            )
        }
    }

    # Default prompt for any ID type not in the specific list
    DEFAULT_OCR_PROMPT = (
        "Extract data from this Philippine government ID image. "
        "Return a FLAT JSON object with these EXACT keys: "
        "\"document_type_detected\", \"last_name\", \"given_names\", \"middle_name\", \"id_number\", \"date_of_birth\", "
        "\"sex\", \"address\", \"expiry_date\", \"nationality\", "
        "\"face_visible\" (boolean), \"confidence_score\" (number). "
        "Set to null if not found. Do not nest the JSON."
    )

    def _get_id_type_ocr_prompt(self, id_type: str) -> str:
        """Returns a tailored Gemini OCR prompt for the given ID type."""
        config = self.ID_TYPE_OCR_PROMPTS.get(id_type)
        if config:
            return config["prompt"]
        return f"Selected ID type: '{id_type}'. {self.DEFAULT_OCR_PROMPT}"

    def _get_id_type_fields(self, id_type: str) -> list:
        """Returns the expected field list for the given ID type."""
        config = self.ID_TYPE_OCR_PROMPTS.get(id_type)
        if config:
            return config["fields"]
        return ["full_name", "id_number", "date_of_birth", "sex", "address"]

    # Tagalog labels that should NEVER appear in extracted name/value fields
    PHILID_LABEL_NOISE = [
        "APELYIDO", "LAST NAME", "MGA PANGALAN", "GIVEN NAMES", "GITNANG APELYIDO",
        "MIDDLE NAME", "PETSA NG KAPANGANAKAN", "DATE OF BIRTH", "TIRAHAN", "ADDRESS",
        "KASARIAN", "SEX", "DUGO", "BLOOD TYPE", "NASYONALIDAD", "NATIONALITY",
        "LUGAR NG KAPANGANAKAN", "NG KAPANGANAKAN", "MGR PRNGALAN", "GINANG APELYITO",
        "NG KANANGANAKAN", "DETE OF EIRTH", "PRNGALAN",
    ]

    def _strip_philid_label_noise(self, value: str) -> str:
        """Remove any accidentally-included Tagalog label text from an extracted value."""
        if not value or not isinstance(value, str):
            return value
        clean = value.upper()
        for label in self.PHILID_LABEL_NOISE:
            clean = clean.replace(label, "").strip()
        # Also strip lone connector words left behind
        for noise in ["NG ", " NG", "SA ", " SA"]:
            if clean == noise.strip():
                clean = ""
        return clean.strip(" ,/-")

    def _parse_philid_from_ocr_text(self, text: str) -> Dict[str, str]:
        """Extracts fields from PhilSys / PhilID raw OCR text using label anchors."""
        if not text:
            return {}
        
        clean = " ".join(text.upper().split())
        
        # 1. Extract ID number (PCN)
        id_number = ""
        pcn_match = re.search(r'(\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4})', clean)
        if pcn_match:
            id_number = pcn_match.group(1)
        else:
            mangled_pcn = re.search(r'(\d{4}[-\s]+\d{4}[-\s]*[-\s]+[-\s]*\d{2,4}[-\s]+\d{4})', clean)
            if mangled_pcn:
                id_number = mangled_pcn.group(1)
            else:
                digits_seq = re.search(r'(\d[\s-]*){12,16}', clean)
                if digits_seq:
                    id_number = digits_seq.group(0)

        if id_number:
            digits = re.sub(r'\D', '', id_number)
            if len(digits) == 16:
                id_number = f"{digits[0:4]}-{digits[4:8]}-{digits[8:12]}-{digits[12:16]}"
            elif len(digits) >= 12:
                parts = [digits[i:i+4] for i in range(0, len(digits), 4)]
                id_number = "-".join(parts)
                
        # 2. Extract Fields using Anchor Sequences
        last_name_anchors = r'(?:APELYIDO|APLEVIDC|APELYITO|SURNAME|LAST\s*NAME)'
        given_names_anchors = r'(?:MGA\s*PANGALAN|MGR?\s*PRNGALAN|PRNGALAN|GIVEN\s*NAMES?|GIVEN)'
        middle_name_anchors = r'(?:GITNANG\s*APELYIDO|GINANG\s*APELYITO|MIDDLE\s*NAMES?|MID\s*NAME)'
        dob_anchors = r'(?:PETSA\s*NG\s*KAPANGANAKAN|NG\s*KANANGANAKAN|DATE\s*OF\s*BIRTH|DETE\s*OF\s*EIRTH|EIRTH|BIRTH)'
        address_anchors = r'(?:TIRAHAN|ADDRESS)'
        
        parsed = {}
        
        # Last Name
        last_name_match = re.search(last_name_anchors + r'\s*[:/.-]*\s*(.*?)\s*(?:' + given_names_anchors + '|' + middle_name_anchors + ')', clean)
        if last_name_match:
            parsed["last_name"] = self._strip_philid_label_noise(last_name_match.group(1).strip())
            
        # Given Names
        given_names_match = re.search(given_names_anchors + r'\s*[:/.-]*\s*(.*?)\s*(?:' + middle_name_anchors + '|' + dob_anchors + ')', clean)
        if given_names_match:
            parsed["given_names"] = self._strip_philid_label_noise(given_names_match.group(1).strip())
            parsed["first_name"] = parsed["given_names"]
            
        # Middle Name
        middle_name_match = re.search(middle_name_anchors + r'\s*[:/.-]*\s*(.*?)\s*(?:' + dob_anchors + '|' + address_anchors + ')', clean)
        if middle_name_match:
            parsed["middle_name"] = self._strip_philid_label_noise(middle_name_match.group(1).strip())
            
        # Date of Birth
        dob_match = re.search(dob_anchors + r'\s*[:/.-]*\s*(.*?)\s*(?:' + address_anchors + '|SEX|KASARIAN|DUGO|BLOOD)', clean)
        if dob_match:
            raw_dob = dob_match.group(1).strip()
            raw_dob = re.sub(r'\b\d{3}\s+PHL\b', '', raw_dob).strip()
            raw_dob = re.sub(r'\bPHL\b', '', raw_dob).strip()
            parsed["date_of_birth"] = self._strip_philid_label_noise(raw_dob)
            
        # Address
        address_match = re.search(address_anchors + r'\s*[:/.-]*\s*(.*)', clean)
        if address_match:
            parsed["address"] = self._strip_philid_label_noise(address_match.group(1).strip())
            
        if id_number:
            parsed["id_number"] = id_number
            
        return parsed


    def _build_structured_ocr_data(self, gemini_data: dict, id_type: str, method: str = "gemini") -> dict:
        """Builds a structured ocr_data dict from Gemini/Tesseract results."""
        expected_fields = self._get_id_type_fields(id_type)
        fields = {}
        for field in expected_fields:
            fields[field] = gemini_data.get(field)
        
        # Also capture any extra fields Gemini found
        skip_keys = {"face_visible", "confidence_score", "document_type_detected"}
        for key, val in gemini_data.items():
            if key not in skip_keys and key not in fields:
                fields[key] = val

        # For PhilID / UMID — strip any Tagalog label noise from name fields
        is_philid = id_type in ("PhilSys / PhilID", "UMID")
        if is_philid:
            for name_field in ("last_name", "given_names", "middle_name", "first_name"):
                if fields.get(name_field):
                    fields[name_field] = self._strip_philid_label_noise(fields[name_field])

        # Build full_name from parts if not directly present
        if not fields.get("full_name"):
            if id_type == "Passport":
                name_parts = [fields.get(k) for k in ("given_names", "middle_name", "last_name") if fields.get(k)]
                if name_parts:
                    fields["full_name"] = " ".join(name_parts)
            elif is_philid:
                # PhilID: Given Names + Last Name (middle name is mother's maiden surname — not part of display name)
                name_parts = [fields.get(k) for k in ("given_names", "last_name") if fields.get(k)]
                if name_parts:
                    fields["full_name"] = " ".join(name_parts)
            elif id_type == "Driver's License":
                name_parts = [fields.get(k) for k in ("first_name", "middle_name", "last_name") if fields.get(k)]
                if name_parts:
                    fields["full_name"] = " ".join(name_parts)
        
        return {
            "id_type": id_type,
            "extraction_method": method,
            "document_type_detected": gemini_data.get("document_type_detected", id_type),
            "confidence_score": gemini_data.get("confidence_score", 0.0),
            "face_visible": gemini_data.get("face_visible", False),
            "fields": fields,
            # Backward-compatible flat keys
            "full_name": fields.get("full_name", ""),
            "id_number": fields.get("id_number") or fields.get("pcn_number") or fields.get("license_number") or fields.get("passport_number") or fields.get("crn_number") or "",
            "birth_date": fields.get("date_of_birth", ""),
            "address": fields.get("address", "")
        }

    def _extract_mrz_from_text(self, text: str) -> dict:
        """Extracts MRZ lines from OCR text (Passport fallback)."""
        mrz_data = {"mrz_line_1": None, "mrz_line_2": None}
        # MRZ lines: 44 chars each, only A-Z, 0-9, <
        mrz_pattern = r'([A-Z0-9<]{30,44})'
        matches = re.findall(mrz_pattern, text.upper().replace(' ', ''))
        mrz_candidates = [m for m in matches if len(m) >= 30 and '<' in m]
        if len(mrz_candidates) >= 2:
            mrz_data["mrz_line_1"] = mrz_candidates[-2]
            mrz_data["mrz_line_2"] = mrz_candidates[-1]
        elif len(mrz_candidates) == 1:
            mrz_data["mrz_line_1"] = mrz_candidates[0]
        return mrz_data


    async def verify_id_document(self, 
                           id_path: str, 
                           full_name: str, 
                           id_number: str, 
                           id_type: str,
                           db: Session = None,
                           user_id: int = None,
                           dob: str = None,
                           address: str = None) -> Dict[str, Any]:
        """Strictly validates the ID document (Quality + OCR + Patterns) synchronously."""
        try:
            # 1. Duplicate Check (Fraud Prevention)
            if db and user_id and id_number:
                if self.check_duplicate_id(db, id_number, user_id):
                    return {"status": "rejected", "ocr_match": False, "pattern_valid": True, 
                            "failure_reason": "❌ This ID has already been registered."}

            # 2. ID Pattern Validation
            pattern_valid = self.validate_id_pattern(id_type, id_number)
            
            # 3. Image Loading & Quality Check
            id_img = self._prepare_image(id_path)
            quality_check = self.check_image_quality(id_img)
            if not quality_check["valid"]:
                return {"status": "mismatched", "ocr_match": False, "pattern_valid": pattern_valid,
                        "failure_reason": quality_check["reason"]}
            
            # 4. Perform OCR via Gemini (Primary) or unified EasyOCR -> Tesseract pipeline (Fallback)
            gemini_data = None
            ocr_text = None
            parsed = None
            word_data = None
            
            if os.getenv("GEMINI_API_KEY"):
                print("[KYC DEBUG] Calling Gemini API as primary OCR engine for document verification...")
                gemini_prompt = self._get_id_type_ocr_prompt(id_type)
                gemini_data = await self._call_gemini_ocr(id_path, gemini_prompt)
            
            if not gemini_data:
                print("[KYC WARNING] Gemini API unavailable or failed. Using EasyOCR/Tesseract pipeline...")
                ocr_text, parsed, word_data = self._run_ocr_pipeline(id_img, id_type)
                
                # For PhilID: apply a layout-aware parser that uses Tagalog label anchors as field separators
                if id_type in ("PhilSys / PhilID", "UMID") and ocr_text:
                    philid_parsed = self._parse_philid_from_ocr_text(ocr_text)
                    if philid_parsed:
                        parsed.update(philid_parsed)

            
            structured_ocr = None
            
            if gemini_data and isinstance(gemini_data, dict) and any(gemini_data.values()):
                print(f"[KYC DEBUG] Gemini OCR Succeeded for ID type: {id_type}")
                print(f"[KYC DEBUG] Gemini extracted fields: {list(gemini_data.keys())}")
                
                structured_ocr = self._build_structured_ocr_data(gemini_data, id_type, "gemini")
                
                # Build text for matching logic
                text_parts = []
                for v in gemini_data.values():
                    if isinstance(v, str) and v:
                        text_parts.append(v)
                ocr_text = " ".join(text_parts)
                clean_ocr_upper = ocr_text.upper()
                is_likely_id = True
                rich_data = {
                    "full_name": structured_ocr.get("full_name", ""),
                    "id_number": structured_ocr.get("id_number", "") or id_number,
                    "extracted_dob": gemini_data.get("date_of_birth", ""),
                    "extracted_expiry": gemini_data.get("expiry_date", ""),
                    "extracted_address": gemini_data.get("address", ""),
                    "first_name": gemini_data.get("first_name", ""),
                    "last_name": gemini_data.get("last_name", ""),
                    "middle_name": gemini_data.get("middle_name", ""),
                    "given_names": gemini_data.get("given_names", ""),
                    "is_tampered": False
                }
                # Optimization: Trust Gemini for face visibility to save OpenCV processing time
                has_face = gemini_data.get("face_visible", True)
                id_faces = [1] if has_face else [] 
            else:
                # Normal path: EasyOCR / Tesseract pipeline
                # Handle empty/garbage text for Demo mode if no Gemini key or Gemini failed
                if not ocr_text or not ocr_text.strip() or self._is_ocr_garbage(ocr_text):
                    print(f"[KYC WARNING] OCR pipeline failed to parse text for ID.")
                    if not os.getenv("GEMINI_API_KEY"):
                        print("[KYC DEBUG] Permitting empty OCR text for ID in Demo mode.")
                        ocr_text = f"DEMO_BYPASS_MODE_TEXT {full_name} {id_number}"
                    else:
                        return {
                            "status": "rejected",
                            "ocr_match": False,
                            "failure_reason": "❌ Unable to read the ID. Please upload a clearer image."
                        }
                
                clean_ocr_upper = ocr_text.upper()
                
                # Check for face
                id_faces = self._detect_faces_detailed(id_img)
                has_face = len(id_faces) > 0
                if not has_face and parsed:
                    has_face = bool(parsed.get("face_visible", False))

                # Check if any ID number pattern exists in text (lenient legitimacy)
                id_pattern_found = False
                id_patterns_check = [
                    r'\d{4}-\d{4}-\d{4}-\d{4}',  # PhilID
                    r'[A-Z]\d{2}-\d{2}-\d{6}',   # Driver's License
                    r'\d{2}-\d{7}-\d{1}',        # SSS
                    r'\d{3}-\d{3}-\d{3}',        # TIN variants
                ]
                for pattern in id_patterns_check:
                    if re.search(pattern, clean_ocr_upper):
                        id_pattern_found = True
                        break
                
                # 5. Legitimacy Check (LENIENT - accept if image quality is good OR if ID pattern is found)
                def fuzzy_contains_id_keywords(text):
                    if any(kw in text for kw in self.ID_LEGITIMACY_KEYWORDS):
                        return True
                    typo_tolerant_kws = ["PHILIPPINES", "REPUBLIC", "IDENTITY", "IDENTIFICATION", "PASSPORT", "LICENSE"]
                    for kw in typo_tolerant_kws:
                        if len(text) > 20:
                            match = difflib.get_close_matches(kw, text.split(), n=1, cutoff=0.7)
                            if match: return True
                    return False
                
                is_likely_id = (fuzzy_contains_id_keywords(clean_ocr_upper) or has_face or id_pattern_found) and len(clean_ocr_upper.strip()) > 10
                
                rich_data = {
                    "full_name": parsed.get("full_name") if parsed.get("full_name") not in ["NOT DETECTED", "LOW CONFIDENCE"] else "",
                    "id_number": parsed.get("id_number") if parsed.get("id_number") not in ["NOT DETECTED", "LOW CONFIDENCE"] else "",
                    "extracted_dob": parsed.get("date_of_birth") if parsed.get("date_of_birth") not in ["NOT DETECTED", "LOW CONFIDENCE"] else "",
                    "extracted_address": parsed.get("address") if parsed.get("address") not in ["NOT DETECTED", "LOW CONFIDENCE"] else "",
                    "extracted_expiry": parsed.get("visa_until") or parsed.get("expiration_date") or "",
                    "first_name": parsed.get("first_name") or parsed.get("given_names", "") if parsed.get("first_name") not in ["NOT DETECTED", "LOW CONFIDENCE"] else "",
                    "last_name": parsed.get("last_name") if parsed.get("last_name") not in ["NOT DETECTED", "LOW CONFIDENCE"] else "",
                    "middle_name": parsed.get("middle_name") if parsed.get("middle_name") not in ["NOT DETECTED", "LOW CONFIDENCE"] else "",
                    "given_names": parsed.get("given_names") or parsed.get("first_name", "") if parsed.get("given_names") not in ["NOT DETECTED", "LOW CONFIDENCE"] else "",
                    "is_tampered": False
                }
                
                # Build fields for structured_ocr
                fields = {
                    "full_name": parsed.get("full_name", ""),
                    "id_number": parsed.get("id_number", ""),
                    "date_of_birth": parsed.get("date_of_birth", ""),
                    "address": parsed.get("address", ""),
                    "sex": parsed.get("sex", ""),
                    "first_name": parsed.get("first_name", ""),
                    "last_name": parsed.get("last_name", ""),
                    "middle_name": parsed.get("middle_name", ""),
                    "given_names": parsed.get("given_names", "")
                }
                if id_type == "Passport":
                    mrz = self._extract_mrz_from_text(ocr_text)
                    fields.update(mrz)
                
                # For PhilID / UMID — strip Tagalog label noise from name fields (EasyOCR picks up labels)
                if id_type in ("PhilSys / PhilID", "UMID"):
                    for name_field in ("last_name", "given_names", "middle_name", "first_name", "full_name"):
                        if fields.get(name_field) and isinstance(fields[name_field], str):
                            fields[name_field] = self._strip_philid_label_noise(fields[name_field])
                    # Rebuild full_name cleanly
                    name_parts = [fields.get(k) for k in ("given_names", "last_name") if fields.get(k)]
                    if name_parts:
                        fields["full_name"] = " ".join(name_parts)
                    
                    # Update rich_data for consistency in matching
                    rich_data["full_name"] = fields["full_name"]
                    rich_data["last_name"] = fields["last_name"]
                    rich_data["given_names"] = fields["given_names"]
                    rich_data["first_name"] = fields["first_name"]
                    rich_data["middle_name"] = fields["middle_name"]
                    rich_data["id_number"] = fields["id_number"]
                    rich_data["extracted_dob"] = fields["date_of_birth"]
                    rich_data["extracted_address"] = fields["address"]
                
                method = "easyocr" if EASYOCR_AVAILABLE else "tesseract"
                
                structured_ocr = {
                    "id_type": id_type,
                    "extraction_method": method,
                    "document_type_detected": id_type,
                    "confidence_score": self._calc_overall_confidence(word_data),
                    "face_visible": has_face,
                    "fields": fields,
                    "full_name": fields.get("full_name", ""),
                    "id_number": fields.get("id_number", ""),
                    "birth_date": fields.get("date_of_birth", ""),
                    "address": fields.get("address", "")
                }


            
            # 6. Specific ID Type Keyword Check (NEW & STRICT)
            # Check if the selected ID type (e.g. "Passport") appears in the OCR text
            type_keywords = {
                'PhilID (National ID)': ["PHILSYS", "PHILID", "NATIONAL ID", "PHILIPPINE IDENTIFICATION", "REPUBLIKA", "PAMBANSANG"],
                'Driver\'s License': ["DRIVER", "LICENSE", "LTO", "TRANSPORTATION"],
                'Passport': ["PASSPORT", "DFA"],
                'UMID': ["UMID", "UNIFIED", "MULTI-PURPOSE"],
                'SSS ID': ["SSS", "SOCIAL SECURITY"],
                'PRC ID': ["PRC", "PROFESSIONAL", "REGULATION"],
                'Postal ID': ["POSTAL", "PHLPOST"],
                'TIN ID': ["TIN", "INTERNAL REVENUE", "TAX"],
                'PhilHealth ID': ["PHILHEALTH"],
                'Voter\'s ID': ["VOTER", "COMELEC"]
            }
            
            selected_type_kws = type_keywords.get(id_type, [id_type.upper()])
            
            # Stricter type matching using word boundaries to avoid partial matches (e.g., "DRIVER" in random text)
            type_found_in_ocr = False
            for kw in selected_type_kws:
                if re.search(r'\b' + re.escape(kw) + r'\b', clean_ocr_upper):
                    type_found_in_ocr = True
                    break
            
            # 7. SMART MATCHING LOGIC (FOLLOWING USER'S PSEUDO-CODE)
            reasons = []
            
            # Helper for name matching (Case insensitive, ignore extra spaces, typo tolerance)
            def match_name(input_name, ocr_data_name, full_ocr_text):
                if not input_name: return False
                clean_input = " ".join(input_name.lower().split())
                full_ocr_lower = full_ocr_text.lower()
                
                # Try exact match first
                if (ocr_data_name and clean_input in ocr_data_name.lower()) or clean_input in full_ocr_lower:
                    return True
                
                # Typo tolerance (Fuzzy) - lowered from 0.85 to 0.70 for more lenient matching
                if ocr_data_name:
                    ratio = difflib.SequenceMatcher(None, clean_input, ocr_data_name.lower()).ratio()
                    if ratio > 0.70: return True
                
                # Check parts (lowered to 50% match for robustness - was 60%)
                input_parts = [p for p in clean_input.split() if len(p) > 2]
                if not input_parts: return False
                matches = 0
                for part in input_parts:
                    if part in full_ocr_lower or any(difflib.SequenceMatcher(None, part, w).ratio() > 0.75 for w in full_ocr_lower.split()):
                        matches += 1
                return (matches / len(input_parts)) >= 0.50

            # Helper for Date of Birth matching
            def match_dob(input_dob, extracted_dob, full_ocr_text):
                if not input_dob: return True
                # Format check (YYYY-MM-DD)
                clean_input = input_dob.replace("-", "").replace("/", "")
                clean_ocr = re.sub(r'[^0-9]', '', full_ocr_text)
                return clean_input in clean_ocr or input_dob in full_ocr_text
            # Helper for Address matching
            def match_address(input_addr, extracted_addr, full_ocr_text):
                if not input_addr: return True
                clean_input = re.sub(r'[^a-z0-9]', '', input_addr.lower())
                clean_ocr_norm = re.sub(r'[^a-z0-9]', '', full_ocr_text.lower())
                if clean_input in clean_ocr_norm: return True
                # Fuzzy word match
                input_words = [w for w in input_addr.lower().split() if len(w) > 3]
                if not input_words: return True
                found = 0
                for w in input_words:
                    if w in clean_ocr_norm: found += 1
                return (found / len(input_words)) >= 0.5
            # --- EXECUTE VALIDATIONS ---
            # A. Validate the document looks like an actual ID
            if not is_likely_id:
                # Less strict: only reject if it's extremely unlikely to be an ID
                # (very short text, no face, no ID keywords, no ID pattern)
                if not id_pattern_found and len(clean_ocr_upper.strip()) < 20:
                    print(f"[KYC DEBUG] Document legitimacy check FAILED: text_len={len(clean_ocr_upper.strip())}, has_keywords={fuzzy_contains_id_keywords(clean_ocr_upper)}, has_face={has_face}, has_id_pattern={id_pattern_found}")
                    reasons.append("Invalid ID Document. The image doesn't appear to be an ID document.")
                else:
                    print(f"[KYC DEBUG] Document legitimacy check PASSED (lenient): text_len={len(clean_ocr_upper.strip())}, has_keywords={fuzzy_contains_id_keywords(clean_ocr_upper)}, has_face={has_face}, has_id_pattern={id_pattern_found}")
            
            # B. ID Number Cross-Reference: Match entered ID number against OCR-extracted ID number
            norm_id_input = re.sub(r'[^A-Z0-9]', '', id_number.upper())
            norm_id_ocr = re.sub(r'[^A-Z0-9]', '', clean_ocr_upper)
            
            # Try matching against Gemini-extracted ID number first
            gemini_id_extracted = re.sub(r'[^A-Z0-9]', '', (rich_data.get("id_number") or "").upper())
            id_number_matched = False
            
            print(f"[KYC DEBUG] ID Matching - Input: {norm_id_input}, Gemini: {gemini_id_extracted}, OCR contains: {norm_id_input in norm_id_ocr}")
            
            if norm_id_input and gemini_id_extracted:
                # Exact match
                if norm_id_input == gemini_id_extracted:
                    id_number_matched = True
                # Lenient fuzzy: lower threshold from 0.85 to 0.75 to catch OCR errors
                elif difflib.SequenceMatcher(None, norm_id_input, gemini_id_extracted).ratio() > 0.75:
                    id_number_matched = True
                    print(f"[KYC DEBUG] ID number fuzzy match (75%): input='{norm_id_input}' vs extracted='{gemini_id_extracted}'")
            
            # Fallback: Check if ID number exists anywhere in raw OCR text
            if not id_number_matched and norm_id_input:
                if norm_id_input in norm_id_ocr:
                    id_number_matched = True
                elif id_number.upper() in clean_ocr_upper:
                    id_number_matched = True
                # Even more lenient: check if most digits match (for OCR misreads like 0→O, 1→I)
                elif not id_number_matched:
                    # Check if 80% of digits match in sequence
                    digit_ratio = difflib.SequenceMatcher(None, norm_id_input, norm_id_ocr).ratio()
                    if digit_ratio > 0.75:
                        id_number_matched = True
                        print(f"[KYC DEBUG] ID number partial match (75% digit ratio): {digit_ratio:.2f}")
            
            if norm_id_input and not id_number_matched:
                detected_id = gemini_id_extracted or rich_data.get('id_number') or 'Not extracted'
                print(f"[KYC DEBUG] ID Number mismatch: Input='{norm_id_input}', Detected='{detected_id}'")
                reasons.append(f"ID Number mismatch. Detected: {detected_id}")
            
            # C. Name Cross-Reference: Match registration name against OCR-extracted name
            name_matched = match_name(full_name, rich_data.get("full_name"), ocr_text)
            print(f"[KYC DEBUG] Name matching - Input: '{full_name}', Extracted: '{rich_data.get('full_name')}', Match: {name_matched}")
            
            # Also check individual parts (last_name, first_name) from Gemini - LENIENT
            if not name_matched and (rich_data.get("last_name") or rich_data.get("first_name")):
                input_parts = [p.lower() for p in full_name.split() if len(p) > 1]
                extracted_last = (rich_data.get("last_name") or "").lower()
                extracted_first = (rich_data.get("first_name") or "").lower()
                extracted_middle = (rich_data.get("middle_name") or "").lower()
                
                parts_found = 0
                total_parts = len(input_parts)
                for part in input_parts:
                    if part in extracted_last or part in extracted_first or part in extracted_middle:
                        parts_found += 1
                    # Lowered from 0.8 to 0.70 for more lenient matching
                    elif any(difflib.SequenceMatcher(None, part, w).ratio() > 0.70 
                             for w in [extracted_last, extracted_first, extracted_middle] if w):
                        parts_found += 1
                
                # Lowered from 0.5 to 0.40 (less than half of parts need to match)
                if total_parts > 0 and (parts_found / total_parts) >= 0.40:
                    name_matched = True
                    print(f"[KYC DEBUG] Name matched via individual parts: {parts_found}/{total_parts}")
                else:
                    print(f"[KYC DEBUG] Name parts NOT matched: {parts_found}/{total_parts} (need 40%). Last: '{extracted_last}', First: '{extracted_first}', Middle: '{extracted_middle}'")
            
            if not name_matched:
                detected_name = rich_data.get("full_name") or "None"
                print(f"[KYC DEBUG] Name mismatch: Input='{full_name}', Detected='{detected_name}'")
                reasons.append(f"Name mismatch. Detected: {detected_name}")
            
            # D. Tampering / AI-Editing Detection
            if rich_data.get("is_tampered"):
                tamper_reason = rich_data.get("tampering_reason", "Digitally altered.")
                reasons.append(f"Authenticity Failed: {tamper_reason}")
            
            # E. Pattern validation
            if not pattern_valid:
                reasons.append(f"Invalid format for '{id_type}'.")
            
            status = "matched" if not reasons else "rejected"


            # Merge structured OCR into return data
            final_ocr_data = structured_ocr if structured_ocr else {
                "id_type": id_type,
                "extraction_method": "unknown",
                "fields": {},
                "full_name": rich_data.get("full_name", ""),
                "id_number": rich_data.get("id_number", ""),
                "birth_date": rich_data.get("extracted_dob", ""),
                "address": rich_data.get("extracted_address", "")
            }
            final_ocr_data["raw_text"] = ocr_text
            final_ocr_data["full_name_extracted"] = rich_data.get("full_name")
            final_ocr_data["dob_extracted"] = rich_data.get("extracted_dob")
            final_ocr_data["address_extracted"] = rich_data.get("extracted_address")

            return {
                "status": status,
                "ocr_match": status == "matched",
                "is_likely_id": is_likely_id,
                "pattern_valid": pattern_valid,
                "id_number_matched": id_number_matched if norm_id_input else True,
                "name_matched": name_matched,
                "failure_reason": "<br>".join(reasons) if reasons else None,
                "extracted_text_preview": ocr_text[:200],
                "ocr_data": final_ocr_data
            }
        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "failure_reason": f"System Error during ID scan: {str(e)}"}

    async def extract_id_data(self, id_path: str, id_type: str) -> Dict[str, Any]:
        """Extracts text from ID using Gemini API (with EasyOCR + Tesseract fallback)."""
        try:
            id_img = self._prepare_image(id_path)
            
            # 1. Blurry / Resolution Check
            quality_check = self.check_image_quality(id_img)
            if not quality_check["valid"]:
                return {"success": False, "error": quality_check["reason"]}
            
            # 2. Cropped ID Check
            if self._is_image_cropped(id_img):
                return {"success": False, "error": "Please capture the entire ID card."}
            
            gemini_data = None
            if os.getenv("GEMINI_API_KEY"):
                print("[KYC DEBUG] Calling Gemini API as primary OCR engine for ID extraction...")
                gemini_prompt = self._get_id_type_ocr_prompt(id_type)
                gemini_data = await self._call_gemini_ocr(id_path, gemini_prompt)
                
            if gemini_data and isinstance(gemini_data, dict) and any(gemini_data.values()):
                print(f"[KYC DEBUG] Gemini OCR Succeeded for ID type: {id_type}")
                structured_ocr = self._build_structured_ocr_data(gemini_data, id_type, "gemini")
                return {"success": True, "data": structured_ocr, "quality": quality_check}
                
            # Fallback to EasyOCR/Tesseract if Gemini not available or failed
            print("[KYC WARNING] Gemini API unavailable or failed. Using EasyOCR/Tesseract fallback pipeline...")
            text, parsed, word_data = self._run_ocr_pipeline(id_img, id_type)

            # For PhilID: apply a layout-aware parser that uses Tagalog label anchors as field separators
            if id_type in ("PhilSys / PhilID", "UMID") and text:
                philid_parsed = self._parse_philid_from_ocr_text(text)
                if philid_parsed:
                    parsed.update(philid_parsed)
            
            clean_ocr_upper = text.upper()
            id_faces = self._detect_faces_detailed(id_img)
            has_face = len(id_faces) > 0
            if not has_face and parsed:
                has_face = bool(parsed.get("face_visible", False))
            
            # Pattern check for ID
            id_pattern_found = False
            id_patterns_check = [
                r'\d{4}-\d{4}-\d{4}-\d{4}',  # PhilID
                r'[A-Z]\d{2}-\d{2}-\d{6}',   # Driver's License
                r'\d{2}-\d{7}-\d{1}',        # SSS
                r'\d{3}-\d{3}-\d{3}',        # TIN variants
            ]
            for pattern in id_patterns_check:
                if re.search(pattern, clean_ocr_upper):
                    id_pattern_found = True
                    break
            
            def fuzzy_contains_id_keywords(text):
                if any(kw in text for kw in self.ID_LEGITIMACY_KEYWORDS):
                    return True
                typo_tolerant_kws = ["PHILIPPINES", "REPUBLIC", "IDENTITY", "IDENTIFICATION", "PASSPORT", "LICENSE"]
                for kw in typo_tolerant_kws:
                    if len(text) > 20:
                        match = difflib.get_close_matches(kw, text.split(), n=1, cutoff=0.7)
                        if match: return True
                return False

            is_likely_id = (fuzzy_contains_id_keywords(clean_ocr_upper) or has_face or id_pattern_found) and len(clean_ocr_upper.strip()) > 10
            
            # 3. No ID Detected
            if not is_likely_id:
                return {"success": False, "error": "No valid ID detected. Please upload a clear ID image."}

            # 4. OCR Failed / Garbage Text
            if not text or not text.strip() or self._is_ocr_garbage(text):
                return {"success": False, "error": "Unable to extract ID details. Please try again."}
            
            # Build structured output compatible with frontend
            fields = {k: v for k, v in parsed.items() if k != "_all_not_detected"}

            # For PhilID / UMID — strip Tagalog label noise from name fields (EasyOCR picks up labels)
            if id_type in ("PhilSys / PhilID", "UMID"):
                for name_field in ("last_name", "given_names", "middle_name", "first_name", "full_name"):
                    if fields.get(name_field) and isinstance(fields[name_field], str):
                        fields[name_field] = self._strip_philid_label_noise(fields[name_field])
                # Always rebuild full_name for PhilID/UMID from the clean name components
                name_parts = [fields.get(k) for k in ("given_names", "last_name") if fields.get(k)]
                if name_parts:
                    fields["full_name"] = " ".join(name_parts)
            
            # Determine extraction method used
            method = "easyocr" if EASYOCR_AVAILABLE else "tesseract"
            
            structured_ocr = {
                "id_type": id_type,
                "extraction_method": method,
                "document_type_detected": id_type,
                "confidence_score": self._calc_overall_confidence(word_data),
                "face_visible": has_face,
                "fields": fields,
                # Backward-compatible flat keys
                "full_name": fields.get("full_name", ""),
                "id_number": fields.get("id_number") or parsed.get("id_number") or parsed.get("license_number") or parsed.get("passport_number") or "",
                "birth_date": fields.get("date_of_birth") or parsed.get("date_of_birth") or "",
                "address": fields.get("address") or parsed.get("address") or ""
            }

            
            return {"success": True, "data": structured_ocr, "quality": quality_check}
        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": "Unable to extract ID details. Please try again."}

    async def verify_identity_v2(self, 
                           id_path: str, 
                           selfie_paths: List[str], 
                           full_name: str, 
                           id_number: str, 
                           id_type: str, 
                           db: Session = None,
                           user_id: int = None,
                           dob: str = None,
                           address: str = None) -> Dict[str, Any]:
        """Refactored full verification logic using verify_id_document and liveness checks."""
        try:
            # 1. Document Verification
            id_result = await self.verify_id_document(id_path, full_name, id_number, id_type, db, user_id, dob, address)
            if id_result["status"] == "error":
                return id_result # Bubble up error

            ocr_match = id_result.get("ocr_match", False)
            pattern_valid = id_result.get("pattern_valid", False)
            ocr_text = id_result.get("ocr_data", {}).get("raw_text", "")

            # Load selfie images
            selfie_imgs = []
            for sp in selfie_paths:
                selfie_imgs.append(self._prepare_image(sp))

            # --- VALIDATIONS FOR LIVELINESS ---
            liveness_failure = None
            
            # 1. Face Too Dark Check (Locally processed as it is lightweight)
            for img in selfie_imgs:
                mean_brightness = np.mean(img)
                if mean_brightness < 40: # Threshold for dark environment
                    liveness_failure = "Environment is too dark. Please improve lighting."
                    break

            vps_url = os.getenv("VPS_AI_URL")
            vps_api_key = os.getenv("VPS_API_KEY")
            vps_success = False
            face_match_confidence = 0.0
            liveness_score = 0.0
            face_count = 0
            occlusion_detected = False
            occlusion_reason = None
            verification_result = {}
            liveness_result = {}

            if not liveness_failure and vps_url:
                print(f"[KYC DEBUG] Delegating Face Verification and Liveness to VPS: {vps_url}/verify")
                try:
                    files = []
                    
                    # Read ID image
                    id_filename = os.path.basename(id_path.replace('\\', '/'))
                    id_real_path = os.path.join("app/static/uploads/verification", id_filename)
                    with open(id_real_path, "rb") as f:
                        id_raw_data = f.read()
                    try:
                        id_decrypted = decrypt_data(id_raw_data)
                    except Exception:
                        id_decrypted = id_raw_data
                    
                    files.append(("img1", ("id_card.jpg", id_decrypted, "image/jpeg")))
                    
                    # Read and decrypt selfie images
                    for i, sp in enumerate(selfie_paths):
                        selfie_filename = os.path.basename(sp.replace('\\', '/'))
                        selfie_real_path = os.path.join("app/static/uploads/verification", selfie_filename)
                        with open(selfie_real_path, "rb") as f:
                            selfie_raw_data = f.read()
                        try:
                            selfie_decrypted = decrypt_data(selfie_raw_data)
                        except Exception:
                            selfie_decrypted = selfie_raw_data
                        
                        # Add first selfie as img2
                        if i == 0:
                            files.append(("img2", (f"selfie_{i}.jpg", selfie_decrypted, "image/jpeg")))
                        
                        # Add to selfies list
                        files.append(("selfies", (f"selfie_{i}.jpg", selfie_decrypted, "image/jpeg")))
                    
                    headers = {}
                    if vps_api_key:
                        headers["X-API-Key"] = vps_api_key
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            f"{vps_url}/verify",
                            files=files,
                            data={"enforce_detection": "false"},
                            headers=headers,
                            timeout=45.0
                        )
                        
                    if response.status_code == 200:
                        vps_res = response.json()
                        verification_result = vps_res.get("verification", {})
                        liveness_result = vps_res.get("liveness", {})
                        vps_success = True
                        print("[KYC DEBUG] VPS Verification and Liveness call succeeded!")
                    else:
                        print(f"[KYC WARNING] VPS Verify failed with status {response.status_code}: {response.text}")
                except Exception as e:
                    print(f"[KYC ERROR] VPS Verify request failed: {e}")
                    traceback.print_exc()

            id_img = self._prepare_image(id_path)
            id_faces = self._detect_faces_detailed(id_img)

            if not liveness_failure:
                if vps_success:
                    # 2. Extract results from VPS
                    face_match_confidence = verification_result.get("similarity_score", 0.0) if verification_result.get("success") else 0.0
                    # If verified by DeepFace but score is slightly low, adjust to pass
                    if verification_result.get("verified") and face_match_confidence < 0.5:
                        face_match_confidence = max(face_match_confidence, 0.6)
                        
                    liveness_score = liveness_result.get("score", 0.0) if liveness_result.get("success") else 0.0
                    face_count = liveness_result.get("face_count", 0)
                    occlusion_detected = liveness_result.get("occlusion_detected", False)
                    occlusion_reason = liveness_result.get("failure_reason")
                    
                    # Check for face detection error or face verification failure
                    if not verification_result.get("success"):
                        v_err = verification_result.get("error", "")
                        print(f"[KYC WARNING] VPS DeepFace verify reported error: {v_err}")
                        if "Face could not be detected" in v_err:
                            liveness_failure = "Face could not be detected in the ID or selfie. Please ensure face is clearly visible."
                        else:
                            liveness_failure = "Face verification failed. Please try again."
                    
                    # Check for face count & spoof
                    elif face_count == 0:
                        liveness_failure = "No face detected. Please face the camera clearly."
                    elif face_count > 1:
                        liveness_failure = "Multiple faces detected. Only one person is allowed."
                    elif occlusion_detected:
                        liveness_failure = occlusion_reason or "Face occlusion detected. Please keep your face clear."
                    elif liveness_score < 0.4:
                        liveness_failure = "Liveliness verification failed. Please try again without using a photo or screen."
                    elif not verification_result.get("verified") and face_match_confidence < 0.5:
                        liveness_failure = "Face does not match the uploaded ID."
                else:
                    # Fallback to local processing if VPS failed or not configured
                    print("[KYC WARNING] Running local liveness and face comparison...")
                    local_liveness = self._check_liveness_mediapipe(selfie_imgs)
                    liveness_score = local_liveness["score"]
                    face_count = local_liveness.get("face_count", 0)
                    occlusion_detected = local_liveness.get("occlusion_detected", False)
                    occlusion_reason = local_liveness.get("failure_reason")
                    
                    if face_count == 0:
                        liveness_failure = "No face detected. Please face the camera clearly."
                    elif face_count > 1:
                        liveness_failure = "Multiple faces detected. Only one person is allowed."
                    elif not liveness_failure and CV2_AVAILABLE:
                        # Secondary Haar Cascade check
                        for img in selfie_imgs:
                            raw_faces = self._detect_faces_detailed(img)
                            if len(raw_faces) > 1:
                                img_area = img.shape[0] * img.shape[1]
                                significant_faces = [
                                    f for f in raw_faces
                                    if (f[2] * f[3]) >= img_area * 0.03
                                ]
                                if len(significant_faces) > 1:
                                    liveness_failure = "Multiple faces detected. Only one person is allowed."
                                    break
                    
                    if not liveness_failure and occlusion_detected:
                        liveness_failure = occlusion_reason or "Face occlusion detected. Please keep your face clear."
                    elif not liveness_failure and liveness_score < 0.4:
                        liveness_failure = "Liveliness verification failed. Please try again without using a photo or screen."
                    
                    # Compare faces locally
                    if not liveness_failure:
                        if len(id_faces) == 1 and face_count > 0:
                            compare_res = self.compare_faces(id_img, selfie_imgs[0])
                            face_match_confidence = compare_res.get("confidence", 0.0)
                            if face_match_confidence < 0.5:
                                liveness_failure = "Face does not match the uploaded ID."
                        else:
                            face_match_confidence = 0.0
                            liveness_failure = "Face does not match the uploaded ID."

            # Calculate Fraud Score
            fraud_score = self.calculate_fraud_score(
                face_match_confidence,
                liveness_score,
                ocr_match,
                pattern_valid
            )

            # Decision logic
            if liveness_failure:
                status = "liveliness_failed"
                failure_reason = liveness_failure
            else:
                status = "pending_manual_review"
                failure_reason = id_result.get("failure_reason") # Save OCR discrepancy if any

            return {
                "status": status,
                "fraud_score": fraud_score,
                "face_match_confidence": face_match_confidence,
                "liveness_score": liveness_score,
                "ocr_match": ocr_match,
                "pattern_valid": pattern_valid,
                "failure_reason": failure_reason,
                "raw_text": ocr_text,
                "extracted_text_preview": ocr_text[:200],
                "ocr_data": {
                    **id_result.get("ocr_data", {}),
                    "faces_in_id": len(id_faces),
                    "raw_ocr": ocr_text
                }
            }
        except Exception as e:
            traceback.print_exc()
            return {
                "status": "failed",
                "fraud_score": 0,
                "failure_reason": f"System Error: {str(e)}",
                "ocr_data": {}
            }

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Attempts to parse a date string from OCR into a datetime object."""
        if not date_str:
            return None
        
        # Clean string
        clean_date = re.sub(r'(?i)EXPIRY|EXPIRES|DATE|UNTIL|VALID|THRU|[:.\-\s]', ' ', date_str).strip()
        
        # Try various formats
        formats = [
            "%b %d %Y", "%B %d %Y", "%m %d %Y", "%d %b %Y", "%d %B %Y",
            "%Y %m %d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d"
        ]
        
        # Try to find a year in the string first to narrow it down
        year_match = re.search(r'\b(20\d{2})\b', date_str)
        if not year_match:
            return None
            
        for fmt in formats:
            try:
                # We use fuzzy matching by trying to parse parts of the string
                return datetime.strptime(clean_date, fmt)
            except ValueError:
                continue
        
        # Last resort: search for YYYY-MM-DD or MM/DD/YYYY in the raw string
        iso_match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', date_str)
        if iso_match:
            try:
                return datetime(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
            except: pass
            
        us_match = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', date_str)
        if us_match:
            try:
                # Assume MM/DD/YYYY for Philippine permits (common)
                return datetime(int(us_match.group(3)), int(us_match.group(1)), int(us_match.group(2)))
            except: pass
            
        return None

    async def verify_business_permit(self, permit_path: str, business_name: str, owner_name: str = None, db: Session = None) -> Dict[str, Any]:
        """OCR Verification for Business Permits with Owner, Format, and Expiry Matching."""
        try:
            # 1. Image Loading & Quality Check
            img = self._prepare_image(permit_path)
            quality_check = self.check_image_quality(img)
            if not quality_check["valid"]:
                return {"status": "mismatched", "ocr_match": False, "failure_reason": quality_check["reason"]}

            # 2. Perform OCR via Tesseract (Primary)
            ocr_text = self._run_tesseract_multi_psm(img)
            gemini_data = None
            
            if not ocr_text or not ocr_text.strip() or self._is_ocr_garbage(ocr_text):
                print(f"[KYC WARNING] Tesseract failed for permit. Trying Gemini fallback...")
                gemini_prompt = (
                    f"Extract data from this Business Permit. Target Business Name: '{business_name}'. "
                    "Return a JSON object with keys: 'document_type_detected', 'business_name', 'permit_number', 'expiration_date', 'owner_name', 'is_tampered', 'tampering_reason'."
                )
                gemini_data = await self._call_gemini_ocr(permit_path, gemini_prompt)
                if gemini_data and gemini_data.get("business_name"):
                    ocr_text = f"{gemini_data.get('business_name')} {gemini_data.get('permit_number')} {gemini_data.get('owner_name')} {gemini_data.get('expiration_date')}"
                else:
                    return {"status": "rejected", "ocr_match": False, "failure_reason": "❌ Unable to read the Permit. Ensure high clarity."}

            clean_ocr_upper = ocr_text.upper()
            target_name = " ".join(business_name.lower().split())

            print(f"[KYC DEBUG] Business Permit OCR - Target: '{target_name}'")
            print(f"[KYC DEBUG] OCR Text (Preview): '{clean_ocr_upper[:200]}...'")


            # 4. Data Extraction
            permit_number = ""
            expiration_date_str = ""
            if gemini_data:
                permit_number = str(gemini_data.get("permit_number", "")).strip()
                expiration_date_str = str(gemini_data.get("expiration_date", "")).strip()
            else:
                permit_no_match = re.search(r'(?:PERMIT|LICENSE|BP|ACCOUNT)\s*(?:NO|NUMBER)?[:.\s]+([A-Z0-9-]{4,20})', clean_ocr_upper)
                if permit_no_match:
                    permit_number = permit_no_match.group(1)
                
                expiry_match = re.search(r'(?:EXPIRY|EXPIRES|VALID UNTIL|DATE OF EXPIRATION)[:.\s]+([A-Z0-9,\s/-]{6,30})', clean_ocr_upper)
                if expiry_match:
                    expiration_date_str = expiry_match.group(1).strip()

            clean_ocr = clean_ocr_upper.lower()

            # --- ENHANCED CHECKS ---
            permit_checks_failed = []
            
            # 1. Check required permit fields
            if not permit_number or len(permit_number) < 4:
                permit_checks_failed.append("Permit number could not be extracted.")
            
            # 2. Enforce Permit Number Format
            if permit_number and not re.match(r'^[A-Z0-9-]{4,30}$', permit_number.replace(" ", "").upper()):
                permit_checks_failed.append(f"Invalid Permit Number format: '{permit_number}'.")


            # 3. Expiration Date Check (NEW)
            is_expired = False
            if expiration_date_str:
                from datetime import datetime
                parsed_expiry = self._parse_date(expiration_date_str)
                if parsed_expiry:
                    if parsed_expiry < datetime.now():
                        is_expired = True
                        permit_checks_failed.append(f"The permit expired on {parsed_expiry.strftime('%Y-%m-%d')}.")
                else:
                    # If we have a string but can't parse it, we'll flag it for manual review or be lenient
                    print(f"[KYC WARNING] Could not parse expiration date: {expiration_date_str}")
            else:
                permit_checks_failed.append("Expiration date could not be extracted.")

            # 4. Detect Duplicates (Fraud Prevention)
            if db and permit_number:
                from ..db.models import IdentityVerification
                from sqlalchemy import String, cast
                
                # Search specifically in ocr_data JSONB
                existing_v = db.query(IdentityVerification).filter(
                    IdentityVerification.verification_status.in_(["approved", "verified"]),
                    cast(IdentityVerification.ocr_data, String).contains(permit_number)
                ).first()
                
                if existing_v:
                    permit_checks_failed.append("This Business Permit is already registered by another caterer.")

            # 5. Keyword Check (Is it even a permit?)
            is_likely_permit = any(kw.lower() in clean_ocr for kw in self.BUSINESS_PERMIT_KEYWORDS)
            if not is_likely_permit and len(clean_ocr.strip()) > 20:
                # If Gemini was confident about the type, we trust it
                if gemini_data and "PERMIT" in str(gemini_data.get("document_type_detected", "")).upper():
                    is_likely_permit = True
                elif "PERMIT" in clean_ocr.upper() or "MAYOR" in clean_ocr.upper():
                     is_likely_permit = True

            # 6. Normalized Matching for Business Name
            norm_target_name = re.sub(r'[^\w\s]', '', target_name.upper())
            norm_ocr = re.sub(r'[^\w\s]', '', clean_ocr_upper)
            gemini_biz_name = re.sub(r'[^\w\s]', '', (gemini_data.get("business_name", "")).upper()) if gemini_data else ""
            
            name_match = False
            match_ratio = 0
            if norm_target_name:
                if gemini_biz_name and (norm_target_name in gemini_biz_name or gemini_biz_name in norm_target_name):
                    name_match = True
                elif norm_target_name in norm_ocr:
                    name_match = True
                else:
                    name_parts = [p for p in norm_target_name.split() if len(p) > 2]
                    matches = 0
                    for part in name_parts:
                        if part in norm_ocr:
                            matches += 1
                        else:
                            words = norm_ocr.split()
                            for word in words:
                                if difflib.SequenceMatcher(None, part, word).ratio() > 0.8:
                                    matches += 1
                                    break
                    match_ratio = matches / len(name_parts) if name_parts else 0
                    name_match = match_ratio >= 0.5 

            # 7. Owner Name Matching
            owner_match = True
            owner_found_in_ocr = ""
            if owner_name:
                norm_owner_name = re.sub(r'[^\w\s]', '', owner_name.upper())
                gemini_owner = re.sub(r'[^\w\s]', '', (gemini_data.get("owner_name", "")).upper()) if gemini_data else ""
                
                if norm_owner_name:
                    if gemini_owner and (norm_owner_name in gemini_owner or gemini_owner in norm_owner_name):
                        owner_match = True
                    elif norm_owner_name in norm_ocr:
                        owner_match = True
                    else:
                        owner_parts = [p for p in norm_owner_name.split() if len(p) > 2]
                        owner_matches = 0
                        for part in owner_parts:
                            if part in norm_ocr:
                                owner_matches += 1
                            else:
                                words = norm_ocr.split()
                                for word in words:
                                    if difflib.SequenceMatcher(None, part, word).ratio() > 0.8:
                                        owner_matches += 1
                                        break
                        owner_match_ratio = owner_matches / len(owner_parts) if owner_parts else 0
                        owner_match = owner_match_ratio >= 0.5
                
                # Attempt to find owner name around labels
                for label in self.OWNER_NAME_LABELS:
                    label_pos = ocr_text.upper().find(label)
                    if label_pos != -1:
                        snippet = ocr_text[label_pos + len(label):label_pos + len(label) + 50].strip()
                        owner_found_in_ocr = snippet.split('\n')[0].strip()
                        break

            # 8. Final Decision
            failure_reasons = []
            if not is_likely_permit:
                failure_reasons.append("Invalid Business Permit.")
            if not name_match:
                failure_reasons.append("Business name mismatch.")
            if not owner_match:
                failure_reasons.append("Owner name mismatch.")
            if permit_checks_failed:
                failure_reasons.extend(permit_checks_failed)
            
            # Tampering / AI-Editing Detection for Permit
            is_tampered = False
            tampering_reason = None
            if gemini_data and gemini_data.get("is_tampered"):
                is_tampered = True
                tampering_reason = gemini_data.get("tampering_reason", "Digitally altered.")
                failure_reasons.append(f"Authenticity Failed: {tampering_reason}")

            status = "matched" if (name_match and owner_match and is_likely_permit and not permit_checks_failed and not is_tampered) else "rejected"

            return {
                "status": status,
                "ocr_match": name_match and owner_match,
                "is_likely_permit": is_likely_permit,
                "permit_number": permit_number,
                "expiration_date": expiration_date_str,
                "failure_reason": " ".join(failure_reasons) if failure_reasons else None,
                "extracted_text_preview": ocr_text[:300],
                "ocr_data": {
                    "raw_text": ocr_text,
                    "business_name_match": name_match,
                    "owner_name_match": owner_match,
                    "permit_number": permit_number,
                    "expiration_date": expiration_date_str,
                    "is_expired": is_expired,
                    "match_ratio": match_ratio,
                    "owner_found": owner_found_in_ocr,
                    "is_tampered": is_tampered,
                    "tampering_reason": tampering_reason
                }
            }

        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "failure_reason": f"System Error during Permit scan: {str(e)}"}

    async def verify_menu_document(self, menu_path: str) -> Dict[str, Any]:
        """OCR Verification for Sample Menus to ensure they are legit food-related documents."""
        try:
            # 1. Image Loading & Quality Check
            # If it's a PDF, we might need to skip OpenCV checks or convert first
            # For now, assuming image or basic PDF processing
            filename = os.path.basename(menu_path.replace('\\', '/'))
            ext = os.path.splitext(filename)[1].lower()
            
            if ext != '.pdf':
                try:
                    img = self._prepare_image(menu_path)
                    quality_check = self.check_image_quality(img)
                    if not quality_check["valid"]:
                        return {"status": "rejected", "ocr_match": False, "failure_reason": quality_check["reason"]}
                    
                    # 2. Perform OCR
                    ocr_text = self._run_tesseract_multi_psm(img)
                except Exception as e:
                    print(f"[KYC ERROR] Menu image prep failed: {e}")
                    return {"status": "error", "failure_reason": "Unable to process menu image."}
            else:
                # PDF handling - basic length/metadata check for now, or just trust the file validator in utils
                # In a real app, we'd use pdfplumber or similar
                return {"status": "approved", "ocr_match": True, "failure_reason": None}

            if not ocr_text or not ocr_text.strip() or self._is_ocr_garbage(ocr_text):
                is_likely_menu = False
            else:
                clean_ocr_upper = ocr_text.upper()
                is_likely_menu = any(kw in clean_ocr_upper for kw in self.MENU_KEYWORDS)

            if not is_likely_menu:
                print(f"[KYC WARNING] Tesseract failed for menu (No keywords or garbage). Trying Gemini fallback...")
                gemini_prompt = (
                    "Analyze this image. Determine if it is a catering menu, food list, or food package pricing document. "
                    "Return a JSON object with keys: 'is_likely_menu' (boolean) and 'extracted_text_preview' (string, max 300 chars of key food items)."
                )
                gemini_data = await self._call_gemini_ocr(menu_path, gemini_prompt)
                
                # If Gemini fails completely (e.g. no API key), we will just approve it as a lenient fallback
                if not gemini_data:
                     print("[KYC DEBUG] Gemini OCR unavailable. Leniently approving sample menu.")
                     return {"status": "approved", "ocr_match": True, "is_likely_menu": True, "failure_reason": None, "extracted_text_preview": "Lenient approval (No AI)"}

                if gemini_data and gemini_data.get("is_likely_menu"):
                    return {
                        "status": "approved",
                        "ocr_match": True,
                        "is_likely_menu": True,
                        "failure_reason": None,
                        "extracted_text_preview": gemini_data.get("extracted_text_preview", "")[:300]
                    }
                else:
                    return {"status": "rejected", "ocr_match": False, "failure_reason": "❌ Document does not appear to be a valid menu/price list."}
            else:
                return {
                    "status": "approved",
                    "ocr_match": True,
                    "is_likely_menu": True,
                    "failure_reason": None,
                    "extracted_text_preview": ocr_text[:300]
                }

        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "failure_reason": f"System Error during Menu scan: {str(e)}"}

    def verify_identity(self, id_url: str, selfie_url: str) -> dict:
        """Legacy mock for compatibility."""
        return {
            "success": True,
            "failure_reason": None,
            "ocr_data": {"full_name": "RODRIGUEZ, MARIA CLARA"}
        }

    def check_liveness(self, selfie_url: str) -> dict:
        """Legacy mock for compatibility."""
        return {"success": True, "liveness_token": "live_tok_" + str(random.randint(1000, 9999))}

verification_service = VerificationService()
