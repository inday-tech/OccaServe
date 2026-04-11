import sys
import os
import time
import cv2
import numpy as np
import pytesseract

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.verification import verification_service

def benchmark_component(name, func, *args, **kwargs):
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    print(f"[BENCHMARK] {name:30} : {end - start:.4f} seconds")
    return result

def run_benchmarks():
    print("--- KYC Performance Benchmark ---")
    
    # Create a high-res dummy image (4000x3000)
    print("Creating high-res dummy image (4000x3000)...")
    h, w = 3000, 4000
    img = np.ones((h, w, 3), dtype=np.uint8) * 200
    cv2.putText(img, "REPUBLIC OF THE PHILIPPINES", (int(w*0.2), int(h*0.1)), cv2.FONT_HERSHEY_SIMPLEX, 5, (0,0,0), 10)
    cv2.putText(img, "NAME: MARIA CLARA", (int(w*0.1), int(h*0.3)), cv2.FONT_HERSHEY_SIMPLEX, 6, (0,0,0), 12)
    cv2.putText(img, "ID NO: 1234-5678-9012", (int(w*0.1), int(h*0.5)), cv2.FONT_HERSHEY_SIMPLEX, 6, (0,0,0), 12)
    
    # 1. Quality Check
    benchmark_component("Quality Check (Original)", verification_service._check_image_quality, img)
    
    # 2. OCR Preprocessing + Tesseract
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    benchmark_component("OCR (Original High-Res)", pytesseract.image_to_string, thresh)
    
    # 3. Optimized OCR (Resized)
    max_dim = 1200
    scale = max_dim / max(h, w)
    resized_img = cv2.resize(img, (int(w * scale), int(h * scale)))
    r_h, r_w, _ = resized_img.shape
    
    r_gray = cv2.cvtColor(resized_img, cv2.COLOR_BGR2GRAY)
    r_denoised = cv2.bilateralFilter(r_gray, 9, 75, 75)
    r_thresh = cv2.adaptiveThreshold(r_denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    benchmark_component(f"OCR (Resized to {r_w}x{r_h})", pytesseract.image_to_string, r_thresh)
    
    # 4. Face Detection (Original)
    # Note: Mediapipe usually handles resizing internally but let's see the overhead
    benchmark_component("Face Extraction (Original)", verification_service._extract_face, img)
    benchmark_component("Face Extraction (Resized)", verification_service._extract_face, resized_img)

    # 5. Face Vector (Original)
    benchmark_component("Face Vector (Original)", verification_service._get_face_vector, img)
    benchmark_component("Face Vector (Resized)", verification_service._get_face_vector, resized_img)

if __name__ == "__main__":
    run_benchmarks()
