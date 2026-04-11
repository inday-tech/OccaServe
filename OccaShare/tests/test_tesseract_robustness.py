import sys
import os
import cv2
import numpy as np

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.services.verification import verification_service

def test_tesseract_preprocessing():
    print("Testing Enhanced Tesseract Preprocessing...")
    
    # Path to a test image
    test_img_path = "app/static/uploads/verification/test_id.jpg"
    
    if not os.path.exists(test_img_path):
        print(f"ERROR: Test image not found at {test_img_path}")
        return

    # Load image normally (bypass decryption for test)
    img = cv2.imread(test_img_path)
    if img is None:
        print(f"ERROR: Failed to load image at {test_img_path}")
        return

    print(f"Original image shape: {img.shape}")
    
    # 1. Test Deskew
    deskewed = verification_service._deskew(img)
    print("Deskewing completed.")
    
    # 2. Test Tesseract Logic
    print("Running Tesseract Multi-PSM...")
    text = verification_service._run_tesseract_multi_psm(img)
    
    print("\n--- OCR RESULT ---")
    print(text)
    print("------------------")
    
    if len(text.strip()) > 10:
        print("SUCCESS: Tesseract extracted meaningful text.")
    else:
        print("WARNING: Tesseract result is very short or empty.")

if __name__ == "__main__":
    test_tesseract_preprocessing()
