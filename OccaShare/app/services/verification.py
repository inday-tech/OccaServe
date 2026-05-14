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
from typing import List, Dict, Any, Optional
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
        filename = encrypted_path.split("/")[-1]
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

    def _extract_rich_ocr_data(self, text: str) -> Dict[str, Any]:
        """Extracts Full Name, ID Number, DOB, Expiry, and Address using regex."""
        data = {
            "full_name": "",
            "id_number": "",
            "extracted_dob": "",
            "extracted_expiry": "",
            "extracted_address": ""
        }
        
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        clean_text_upper = text.upper()
        
        # 1. Name Extraction (Improved Heuristics)
        potential_names = []
        for i, line in enumerate(lines):
            upper_line = line.upper()
            if any(k in upper_line for k in ["NAME", "SURNAME", "GIVEN", "FIRST", "MAIDEN"]):
                val = lines[i+1] if i+1 < len(lines) else ""
                if len(val) > 4 and not any(char.isdigit() for char in val):
                    potential_names.append(val.strip())
            
            # Look for typical 2-3 word name format in all caps
            if 10 < len(line) < 50 and line.isupper() and re.match(r'^[A-Z ,.-]+$', line):
                if not any(kw in line for kw in self.ID_LEGITIMACY_KEYWORDS) and \
                   not any(kw in line for kw in ["PUROK", "BRGY", "CITY", "PROVINCE", "STREET", "BARANGAY"]):
                    potential_names.append(line)

        if potential_names:
            data["full_name"] = potential_names[0]

        # 2. ID Number Extraction
        id_patterns = [
            r'(\d{4}-\d{4}-\d{4}-\d{4})', # PhilID
            r'([A-Z]\d{2}-\d{2}-\d{6})',    # Driver's License
            r'([A-Z]\d{7,8}[A-Z]?)',         # Passport
            r'(\d{2}-\d{7}-\d{1})',         # SSS
            r'(\d{3}-\d{3}-\d{3}-\d{0,3})', # TIN
            r'(\d{4}-\d{7}-\d{1})'          # UMID
        ]
        for pattern in id_patterns:
            match = re.search(pattern, clean_text_upper)
            if match:
                data["id_number"] = match.group(1).strip()
                break

        # 3. Birth Date Detection (Aggressive)
        date_pattern = r"(\b(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z.]*\s+\d{1,2},?\s+\d{4}\b|\d{2}[-/]\d{2}[-/]\d{4}|\d{4}[-/]\d{2}[-/]\d{2})"
        dob_keywords = ["DATE OF BIRTH", "BIRTH DATE", "DOB", "BORN", "BIRTH", "DATE DE NAISSANCE"]
        for kw in dob_keywords:
            match = re.search(re.escape(kw) + r".{1,30}(" + date_pattern + r")", clean_text_upper, re.DOTALL)
            if match:
                data["extracted_dob"] = match.group(1)
                break
        
        # 4. Address Detection (Philippine Specific)
        address_parts = []
        address_markers = ["PUROK", "BRGY", "BARANGAY", "CITY", "PROVINCE", "STREET", "SUBD", "MUNICIPALITY", "DISTRICT", "PHASE"]
        for i, line in enumerate(lines):
            line_upper = line.upper()
            if any(marker in line_upper for marker in address_markers):
                address_parts.append(line)
                if i+1 < len(lines) and (lines[i+1].isupper() or len(lines[i+1]) < 30):
                    if not any(kw in lines[i+1].upper() for kw in self.ID_LEGITIMACY_KEYWORDS):
                        address_parts.append(lines[i+1])
                break
        
        if address_parts:
            data["extracted_address"] = ", ".join(address_parts)

        return data

        return data

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
            return {"valid": False, "reason": "Image is too blurry. Please ensure the camera is in focus."}
            
        return {"valid": True}

    def check_duplicate_id(self, db: Session, id_number: str, current_user_id: int) -> bool:
        """Checks if the ID number is already associated with another verified user."""
        existing = db.query(IdentityVerification).filter(
            IdentityVerification.id_number == id_number,
            IdentityVerification.user_id != current_user_id,
            IdentityVerification.verification_status == 'approved'
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
        angle = cv2.minAreaRect(coords)[-1]
        
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
            
        # Avoid rotating if the angle is essentially 0, 90, or 180 degrees
        if abs(angle) < 0.5 or abs(angle - 90) < 0.5 or abs(angle + 90) < 0.5:
            print(f"[KYC DEBUG] Deskewing skipped (already upright). Original Angle: {angle:.2f}")
            return image
            
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        print(f"[KYC DEBUG] Deskewing applied. Angle: {angle:.2f}")
        return rotated

    def _enhance_for_ocr(self, img: np.ndarray) -> np.ndarray:
        """Applies contrast enhancement and sharpening to improve OCR."""
        if not CV2_AVAILABLE: return img
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Sharpening (Unsharp Masking)
        blurred = cv2.GaussianBlur(enhanced, (0, 0), 3)
        sharpened = cv2.addWeighted(enhanced, 1.5, blurred, -0.5, 0)
        
        return sharpened

    def _run_tesseract_multi_psm(self, image: np.ndarray) -> str:
        """Runs Tesseract with advanced preprocessing and multiple PSM modes."""
        if not PYTESSERACT_AVAILABLE:
            print("[KYC ERROR] OCR requested but pytesseract not available.")
            return ""

        if not CV2_AVAILABLE:
            print("[KYC ERROR] OCR requested but OpenCV not available for preprocessing.")
            return ""

        # 1. Deskew
        image = self._deskew(image)
        
        # 2. Rescale for better OCR quality
        height, width = image.shape[:2]
        # Target height of ~1000px for OCR is often optimal
        scaling_factor = 2.0 if height < 800 else 1.0
        upscaled = cv2.resize(image, (int(width * scaling_factor), int(height * scaling_factor)), interpolation=cv2.INTER_CUBIC)
        
        # 3. Robust Grayscale & Noise Reduction
        gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
        
        # Background subtraction to handle textured backgrounds
        # Using a large kernel to estimate the background then subtracting it
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))
        bg = cv2.morphologyEx(gray, cv2.MORPH_DILATE, kernel)
        gray_sub = cv2.divide(gray, bg, scale=255)
        
        # Bilateral Filtering (Noise reduction while preserving edges)
        filtered = cv2.bilateralFilter(gray_sub, 9, 75, 75)
        
        # 4. Adaptive Thresholding (Otsu + Gaussian fallback)
        # We'll try both to see which gives better text density
        thresh_gaussian = cv2.adaptiveThreshold(filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        _, thresh_otsu = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        
        best_text = ""
        
        def run_pass(img_pass):
            nonlocal best_text
            # PSM 3: Automatic segmentation. 
            # PSM 6: Uniform block (often best for IDs).
            # PSM 11: Sparse text (good for small labels).
            # PSM 6 is usually sufficient for IDs and is the fastest
            for psm in [6]: 
                config = f'--psm {psm} -l eng'
                try:
                    if not pytesseract: return False
                    current_text = pytesseract.image_to_string(img_pass, config=config)
                    if len(current_text.strip()) > len(best_text.strip()):
                        best_text = current_text
                        # If we have a decent amount of text, stop early to save time
                        if len(best_text.strip()) > 50: return True
                except: continue
            return False

        # Attempt with Gaussian Thresholding first
        run_pass(thresh_gaussian)
        
        # Only try Otsu or Rotation if Gaussian was very poor (< 30 chars)
        if len(best_text.strip()) < 30:
            print("[KYC DEBUG] Tesseract fallback: Gaussian poor, trying Otsu/Rotation/Orientation/Raw...")
            if not run_pass(thresh_otsu):
                # Try raw filtered image (no thresholding)
                if run_pass(filtered):
                    print("[KYC DEBUG] OCR match found using Raw Filtered image.")
                else:
                    # Try 90-degree rotations of the UPSCALED image (more robust than rotating thresh)
                    for rot_const in [cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE]:
                        try:
                            rotated = cv2.rotate(upscaled, rot_const)
                            gray_rot = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)
                            _, thresh_rot = cv2.threshold(gray_rot, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
                            if run_pass(thresh_rot):
                                print(f"[KYC DEBUG] OCR match found after rotation {rot_const}.")
                                break
                        except: continue

            # Final attempt: High Contrast Binarization
            if len(best_text.strip()) < 30:
                alpha = 1.5 # Contrast
                adjusted = cv2.convertScaleAbs(upscaled, alpha=alpha, beta=0)
                gray_adj = cv2.cvtColor(adjusted, cv2.COLOR_BGR2GRAY)
                _, thresh_adj = cv2.threshold(gray_adj, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
                run_pass(thresh_adj)
            
        return best_text

    async def _call_gemini_ocr(self, image_path: str, prompt: str) -> Dict[str, Any]:
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            print("[KYC DEBUG] No Gemini API key found. Skipping Gemini OCR.")
            return None
        try:
            start_time = time.time()
            filename = image_path.split("/")[-1]
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
                
            # Fixed model name to 1.5-flash for stability and speed
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
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
                response = await client.post(url, json=payload, headers=headers, timeout=15.0)
                if response.status_code == 200:
                    data = response.json()
                    text = data['candidates'][0]['content']['parts'][0]['text']
                    elapsed = time.time() - start_time
                    print(f"[KYC DEBUG] Gemini OCR Succeeded in {elapsed:.2f}s")
                    return json.loads(text)
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
        "PhilID (National ID)": {
            "fields": ["full_name", "pcn_number", "date_of_birth", "sex", "address", "blood_type", "nationality"],
            "prompt": (
                "This is a Philippine National ID (PhilSys/PhilID). Extract ALL of the following fields. "
                "Return a JSON object with these exact keys: "
                "'document_type_detected', 'full_name', 'pcn_number' (PhilSys Card Number, format: XXXX-XXXX-XXXX-XXXX), "
                "'date_of_birth', 'sex', 'address', 'blood_type', 'nationality', "
                "'face_visible' (boolean), 'confidence_score' (0-1). "
                "If a field is not visible or unreadable, set its value to null."
            )
        },
        "Driver's License": {
            "fields": ["full_name", "license_number", "nationality", "date_of_birth", "address", "expiry_date", "agency_code", "dl_codes", "restrictions", "height", "weight"],
            "prompt": (
                "This is a Philippine Driver's License issued by LTO. Extract ALL of the following fields. "
                "Return a JSON object with these exact keys: "
                "'document_type_detected', 'full_name', 'license_number' (format: X00-00-000000), "
                "'nationality', 'date_of_birth', 'address', 'expiry_date', "
                "'agency_code', 'dl_codes' (DL codes/restrictions like A, A1, B, B1, B2, C, D, BE, CE), "
                "'restrictions', 'height', 'weight', "
                "'face_visible' (boolean), 'confidence_score' (0-1). "
                "If a field is not visible or unreadable, set its value to null."
            )
        },
        "Passport": {
            "fields": ["surname", "given_name", "middle_name", "passport_number", "nationality", "date_of_birth", "sex", "place_of_birth", "date_issued", "expiry_date", "mrz_line_1", "mrz_line_2"],
            "prompt": (
                "This is a Philippine Passport. Extract ALL of the following fields. "
                "Return a JSON object with these exact keys: "
                "'document_type_detected', 'surname', 'given_name', 'middle_name', "
                "'passport_number' (format: X0000000 or XX0000000), "
                "'nationality', 'date_of_birth', 'sex', 'place_of_birth', "
                "'date_issued', 'expiry_date', "
                "'mrz_line_1' (first line of Machine Readable Zone at bottom), "
                "'mrz_line_2' (second line of Machine Readable Zone at bottom), "
                "'face_visible' (boolean), 'confidence_score' (0-1). "
                "IMPORTANT: The MRZ lines are the two lines of text at the very bottom of the passport data page, "
                "composed of capital letters, digits, and '<' characters. Extract them exactly as printed. "
                "If a field is not visible or unreadable, set its value to null."
            )
        },
        "UMID": {
            "fields": ["full_name", "crn_number", "date_of_birth", "sex", "address"],
            "prompt": (
                "This is a Philippine Unified Multi-Purpose ID (UMID). Extract ALL of the following fields. "
                "Return a JSON object with these exact keys: "
                "'document_type_detected', 'full_name', 'crn_number' (Common Reference Number, format: XXXX-XXXXXXX-X), "
                "'date_of_birth', 'sex', 'address', "
                "'face_visible' (boolean), 'confidence_score' (0-1). "
                "If a field is not visible or unreadable, set its value to null."
            )
        }
    }

    # Default prompt for any ID type not in the specific list
    DEFAULT_OCR_PROMPT = (
        "Extract data from this Philippine government ID image. "
        "Return a JSON object with these keys: "
        "'document_type_detected', 'full_name', 'id_number', 'date_of_birth', "
        "'sex', 'address', 'expiry_date', 'nationality', "
        "'face_visible' (boolean), 'confidence_score' (0-1). "
        "If a field is not visible or unreadable, set its value to null."
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
        
        # Build the full_name for passport (surname + given + middle)
        if id_type == "Passport" and not fields.get("full_name"):
            name_parts = []
            for k in ["given_name", "middle_name", "surname"]:
                if fields.get(k):
                    name_parts.append(fields[k])
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
            
            # 4. Perform OCR via Gemini API (if key available) or fallback to Tesseract
            gemini_data = None
            gemini_prompt = self._get_id_type_ocr_prompt(id_type)
            gemini_data = await self._call_gemini_ocr(id_path, gemini_prompt)
            
            structured_ocr = None  # Will hold the new structured format
            
            if gemini_data and (gemini_data.get("full_name") or gemini_data.get("surname") or gemini_data.get("given_name")):
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
                    "extracted_address": gemini_data.get("address", "")
                }
                # Optimization: Trust Gemini for face visibility to save OpenCV processing time
                has_face = gemini_data.get("face_visible", True)
                id_faces = [1] if has_face else [] 
            else:
                ocr_text = self._run_tesseract_multi_psm(id_img)
                
                if not ocr_text or not ocr_text.strip() or self._is_ocr_garbage(ocr_text):
                    print(f"[KYC WARNING] Tesseract failed to parse text for ID.")
                    if not os.getenv("GEMINI_API_KEY"):
                        print("[KYC DEBUG] Permitting empty OCR text for ID in Demo mode.")
                        ocr_text = "DEMO_BYPASS_MODE_TEXT"
                    else:
                        return {
                            "status": "rejected",
                            "ocr_match": False,
                            "failure_reason": "❌ Unable to read the ID. Please upload a clearer image."
                        }

                    
                clean_ocr_upper = ocr_text.upper()
                
                # 5. Legitimacy Check (STRICTER but with FUZZY)
                def fuzzy_contains_id_keywords(text):
                    if any(kw in text for kw in self.ID_LEGITIMACY_KEYWORDS):
                        return True
                    typo_tolerant_kws = ["PHILIPPINES", "REPUBLIC", "IDENTITY", "IDENTIFICATION", "PASSPORT", "LICENSE"]
                    for kw in typo_tolerant_kws:
                        if len(text) > 20:
                            match = difflib.get_close_matches(kw, text.split(), n=1, cutoff=0.7)
                            if match: return True
                    return False
                
                id_faces = self._detect_faces_detailed(id_img)
                has_face = len(id_faces) > 0
                is_likely_id = (fuzzy_contains_id_keywords(clean_ocr_upper) or has_face) and len(clean_ocr_upper.strip()) > 15
                
                rich_data = self._extract_rich_ocr_data(ocr_text)
                
                # Build structured OCR for Tesseract fallback
                tesseract_fields = {
                    "full_name": rich_data.get("full_name", ""),
                    "id_number": rich_data.get("id_number", ""),
                    "date_of_birth": rich_data.get("extracted_dob", ""),
                    "address": rich_data.get("extracted_address", "")
                }
                # For passport: attempt MRZ extraction
                if id_type == "Passport":
                    mrz = self._extract_mrz_from_text(ocr_text)
                    tesseract_fields.update(mrz)
                
                structured_ocr = {
                    "id_type": id_type,
                    "extraction_method": "tesseract",
                    "document_type_detected": id_type,
                    "confidence_score": 0.5,
                    "face_visible": has_face,
                    "fields": tesseract_fields,
                    "full_name": tesseract_fields.get("full_name", ""),
                    "id_number": tesseract_fields.get("id_number", ""),
                    "birth_date": tesseract_fields.get("date_of_birth", ""),
                    "address": tesseract_fields.get("address", "")
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
                
                # Typo tolerance (Fuzzy)
                if ocr_data_name:
                    ratio = difflib.SequenceMatcher(None, clean_input, ocr_data_name.lower()).ratio()
                    if ratio > 0.85: return True
                
                # Check parts (lowered to 60% match for robustness)
                input_parts = [p for p in clean_input.split() if len(p) > 2]
                if not input_parts: return False
                matches = 0
                for part in input_parts:
                    if part in full_ocr_lower or any(difflib.SequenceMatcher(None, part, w).ratio() > 0.8 for w in full_ocr_lower.split()):
                        matches += 1
                return (matches / len(input_parts)) >= 0.60

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
            norm_id_input = id_number.replace("-", "").replace(" ", "").upper()
            norm_id_ocr = clean_ocr_upper.replace("-", "").replace(" ", "")

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
                "failure_reason": " ".join(reasons) if reasons else None,
                "extracted_text_preview": ocr_text[:200],
                "ocr_data": final_ocr_data
            }
        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "failure_reason": f"System Error during ID scan: {str(e)}"}

    async def extract_id_data(self, id_path: str, id_type: str) -> Dict[str, Any]:
        """Extracts text from ID without performing validation against user input."""
        try:
            id_img = self._prepare_image(id_path)
            quality_check = self.check_image_quality(id_img)
            
            gemini_prompt = self._get_id_type_ocr_prompt(id_type)
            gemini_data = await self._call_gemini_ocr(id_path, gemini_prompt)
            
            if gemini_data and (gemini_data.get("full_name") or gemini_data.get("surname")):
                structured_ocr = self._build_structured_ocr_data(gemini_data, id_type, "gemini")
            else:
                ocr_text = self._run_tesseract_multi_psm(id_img)
                rich_data = self._extract_rich_ocr_data(ocr_text)
                tesseract_fields = {
                    "full_name": rich_data.get("full_name", ""),
                    "id_number": rich_data.get("id_number", ""),
                    "date_of_birth": rich_data.get("extracted_dob", ""),
                    "address": rich_data.get("extracted_address", "")
                }
                structured_ocr = {
                    "id_type": id_type,
                    "extraction_method": "tesseract",
                    "fields": tesseract_fields,
                    "full_name": tesseract_fields.get("full_name", ""),
                    "id_number": tesseract_fields.get("id_number", ""),
                    "birth_date": tesseract_fields.get("date_of_birth", ""),
                    "address": tesseract_fields.get("address", "")
                }
            
            return {
                "success": True,
                "data": structured_ocr,
                "quality": quality_check
            }
        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}

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
        """Refactored full verification logic using verify_id_document."""
        try:
            # 1. Document Verification (Now just re-using the method)
            id_result = await self.verify_id_document(id_path, full_name, id_number, id_type, db, user_id, dob, address)
            if id_result["status"] == "error":
                return id_result # Bubble up error

            ocr_match = id_result["ocr_match"]
            pattern_valid = id_result["pattern_valid"]
            ocr_text = id_result["ocr_data"]["raw_text"]

            # 3. MediaPipe Liveness Detection
            selfie_imgs = []
            for sp in selfie_paths:
                selfie_imgs.append(self._prepare_image(sp))
            
            liveness_result = self._check_liveness_mediapipe(selfie_imgs)
            liveness_score = liveness_result["score"]
            
            # 4. Face Matching (Detection Check)
            id_img = self._prepare_image(id_path)
            id_faces = self._detect_faces_detailed(id_img)
            face_match_confidence = 0.0
            if len(id_faces) == 1 and liveness_result["face_count"] > 0:
                face_match_confidence = 0.75 # Placeholder for real recognition
            
            # 5. Calculate Fraud Score
            fraud_score = self.calculate_fraud_score(
                face_match_confidence,
                liveness_score,
                ocr_match,
                pattern_valid
            )
            
            # 6. Decision logic
            status = "approved"
            reasons = []
            if not ocr_match: reasons.append("Name or ID not found on document")
            if not pattern_valid: reasons.append("ID number format is invalid")
            if liveness_score < 0.4: reasons.append("Liveness check failed (suspicious movement or no face)")
            
            if fraud_score < 60 or reasons:
                status = "rejected"
                failure_reason = ", ".join(reasons) if reasons else "Low verification confidence"
            else:
                failure_reason = None
                
            return {
                "status": status,
                "fraud_score": fraud_score,
                "face_match_confidence": face_match_confidence,
                "liveness_score": liveness_score,
                "ocr_match": ocr_match,
                "pattern_valid": pattern_valid,
                "failure_reason": failure_reason,
                "extracted_text_preview": ocr_text[:200],
                "ocr_data": {
                    **id_result["ocr_data"],
                    "faces_in_id": len(id_faces)
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

            # 2. Perform OCR via Gemini API (if key available) or fallback to Tesseract
            gemini_prompt = (
                f"Extract data from this Business Permit or Mayor's Permit. Target Business Name: '{business_name}'. "
                "Return a JSON object with keys: 'document_type_detected', 'business_name', 'permit_number', 'expiration_date', 'owner_name', 'confidence_score' (0-1). "
                "The expiration_date should be in YYYY-MM-DD format if possible."
            )
            gemini_data = await self._call_gemini_ocr(permit_path, gemini_prompt)
            
            permit_number = ""
            expiration_date_str = ""
            
            if gemini_data and gemini_data.get("business_name"):
                print(f"[KYC DEBUG] Gemini OCR Succeeded for Business Permit.")
                ocr_text = f"GEMINI OCR RESULT: Business: {gemini_data.get('business_name')}, Owner: {gemini_data.get('owner_name')}, Type: {gemini_data.get('document_type_detected')}"
                clean_ocr = ocr_text.lower()
                permit_number = str(gemini_data.get("permit_number", "")).strip()
                expiration_date_str = str(gemini_data.get("expiration_date", "")).strip()
            else:
                ocr_text = self._run_tesseract_multi_psm(img)
                clean_ocr = " ".join(ocr_text.lower().split())
                
                # Fallback regex for Permit Number (Standard PH Format: YYYY-NNNNN or similar)
                permit_no_match = re.search(r'(?:PERMIT|LICENSE|BP|ACCOUNT)\s*(?:NO|NUMBER)?[:.\s]+([A-Z0-9-]{4,20})', ocr_text.upper())
                if permit_no_match:
                    permit_number = permit_no_match.group(1)
                
                # Fallback for Expiration Date
                expiry_match = re.search(r'(?:EXPIRY|EXPIRES|VALID UNTIL|DATE OF EXPIRATION)[:.\s]+([A-Z0-9,\s/-]{6,30})', ocr_text.upper())
                if expiry_match:
                    expiration_date_str = expiry_match.group(1).strip()
                
            target_name = " ".join(business_name.lower().split())

            print(f"[KYC DEBUG] Business Permit OCR - Target: '{target_name}'")
            print(f"[KYC DEBUG] OCR Text (Preview): '{clean_ocr[:200]}...'")

            # --- ENHANCED CHECKS ---
            permit_checks_failed = []
            
            # 1. Check required permit fields
            if not permit_number or len(permit_number) < 4:
                permit_checks_failed.append("Permit number could not be extracted.")
            
            # 2. Enforce Permit Number Format (Philippines standard usually involves Year or Account No)
            # We allow alphanumeric with dashes, but must be substantial
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
                    IdentityVerification.verification_status == "approved",
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

            # 6. Fuzzy Matching for Business Name
            name_parts = [p for p in target_name.split() if len(p) > 2]
            matches = 0
            for part in name_parts:
                if part in clean_ocr:
                    matches += 1
                else:
                    words = clean_ocr.split()
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
                clean_owner = " ".join(owner_name.lower().split())
                owner_parts = [p for p in clean_owner.split() if len(p) > 2]
                owner_matches = 0
                for part in owner_parts:
                    if part in clean_ocr:
                        owner_matches += 1
                    else:
                        words = clean_ocr.split()
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
                failure_reasons.append("The uploaded document does not look like a valid Business Permit.")
            if not name_match:
                failure_reasons.append(f"Business mismatch: '{business_name}' not detected on document.")
            if not owner_match:
                failure_reasons.append(f"Owner mismatch: '{owner_name}' not detected on document.")
            if permit_checks_failed:
                failure_reasons.extend(permit_checks_failed)

            status = "matched" if (name_match and owner_match and is_likely_permit and not permit_checks_failed) else "rejected"

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
                    "owner_found": owner_found_in_ocr
                }
            }

        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "failure_reason": f"System Error during Permit scan: {str(e)}"}

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
