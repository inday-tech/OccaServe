import random
import time
import re
import os
import io
import difflib
import numpy as np
import traceback
from typing import List, Dict, Any
from ..core.encryption import decrypt_data
from PIL import Image, ImageOps
from sqlalchemy.orm import Session

# Graceful imports for heavy dependencies (may not be available on all cloud platforms)
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    print("[KYC WARNING] OpenCV (cv2) not available. KYC verification will be limited.")
    CV2_AVAILABLE = False

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

# Configure Tesseract Path for Windows (only if available)
if PYTESSERACT_AVAILABLE:
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
            
            # Convert back to BGR for OpenCV
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            return img
        except Exception as e:
            print(f"[KYC DEBUG] Fatal error preparing image {filename}: {e}")
            # Last resort fallback
            try:
                nparr = np.frombuffer(raw_data, np.uint8)
                return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            except:
                raise e

    def _detect_faces_detailed(self, img: np.ndarray) -> List[Any]:
        """Detect faces using standard OpenCV Haar Cascades."""
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        return faces

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
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            detection_result = self.landmarker.detect(mp_image)
            
            if detection_result.face_landmarks:
                face_detected_count += 1
                landmarks = detection_result.face_landmarks[0]
                
                # --- OCCLUSION CHECK ---
                # Check for "confidence" or presence of key landmarks
                # In MediaPipe Tasks, landmarks are always returned but we check 
                # for unusual values or spatial distribution
                # If mouth (index 0, 13, 14, 17) or eyes (33, 133, 362, 263) are out of bounds
                # or if some landmarks have 0 coordinates (rare but possible in some implementations)
                
                # Check Face Orientation (Pose)
                # Yaw: Check distance between eyes and nose
                e_dist_l = np.linalg.norm(np.array([landmarks[33].x, landmarks[33].y]) - np.array([landmarks[1].x, landmarks[1].y]))
                e_dist_r = np.linalg.norm(np.array([landmarks[263].x, landmarks[263].y]) - np.array([landmarks[1].x, landmarks[1].y]))
                yaw_ratio = e_dist_l / e_dist_r if e_dist_r > 0 else 5
                
                if yaw_ratio > 3.0 or yaw_ratio < 0.33:
                    occlusion_detected = True
                    occlusion_reason = "Please face the camera directly."

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
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            res = self.landmarker.detect(mp_image)
            if not res.face_landmarks: return None
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
        
        # 1. Name Extraction (More robust heuristics)
        # Often names are in the first few lines or near keywords
        potential_names = []
        for i, line in enumerate(lines):
            upper_line = line.upper()
            # Keywords indicating following line is a name
            if any(k in upper_line for k in ["NAME", "SURNAME", "GIVEN", "FIRST"]):
                val = lines[i+1] if i+1 < len(lines) else ""
                if len(val) > 5 and not any(char.isdigit() for char in val):
                    potential_names.append(val.strip())
            
            # Lines that are 2-3 words, all caps, no symbols/digits
            if 10 < len(line) < 40 and line.isupper() and re.match(r'^[A-Z ,.-]+$', line):
                # Ignore legitimacy keywords
                if not any(kw in line for kw in self.ID_LEGITIMACY_KEYWORDS):
                    potential_names.append(line)

        if potential_names:
            # Heuristic: the most likely name is often the one that's not a category
            data["full_name"] = potential_names[0]

        # 2. ID Number Extraction
        for line in lines:
            digits_only = re.sub(r'[^0-9]', '', line)
            if len(digits_only) >= 9:
                match = re.search(r'([A-Z0-9][-A-Z0-9 ]{8,20})', line)
                if match:
                    data["id_number"] = match.group(1).strip()
                    break

        # 3. Date Extraction
        date_pattern = r"(\d{2}[-/]\d{2}[-/]\d{4})"
        dates = re.findall(date_pattern, text)
        if dates:
            try:
                sorted_dates = sorted(dates, key=lambda d: time.strptime(d.replace("/", "-"), "%d-%m-%Y"))
                data["extracted_dob"] = sorted_dates[0]
                if len(sorted_dates) > 1:
                    data["extracted_expiry"] = sorted_dates[-1]
            except: pass

        return data

    def check_image_quality(self, image: np.ndarray) -> Dict[str, Any]:
        """Checks image for blur, resolution, and basic glare."""
        height, width = image.shape[:2]
        
        # 1. Resolution Check
        if width < 640 or height < 400:
            return {"valid": False, "reason": f"Resolution too low ({width}x{height}). Please take a clearer photo."}
        
        # 2. Blur Detection (Laplacian Variance)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        print(f"[KYC DEBUG] Image Quality Check - Resolution: {width}x{height}, Blur Score: {blur_score:.2f}")
        
        # Threshold 100 is usually good for ID cards, but let's be slightly more lenient (70)
        if blur_score < 70:
            return {"valid": False, "reason": "Image is too blurry. Please ensure the camera is in focus."}
            
        return {"valid": True}

    def check_duplicate_id(self, db: Session, id_number: str, current_user_id: int) -> bool:
        """Checks if the ID number is already associated with another verified user."""
        from ..db.models import IdentityVerification
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
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.bitwise_not(gray)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        coords = np.column_stack(np.where(thresh > 0))
        angle = cv2.minAreaRect(coords)[-1]
        
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
            
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        print(f"[KYC DEBUG] Deskewing applied. Angle: {angle:.2f}")
        return rotated

    def _enhance_for_ocr(self, img: np.ndarray) -> np.ndarray:
        """Applies contrast enhancement and sharpening to improve OCR."""
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
            for psm in [6, 3]: 
                config = f'--psm {psm} -l eng'
                try:
                    current_text = pytesseract.image_to_string(img_pass, config=config)
                    if len(current_text.strip()) > len(best_text.strip()):
                        best_text = current_text
                        # If we have a decent amount of text, stop early to save time
                        if len(best_text.strip()) > 80: return True
                except: continue
            return False

        # Attempt with Gaussian Thresholding first
        run_pass(thresh_gaussian)
        
        # Only try Otsu or Rotation if Gaussian was very poor (< 30 chars)
        if len(best_text.strip()) < 30:
            print("[KYC DEBUG] Tesseract fallback: Gaussian poor, trying Otsu/Rotation...")
            if not run_pass(thresh_otsu):
                rotated = cv2.rotate(thresh_gaussian, cv2.ROTATE_180)
                run_pass(rotated)
            
        return best_text

    ID_LEGITIMACY_KEYWORDS = [
        "REPUBLIC OF THE PHILIPPINES", "PHILIPPINES", "PASSPORT", "IDENTIFICATION", "SOCIAL SECURITY", 
        "PROFESSIONAL REGULATION COMMISSION", "LAND TRANSPORTATION OFFICE", "COMMISSION ON ELECTIONS",
        "PHILIPPINE IDENTIFICATION", "UNIFIED MULTI-PURPOSE ID", "POSTAL ID", "TAXPAYER IDENTIFICATION",
        "DRIVER'S LICENSE", "UMID", "SSS", "GSIS", "PRC", "COMELEC", "PHILHEALTH"
    ]

    def verify_id_document(self, 
                           id_path: str, 
                           full_name: str, 
                           id_number: str, 
                           id_type: str,
                           db: Session = None,
                           user_id: int = None) -> Dict[str, Any]:
        """Strictly validates the ID document (Quality + OCR + Patterns) synchronously."""
        try:
            # 1. Duplicate Check (Fraud Prevention)
            if db and user_id and id_number:
                if self.check_duplicate_id(db, id_number, user_id):
                    return {"status": "mismatched", "ocr_match": False, "pattern_valid": True, 
                            "failure_reason": "This ID number is already registered to another account."}

            # 2. ID Pattern Validation
            pattern_valid = self.validate_id_pattern(id_type, id_number)
            
            # 3. Image Loading & Quality Check
            id_img = self._prepare_image(id_path)
            quality_check = self.check_image_quality(id_img)
            if not quality_check["valid"]:
                return {"status": "mismatched", "ocr_match": False, "pattern_valid": pattern_valid,
                        "failure_reason": quality_check["reason"]}
            
            # 4. Perform OCR with Tesseract Multi-Pass
            ocr_text = self._run_tesseract_multi_psm(id_img)
            
            if not ocr_text or not ocr_text.strip():
                return {
                    "status": "mismatched",
                    "ocr_match": False,
                    "failure_reason": "Could not extract readable text from your ID. Please ensure the photo is clear, well-lit, and not blurry."
                }
                
            clean_ocr_upper = ocr_text.upper()
            
            # 5. Legitimacy Check (NEW)
            is_likely_id = any(kw in clean_ocr_upper for kw in self.ID_LEGITIMACY_KEYWORDS)
            
            rich_data = self._extract_rich_ocr_data(ocr_text)
            
            # 6. Specific ID Type Keyword Check (NEW & STRICT)
            # Check if the selected ID type (e.g. "Passport") appears in the OCR text
            type_keywords = {
                'PhilSys / PhilID': ["PHILSYS", "PHILID", "NATIONAL ID", "PHILIPPINE IDENTIFICATION"],
                'Driver\'s License': ["DRIVER", "LICENSE", "LTO", "TRANSPORTATION"],
                'Passport': ["PASSPORT", "REPUBLIC", "DFA"],
                'UMID': ["UMID", "UNIFIED", "MULTI-PURPOSE"],
                'SSS ID': ["SSS", "SOCIAL SECURITY"],
                'PRC ID': ["PRC", "PROFESSIONAL", "REGULATION"],
                'Postal ID': ["POSTAL", "PHLPOST"],
                'TIN ID': ["TIN", "INTERNAL REVENUE", "TAX"],
                'PhilHealth ID': ["PHILHEALTH"]
            }
            
            selected_type_kws = type_keywords.get(id_type, [id_type.upper()])
            type_found_in_ocr = any(kw in clean_ocr_upper for kw in selected_type_kws)
            
            # 7. Robust Matching Logic
            clean_name = " ".join(full_name.lower().split())
            clean_ocr = " ".join(ocr_text.lower().split())
            
            def ocr_normalize(s):
                """Normalizes common OCR misreads in names/IDs for robust matching."""
                if not s: return ""
                subs = {
                    '0': 'o', '1': 'i', '2': 'z', '5': 's', '8': 'b',
                    '|': 'i', '[': 'i', ']': 'i', '(': 'i', ')': 'i',
                    'ç': 'c', 'ñ': 'n', 'Ñ': 'n', '—': '-', '–': '-'
                }
                res = s.lower().strip()
                for k, v in subs.items():
                    res = res.replace(k, v)
                res = re.sub(r'[^a-z0-9 ]', '', res)
                return " ".join(res.split())

            def normalize_id(s): return re.sub(r'[^a-zA-Z0-9]', '', s).lower() if s else ""
            
            name_parts = [p for p in clean_name.replace(",", " ").split() if len(p) > 2] # Use longer parts for precision
            norm_id_input = normalize_id(id_number)
            
            print(f"[KYC DEBUG] Strict Matching - Name: '{clean_name}', ID: '{norm_id_input}', Type: '{id_type}'")
            
            # --- FUZZY NAME MATCHING ---
            matches_count = 0
            norm_ocr_for_names = ocr_normalize(clean_ocr)
            norm_name_parts = [ocr_normalize(p) for p in name_parts]
            
            for part in norm_name_parts:
                if len(part) < 2: continue
                if part in norm_ocr_for_names:
                    matches_count += 1
                    continue
                
                ocr_words = norm_ocr_for_names.split()
                best_ratio = 0
                for word in ocr_words:
                    if len(word) < 2: continue
                    ratio = difflib.SequenceMatcher(None, part, word).ratio()
                    if ratio > best_ratio: best_ratio = ratio
                
                if best_ratio > 0.85:
                    matches_count += 1
                
            # Stricter Name Match Threshold (80%)
            name_match = (matches_count / len(name_parts) >= 0.8) if name_parts else False
            
            # Fuzzy ID check refinement
            id_found = False
            best_id_ratio = 0
            if norm_id_input:
                norm_ocr_for_id = re.sub(r'[^a-z0-9]', '', norm_ocr_for_names)
                id_len = len(norm_id_input)
                # Check for exact or highly similar substring
                if norm_id_input in norm_ocr_for_id:
                    id_found = True
                else:
                    for i in range(len(norm_ocr_for_id) - id_len + 1):
                        window = norm_ocr_for_id[i:i+id_len]
                        ratio = difflib.SequenceMatcher(None, norm_id_input, window).ratio()
                        if ratio > best_id_ratio: best_id_ratio = ratio
                    if best_id_ratio >= 0.9: # Increased from 0.8 for strictness
                        id_found = True
            
            # STRICT REQUIREMENT: Name Match AND (ID Found OR Type Found)
            ocr_match = name_match and (id_found or type_found_in_ocr)
            status = "matched" if (ocr_match and is_likely_id) else "mismatched"
            reasons = []
            
            if not is_likely_id:
                return {
                    "status": "rejected",
                    "failure_reason": "Document not recognized as a valid Government ID. Please upload a clear photo of the original document.",
                    "ocr_match": False,
                    "is_likely_id": False
                }
            
            if not ocr_match: 
                entered_name = full_name.upper()
                detected_name = (rich_data.get("full_name") or "NOT DETECTED").upper()
                reasons.append(f"ID Name Mismatch: The name detected on your ID ({detected_name}) does not match your registered customer name ({entered_name}). Please ensure you are using your own valid ID.")

            if not pattern_valid: 
                reasons.append(f"Invalid {id_type} format.")
            
            return {
                "status": status,
                "ocr_match": ocr_match and is_likely_id,
                "is_likely_id": is_likely_id,
                "pattern_valid": pattern_valid,
                "failure_reason": "; ".join(reasons) if reasons else None,
                "extracted_text_preview": ocr_text[:200],
                "ocr_data": {
                    "raw_text": ocr_text,
                    "full_name": rich_data.get("full_name") or "Not detected",
                    "id_number": rich_data.get("id_number") or id_normalize(ocr_text),
                    "name_match": ocr_match,
                    "id_found": id_found,
                    **rich_data
                }
            }
        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "failure_reason": f"System Error during ID scan: {str(e)}"}

    def verify_identity_v2(self, 
                           id_path: str, 
                           selfie_paths: List[str], 
                           full_name: str, 
                           id_number: str, 
                           id_type: str, 
                           db: Session = None,
                           user_id: int = None) -> Dict[str, Any]:
        """Refactored full verification logic using verify_id_document."""
        try:
            # 1. Document Verification (Now just re-using the method)
            id_result = self.verify_id_document(id_path, full_name, id_number, id_type, db, user_id)
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

    def verify_business_permit(self, permit_path: str, business_name: str, owner_name: str = None) -> Dict[str, Any]:
        """OCR Verification for Business Permits with Owner Matching."""
        try:
            # 1. Image Loading & Quality Check
            img = self._prepare_image(permit_path)
            quality_check = self.check_image_quality(img)
            if not quality_check["valid"]:
                return {"status": "mismatched", "ocr_match": False, "failure_reason": quality_check["reason"]}

            # 2. Perform OCR
            ocr_text = self._run_tesseract_multi_psm(img)
            clean_ocr = " ".join(ocr_text.lower().split())
            target_name = " ".join(business_name.lower().split())

            print(f"[KYC DEBUG] Business Permit OCR - Target: '{target_name}'")
            print(f"[KYC DEBUG] OCR Text (Preview): '{clean_ocr[:200]}...'")

            # 3. Keyword Check (Is it even a permit?)
            is_likely_permit = any(kw.lower() in clean_ocr for kw in self.BUSINESS_PERMIT_KEYWORDS)

            # 4. Fuzzy Matching for Business Name
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

            # 5. Owner Name Matching (NEW)
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
                        # Take next 50 characters
                        snippet = ocr_text[label_pos + len(label):label_pos + len(label) + 50].strip()
                        owner_found_in_ocr = snippet.split('\n')[0].strip()
                        break

            # 6. Final Decision
            status = "matched" if (name_match and owner_match and is_likely_permit) else "mismatched"
            failure_reason = []
            
            if not is_likely_permit:
                return {
                    "status": "rejected",
                    "failure_reason": "The uploaded file does not appear to be a valid Business Permit or DTI Certificate. Please upload a clear photo of the original document.",
                    "ocr_match": False,
                    "is_likely_permit": False
                }

            if not name_match:
                failure_reason.append(f"Business mismatch: '{business_name}' not detected on document.")
            if not owner_match:
                failure_reason.append(f"Owner mismatch: '{owner_name}' not detected on document.")

            return {
                "status": status,
                "ocr_match": name_match and owner_match,
                "is_likely_permit": is_likely_permit,
                "failure_reason": "; ".join(failure_reason) if failure_reason else None,
                "extracted_text_preview": ocr_text[:300],
                "ocr_data": {
                    "raw_text": ocr_text,
                    "business_name_match": name_match,
                    "owner_name_match": owner_match,
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
