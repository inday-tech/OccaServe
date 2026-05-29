import os
import io
import re
import cv2
import time
import urllib.request
import numpy as np
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
import traceback
from PIL import Image, ImageOps

# DeepFace import
from deepface import DeepFace

# MediaPipe — correct import path for mediapipe 0.10.x
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions

# EasyOCR reader — initialised lazily in startup event
import easyocr
easyocr_reader = None

# MediaPipe model paths
MODEL_DIR = "/app/models"
MODEL_PATH = os.path.join(MODEL_DIR, "face_landmarker.task")
os.makedirs(MODEL_DIR, exist_ok=True)

# Global Landmarker instance
_landmarker = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Download models and warm up AI libraries on startup."""
    global easyocr_reader, _landmarker

    # 1. Download MediaPipe model if missing
    if not os.path.exists(MODEL_PATH):
        print(f"[AI Server] Downloading MediaPipe face landmarker model to {MODEL_PATH}...")
        try:
            model_url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
            urllib.request.urlretrieve(model_url, MODEL_PATH)
            print("[AI Server] MediaPipe model downloaded.")
        except Exception as e:
            print(f"[AI Server] WARNING: Failed to download MediaPipe model: {e}")

    # 2. Initialise EasyOCR reader
    print("[AI Server] Initialising EasyOCR reader...")
    try:
        easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        print("[AI Server] EasyOCR ready.")
    except Exception as e:
        print(f"[AI Server] WARNING: EasyOCR init failed: {e}")

    # 3. Warm-up MediaPipe FaceLandmarker
    if os.path.exists(MODEL_PATH):
        try:
            base_options = BaseOptions(model_asset_path=MODEL_PATH)
            options = FaceLandmarkerOptions(base_options=base_options, num_faces=1)
            _landmarker = FaceLandmarker.create_from_options(options)
            print("[AI Server] MediaPipe FaceLandmarker ready.")
        except Exception as e:
            print(f"[AI Server] WARNING: MediaPipe FaceLandmarker init failed: {e}")

    yield  # --- server is running ---
    print("[AI Server] Shutting down.")


app = FastAPI(
    title="OccaServe AI Processing API",
    description="Dedicated server for high-performance OCR, DeepFace verification, and Liveness Detection.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: Optional[str] = Security(api_key_header)):
    expected_key = os.getenv("VPS_API_KEY")
    if expected_key:
        if not api_key or api_key != expected_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API Key (X-API-Key header)."
            )
    return api_key


def get_landmarker():
    if _landmarker is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MediaPipe FaceLandmarker is not yet initialised. Please retry in a moment."
        )
    return _landmarker

# --- OCR Preprocessing Utilities ---

def deskew(image: np.ndarray) -> np.ndarray:
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.bitwise_not(gray)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) == 0:
            return image
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) < 0.5 or abs(angle - 90) < 0.5 or abs(angle + 90) < 0.5:
            return image
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    except Exception as e:
        print(f"[OCR Utility] Deskew failed: {e}")
        return image

def auto_crop(image: np.ndarray) -> np.ndarray:
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 30, 150)
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return image
        c = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)
        if w > image.shape[1] * 0.5 and h > image.shape[0] * 0.5:
            return image[y:y+h, x:x+w]
        return image
    except Exception as e:
        print(f"[OCR Utility] Auto-crop failed: {e}")
        return image

def preprocess_for_ocr(image: np.ndarray, aggressive: bool = False) -> np.ndarray:
    try:
        image = deskew(image)
        image = auto_crop(image)

        height, width = image.shape[:2]
        scaling_factor = 4.0 if aggressive else (3.0 if height < 600 else (2.0 if height < 800 else 1.5))
        upscaled = cv2.resize(image, (int(width * scaling_factor), int(height * scaling_factor)), interpolation=cv2.INTER_CUBIC)
        
        gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
        gray = cv2.normalize(gray, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
        
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel_sharpen)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))
        bg = cv2.morphologyEx(sharpened, cv2.MORPH_DILATE, kernel)
        gray_sub = cv2.divide(sharpened, bg, scale=255)

        filtered = cv2.bilateralFilter(gray_sub, 9, 75, 75)

        if aggressive:
            thresh = cv2.adaptiveThreshold(filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 5)
            kernel_clean = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_clean, iterations=1)
        else:
            thresh = cv2.adaptiveThreshold(filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 3)
        
        return thresh
    except Exception as e:
        print(f"[OCR Utility] Preprocessing failed: {e}")
        traceback.print_exc()
        return image

def group_ocr_results_into_lines(results: List[tuple], y_tolerance: int = 15) -> str:
    """
    Groups EasyOCR bounding boxes into lines based on their vertical position.
    This preserves the layout of the ID card, making regex parsing much more accurate.
    """
    if not results:
        return ""
        
    # Sort results primarily by Y-coordinate (top to bottom), then X (left to right)
    # Bbox format: [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
    # We use the top-left y-coordinate (r[0][0][1]) for sorting
    sorted_results = sorted(results, key=lambda r: (r[0][0][1], r[0][0][0]))
    
    lines = []
    current_line = []
    
    for bbox, text, conf in sorted_results:
        clean_text = text.strip()
        if not clean_text or conf < 0.10: # Very lenient confidence to catch faint text
            continue
            
        # Get the top-left y-coordinate of the current bounding box
        y_center = (bbox[0][1] + bbox[2][1]) / 2
        
        if not current_line:
            current_line.append((bbox, clean_text, conf, y_center))
        else:
            # Compare with the average y-center of the current line
            avg_y_center = sum(item[3] for item in current_line) / len(current_line)
            
            if abs(y_center - avg_y_center) <= y_tolerance:
                # Still on the same line
                current_line.append((bbox, clean_text, conf, y_center))
            else:
                # Start a new line
                # Sort the completed line by X-coordinate before saving
                current_line.sort(key=lambda item: item[0][0][0])
                line_text = " ".join(item[1] for item in current_line)
                lines.append(line_text)
                
                # Start new line
                current_line = [(bbox, clean_text, conf, y_center)]
                
    # Add the last line
    if current_line:
        current_line.sort(key=lambda item: item[0][0][0])
        line_text = " ".join(item[1] for item in current_line)
        lines.append(line_text)
        
    return "\n".join(lines)

# --- Face Detection Utilities ---

def detect_faces(image: np.ndarray) -> bool:
    try:
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
        return len(faces) > 0
    except Exception as e:
        print(f"[OCR Utility] Face detection failed: {e}")
        return False

# --- Liveness Detection Utilities ---

def calculate_ear(landmarks, eye_indices) -> float:
    # Vertical distances
    v1 = np.linalg.norm(np.array([landmarks[eye_indices[1]].x, landmarks[eye_indices[1]].y]) - 
                        np.array([landmarks[eye_indices[5]].x, landmarks[eye_indices[5]].y]))
    v2 = np.linalg.norm(np.array([landmarks[eye_indices[2]].x, landmarks[eye_indices[2]].y]) - 
                        np.array([landmarks[eye_indices[4]].x, landmarks[eye_indices[4]].y]))
    # Horizontal distance
    h = np.linalg.norm(np.array([landmarks[eye_indices[0]].x, landmarks[eye_indices[0]].y]) - 
                       np.array([landmarks[eye_indices[3]].x, landmarks[eye_indices[3]].y]))
    
    return (v1 + v2) / (2.0 * h) if h > 0 else 0.0

def run_liveness_check(images: List[np.ndarray]) -> dict:
    landmarker = get_landmarker()
    ears = []
    nose_tips = []
    face_detected_count = 0
    occlusion_detected = False
    occlusion_reason = None

    for img in images:
        try:
            rgb_data = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_data)
            detection_result = landmarker.detect(mp_image)
        except Exception as e:
            print(f"[Liveness] MediaPipe landmarker failed: {e}")
            continue

        if detection_result.face_landmarks:
            face_detected_count += 1
            landmarks = detection_result.face_landmarks[0]

            # Occlusion Check (eyes, mouth, nose within boundaries)
            critical_indices = [33, 133, 362, 263, 1, 61, 291]
            if any(landmarks[i].x < 0 or landmarks[i].x > 1 or landmarks[i].y < 0 or landmarks[i].y > 1 for i in critical_indices):
                occlusion_detected = True
                occlusion_reason = "Face landmarks out of frame. Please stay centered."

            # Yaw: Eye-to-nose distance ratio
            e_dist_l = np.linalg.norm(np.array([landmarks[33].x, landmarks[33].y]) - np.array([landmarks[1].x, landmarks[1].y]))
            e_dist_r = np.linalg.norm(np.array([landmarks[263].x, landmarks[263].y]) - np.array([landmarks[1].x, landmarks[1].y]))
            yaw_ratio = e_dist_l / e_dist_r if e_dist_r > 0 else 5.0

            if yaw_ratio > 3.0 or yaw_ratio < 0.33:
                occlusion_detected = True
                occlusion_reason = "Please face the camera directly. No masks or sunglasses allowed."

            # Scale/Crop verification
            xs = [l.x for l in landmarks]
            ys = [l.y for l in landmarks]
            face_w = max(xs) - min(xs)

            if face_w < 0.2:
                occlusion_detected = True
                occlusion_reason = "Face is too far from the camera."
            elif face_w > 0.9:
                occlusion_detected = True
                occlusion_reason = "Face is too close or partially out of frame."

            left_eye = [33, 160, 158, 133, 153, 144]
            right_eye = [362, 385, 387, 263, 373, 380]
            
            ear_l = calculate_ear(landmarks, left_eye)
            ear_r = calculate_ear(landmarks, right_eye)
            ears.append((ear_l + ear_r) / 2.0)
            nose_tips.append(np.array([landmarks[1].x, landmarks[1].y, landmarks[1].z]))

    # Compute variance and movement
    ear_variance = np.var(ears) if len(ears) > 1 else 0.0
    movement = 0.0
    if len(nose_tips) > 1:
        movement = np.mean([np.linalg.norm(nose_tips[i] - nose_tips[i-1]) for i in range(1, len(nose_tips))])

    liveness_score = 0.0
    if face_detected_count == len(images) and not occlusion_detected:
        liveness_score += 0.4
        if ear_variance > 0.001:
            liveness_score += 0.3
        if movement > 0.01:
            liveness_score += 0.3

    return {
        "success": face_detected_count > 0,
        "score": float(liveness_score),
        "face_count": face_detected_count,
        "occlusion_detected": occlusion_detected,
        "failure_reason": occlusion_reason,
        "ear_variance": float(ear_variance),
        "movement": float(movement)
    }

# --- API Endpoints ---

@app.get("/health")
async def health():
    ocr_ready = easyocr_reader is not None
    mp_ready = _landmarker is not None
    return {
        "status": "healthy",
        "gpu": False,
        "easyocr": ocr_ready,
        "mediapipe": mp_ready,
        "ready": ocr_ready,
    }

@app.get("/debug", dependencies=[Depends(verify_api_key)])
async def debug_info():
    import psutil
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return {
        "status": "online",
        "memory_mb": mem_info.rss / 1024 / 1024,
        "easyocr_loaded": easyocr_reader is not None,
        "mediapipe_loaded": _landmarker is not None,
        "python_version": sys.version
    }

@app.post("/ocr", dependencies=[Depends(verify_api_key)])
async def ocr(
    image: UploadFile = File(...),
    id_type: Optional[str] = Form("Unknown"),
    preprocess: bool = Form(True)
):
    try:
        contents = await image.read()
        pil_img = Image.open(io.BytesIO(contents))
        pil_img = ImageOps.exif_transpose(pil_img)
        raw_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        face_visible = detect_faces(raw_img)

        preprocessed_img = preprocess_for_ocr(raw_img, aggressive=False) if preprocess else raw_img

        if easyocr_reader is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="EasyOCR is still initialising. Please retry in a moment."
            )

        # First pass: EasyOCR on raw image because deep learning OCR performs best on natural color inputs.
        print(f"[AI Server] Running OCR pass 1 (Raw Image)...")
        raw_results = easyocr_reader.readtext(raw_img, detail=1, paragraph=False)
        
        raw_text = group_ocr_results_into_lines(raw_results)
        
        raw_word_data = []
        for (bbox, text, conf) in raw_results:
            clean_text = text.strip()
            if clean_text and conf > 0.10:
                raw_word_data.append({
                    "word": clean_text,
                    "conf": int(conf * 100),
                    "bbox": [[int(coord) for coord in pt] for pt in bbox]
                })

        final_text = raw_text
        final_word_data = raw_word_data

        if preprocess and (len(final_text.strip()) < 50):
            print(f"[AI Server] Raw text too short ({len(final_text)} chars). Running pass 2 (Preprocessed)...")
            preproc_results = easyocr_reader.readtext(preprocessed_img, detail=1, paragraph=False)
            
            preproc_text = group_ocr_results_into_lines(preproc_results)
            
            preproc_word_data = []
            for (bbox, text, conf) in preproc_results:
                clean_text = text.strip()
                if clean_text and conf > 0.10:
                    preproc_word_data.append({
                        "word": clean_text,
                        "conf": int(conf * 100),
                        "bbox": [[int(coord) for coord in pt] for pt in bbox]
                    })
            
            if len(preproc_text) > len(final_text):
                final_text = preproc_text
                final_word_data = preproc_word_data

        results = final_word_data
        text_parts = final_text.split() if final_text else []
        word_data = final_word_data

        return {
            "success": True,
            "text": final_text,
            "word_data": word_data,
            "face_visible": face_visible
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AI Server] OCR endpoint failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"OCR processing failed: {str(e)}")

@app.post("/verify", dependencies=[Depends(verify_api_key)])
async def verify(
    img1: Optional[UploadFile] = File(None),
    img2: Optional[UploadFile] = File(None),
    selfies: Optional[List[UploadFile]] = File(None),
    enforce_detection: bool = Form(False)
):
    result = {}

    # 1. Face Verification using DeepFace
    if img1 and img2:
        try:
            # Read files into memory
            img1_bytes = await img1.read()
            img2_bytes = await img2.read()

            # Load into OpenCV arrays
            img1_arr = cv2.imdecode(np.frombuffer(img1_bytes, np.uint8), cv2.IMREAD_COLOR)
            img2_arr = cv2.imdecode(np.frombuffer(img2_bytes, np.uint8), cv2.IMREAD_COLOR)

            if img1_arr is None or img2_arr is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="One or both uploaded face images could not be decoded."
                )

            # DeepFace Verify
            # Models: VGG-Face, Facenet, Facenet512, OpenFace, DeepFace, DeepID, Dlib, ArcFace, SFace
            # We use VGG-Face (default) or Facenet512 for better accuracy.
            df_result = DeepFace.verify(
                img1_path=img1_arr,
                img2_path=img2_arr,
                enforce_detection=enforce_detection,
                model_name="VGG-Face"
            )

            result["verification"] = {
                "success": True,
                "verified": bool(df_result.get("verified", False)),
                "distance": float(df_result.get("distance", 0.0)),
                "threshold": float(df_result.get("threshold", 0.4)),
                "model": df_result.get("model", "VGG-Face"),
                "similarity_score": float(1 - df_result.get("distance", 0.0))
            }
        except Exception as e:
            print(f"[API Verify] DeepFace verification failed: {e}")
            result["verification"] = {
                "success": False,
                "error": str(e)
            }

    # 2. Liveness Detection using MediaPipe Landmarks
    if selfies and len(selfies) > 0:
        try:
            selfie_images = []
            for selfie in selfies:
                bytes_data = await selfie.read()
                arr = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                if arr is not None:
                    selfie_images.append(arr)

            if not selfie_images:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No valid selfie frames could be decoded."
                )

            liveness_result = run_liveness_check(selfie_images)
            result["liveness"] = liveness_result
        except Exception as e:
            print(f"[API Verify] Liveness check failed: {e}")
            result["liveness"] = {
                "success": False,
                "error": str(e)
            }

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either provide 'img1' and 'img2' for face verification, or 'selfies' list for liveness check, or both."
        )

    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
