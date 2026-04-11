import sys
import os
import cv2
import numpy as np

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.services.verification import verification_service

def test_mediapipe_initialization():
    print("Testing MediaPipe initialization...")
    try:
        from app.services.verification import VerificationService
        service = VerificationService()
        print("SUCCESS: MediaPipe FaceMesh initialized.")
    except Exception as e:
        print(f"FAILURE: {e}")

def test_liveness_logic():
    print("\nTesting Liveness Logic with dummy frames...")
    # Create 3 dummy black frames
    frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(3)]
    
    # Since these are black frames, MediaPipe won't find faces
    result = verification_service._check_liveness_mediapipe(frames)
    print(f"Black Frames Result: {result}")
    
    if result["face_count"] == 0 and result["score"] == 0:
        print("SUCCESS: Correctly handled no-face scenario.")
    else:
        print("FAILURE: Unexpected result for no-face scenario.")

if __name__ == "__main__":
    test_mediapipe_initialization()
    test_liveness_logic()
