import sys
import os
import numpy as np
import cv2
from sqlalchemy.orm import Session

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.services.verification import verification_service
from app.core.encryption import encrypt_data
from app.db.database import SessionLocal

def create_test_id():
    # Create a dummy ID image with some text
    img = np.zeros((400, 600, 3), dtype=np.uint8) + 255 # White background
    cv2.putText(img, "PHILIPPINE NATIONAL ID", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.putText(img, "NAME: JUAN DELA CRUZ", (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, "ID NO: 1234-5678-9012-3456", (50, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    
    # Draw a better "face" for detection
    cv2.circle(img, (500, 150), 60, (0, 0, 0), 2) # Head
    cv2.circle(img, (480, 130), 5, (0, 0, 0), -1) # Eye
    cv2.circle(img, (520, 130), 5, (0, 0, 0), -1) # Eye
    cv2.line(img, (480, 170), (520, 170), (0, 0, 0), 2) # Mouth
    
    # Save temporarily then encrypt
    temp_path = "temp_test_id.jpg"
    cv2.imwrite(temp_path, img)
    
    with open(temp_path, "rb") as f:
        data = f.read()
    
    encrypted_data = encrypt_data(data)
    target_filename = "test_user_id_final.enc"
    target_path = os.path.join("app/static/uploads/verification", target_filename)
    with open(target_path, "wb") as f:
        f.write(encrypted_data)
    os.remove(temp_path)
    return target_filename

def create_test_selfie(index=1):
    # Create a dummy selfie image with a "face"
    img = np.zeros((400, 400, 3), dtype=np.uint8) + 240
    cv2.putText(img, f"Selfie {index}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
    
    # Draw a "face"
    cv2.circle(img, (200, 200), 80, (0, 0, 0), 2) # Head
    cv2.circle(img, (170, 170), 8, (0, 0, 0), -1) # Eye
    cv2.circle(img, (230, 170), 8, (0, 0, 0), -1) # Eye
    cv2.line(img, (170, 240), (230, 240), (0, 0, 0), 2) # Mouth
    
    # Save temporarily then encrypt
    temp_path = f"temp_test_selfie_{index}.jpg"
    cv2.imwrite(temp_path, img)
    with open(temp_path, "rb") as f:
        data = f.read()
    
    encrypted_data = encrypt_data(data)
    target_filename = f"test_user_selfie_{index}_final.enc"
    target_path = os.path.join("app/static/uploads/verification", target_filename)
    with open(target_path, "wb") as f:
        f.write(encrypted_data)
    os.remove(temp_path)
    return target_filename

def test_kyc_logic():
    print("Preparing final test data...")
    id_filename = create_test_id()
    selfie_filenames = [create_test_selfie(1), create_test_selfie(2), create_test_selfie(3)]
    
    id_path = f"/api/bookings/kyc/view/{id_filename}"
    selfie_paths = [f"/api/bookings/kyc/view/{sf}" for sf in selfie_filenames]
    full_name = "JUAN DELA CRUZ"
    id_number = "1234-5678-9012-3456" # Matches PhilID pattern
    id_type = "PhilID (National ID)"

    print(f"Testing KYC logic with accurate data patterns...")
    result = verification_service.verify_identity_v2(id_path, selfie_paths, full_name, id_number, id_type)
    
    print("\n--- Final Verification Result ---")
    for key, value in result.items():
        if key == "ocr_data":
            print(f"{key}:")
            for k, v in value.items():
                if k == "raw_text":
                    print(f"  {k}: {repr(v[:50])}...")
                else:
                    print(f"  {k}: {v}")
        elif key == "extracted_text_preview":
            print(f"{key}: {repr(value)}")
        else:
            print(f"{key}: {value}")
            
    # Cleanup
    os.remove(os.path.join("app/static/uploads/verification", id_filename))
    for sf in selfie_filenames:
        os.remove(os.path.join("app/static/uploads/verification", sf))

if __name__ == "__main__":
    test_kyc_logic()
