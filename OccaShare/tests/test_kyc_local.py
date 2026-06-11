import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.verification import verification_service
import cv2

def test_kyc():
    # Use raw jpg files for testing to avoid decryption issues
    id_path = "/api/bookings/kyc/view/test_id.jpg"
    selfie_paths = ["/api/bookings/kyc/view/test_selfie_1.jpg"]
    
    full_name = "Maria Clara"
    id_number = "1234-5678-9012"
    id_type = "PhilSys / PhilID"
    
    import os
    os.environ["VPS_AI_URL"] = ""
    
    import asyncio
    result = asyncio.run(verification_service.verify_identity_v2(id_path, selfie_paths, full_name, id_number, id_type))
    
    print("\n--- TEST RESULT ---")
    for k, v in result.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    try:
        test_kyc()
    except Exception as e:
        print(f"Error during test: {e}")
