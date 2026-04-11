import sys
import os
import cv2
import numpy as np

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.verification import verification_service

def create_dummy_images():
    """Create dummy images for testing if real ones aren't available."""
    upload_dir = "app/static/uploads/verification"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Simple ID dummy (Grayish background with clear black text for OCR)
    id_img = np.ones((400, 600, 3), dtype=np.uint8) * 200 
    cv2.putText(id_img, "REPUBLIC OF THE PHILIPPINES", (100, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 2)
    cv2.putText(id_img, "NAME: MARIA CLARA", (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,0), 2)
    cv2.putText(id_img, "ID NO: 1234-5678-9012", (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,0), 2)
    cv2.putText(id_img, "BIRTHDAY: 01-01-2000", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,0), 2)
    cv2.imwrite(os.path.join(upload_dir, "test_id.jpg"), id_img)
    
    # Selfie dummies (Mediapipe needs a real face, so these might fail EAR but let's see if it crashes)
    selfie = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.imwrite(os.path.join(upload_dir, "test_selfie_1.jpg"), selfie)
    cv2.imwrite(os.path.join(upload_dir, "test_selfie_2.jpg"), selfie)
    cv2.imwrite(os.path.join(upload_dir, "test_selfie_3.jpg"), selfie)
    
    return "test_id.jpg", ["test_selfie_1.jpg", "test_selfie_2.jpg", "test_selfie_3.jpg"]

def test_real_kyc():
    # Force use dummies for clean verification of logic
    print("Forcing dummy images for clean test...")
    id_filename, selfie_filenames = create_dummy_images()

    id_path = f"/api/bookings/kyc/view/{id_filename}"
    selfie_paths = [f"/api/bookings/kyc/view/{s}" for s in selfie_filenames]
    
    full_name = "Maria Clara"
    id_number = "1234-5678-9012"
    id_type = "PhilID (National ID)"
    
    print(f"\n--- Starting Real KYC Test ---")
    print(f"Target Name: {full_name}")
    print(f"Target ID: {id_number}")
    
    result = verification_service.verify_identity_v2(id_path, selfie_paths, full_name, id_number, id_type)
    
    print("\n--- RESULTS ---")
    print(f"Status: {result.get('status')}")
    print(f"Fraud Score: {result.get('fraud_score')}")
    print(f"Liveness Status: {result.get('liveness_status')} (Score: {result.get('liveness_score')})")
    print(f"Face Similarity: {result.get('face_similarity')}")
    print(f"OCR Match: {result.get('ocr_match')}")
    
    ocr_data = result.get('ocr_data', {})
    print(f"Extracted DOB: {ocr_data.get('extracted_dob')}")
    print(f"Extracted Expiry: {ocr_data.get('extracted_expiry')}")
    print(f"Extracted Address: {ocr_data.get('extracted_address')}")
    
    quality = ocr_data.get('quality', {})
    if quality:
        print(f"Image Quality: {'PASS' if quality.get('quality_pass') else 'FAIL'}")
        print(f" - Variance: {quality.get('variance', 0):.2f}")
        print(f" - Glare: {quality.get('glare_ratio', 0)*100:.1f}%")

    if result.get('failure_reason'):
        print(f"Status/Failure Reason: {result.get('failure_reason')}")
    print(f"EAR Values: {ocr_data.get('blink_ear')}")

if __name__ == "__main__":
    test_real_kyc()
