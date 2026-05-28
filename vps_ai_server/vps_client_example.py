import os
import httpx
from typing import List, Dict, Any

class VPSAIClient:
    """
    Client for interacting with the OccaServe AI Processing VPS Server.
    Integrate this client into the Railway backend (e.g. inside app/services/verification.py)
    to delegate heavy OCR, DeepFace, and MediaPipe liveness checks.
    """
    
    def __init__(self, base_url: str = None):
        # Fetch URL from environment variables, fallback to domain
        self.base_url = (base_url or os.getenv("VPS_AI_URL", "https://api.occaserve.com")).rstrip("/")

    async def extract_ocr(self, image_bytes: bytes, id_type: str = "Unknown", preprocess: bool = True) -> Dict[str, Any]:
        """
        Sends raw image bytes to the VPS for text extraction using EasyOCR.
        
        Returns:
            dict containing:
                "success": bool
                "text": raw reconstructed text string
                "word_data": list of dicts with word, conf, and bbox coordinates
        """
        url = f"{self.base_url}/ocr"
        files = {"image": ("document.jpg", image_bytes, "image/jpeg")}
        data = {"id_type": id_type, "preprocess": str(preprocess).lower()}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, files=files, data=data, timeout=60.0)
            if response.status_code != 200:
                raise Exception(f"VPS OCR service returned error {response.status_code}: {response.text}")
            return response.json()

    async def verify_faces(self, id_face_bytes: bytes, selfie_bytes: bytes, enforce_detection: bool = False) -> Dict[str, Any]:
        """
        Compares the face in the ID card with the face in the selfie using DeepFace.
        
        Returns:
            dict containing:
                "verification": {
                    "success": bool
                    "verified": bool (match status)
                    "distance": float (face distance)
                    "similarity_score": float
                }
        """
        url = f"{self.base_url}/verify"
        files = {
            "img1": ("id_face.jpg", id_face_bytes, "image/jpeg"),
            "img2": ("selfie.jpg", selfie_bytes, "image/jpeg")
        }
        data = {"enforce_detection": str(enforce_detection).lower()}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, files=files, data=data, timeout=60.0)
            if response.status_code != 200:
                raise Exception(f"VPS Face Verification returned error {response.status_code}: {response.text}")
            return response.json()

    async def check_liveness(self, selfie_frames: List[bytes]) -> Dict[str, Any]:
        """
        Analyzes a sequence of selfie frames for movement and blink variance 
        using MediaPipe FaceLandmarker to detect spoofing.
        
        Returns:
            dict containing:
                "liveness": {
                    "success": bool
                    "score": float (0.0 to 1.0)
                    "face_count": int
                    "occlusion_detected": bool
                    "failure_reason": str
                }
        """
        url = f"{self.base_url}/verify"
        files = []
        for i, frame_bytes in enumerate(selfie_frames):
            files.append(("selfies", (f"selfie_{i}.jpg", frame_bytes, "image/jpeg")))
            
        async with httpx.AsyncClient() as client:
            response = await client.post(url, files=files, timeout=60.0)
            if response.status_code != 200:
                raise Exception(f"VPS Liveness service returned error {response.status_code}: {response.text}")
            return response.json()

    async def verify_identity_full(self, id_bytes: bytes, selfie_frames: List[bytes], id_type: str = "Unknown") -> Dict[str, Any]:
        """
        Runs both DeepFace verification (ID face vs first selfie) and MediaPipe liveness detection
        in a single parallelized request.
        """
        url = f"{self.base_url}/verify"
        files = [
            ("img1", ("id_card.jpg", id_bytes, "image/jpeg")),
            ("img2", ("selfie_main.jpg", selfie_frames[0], "image/jpeg"))
        ]
        for i, frame in enumerate(selfie_frames):
            files.append(("selfies", (f"selfie_{i}.jpg", frame, "image/jpeg")))
            
        async with httpx.AsyncClient() as client:
            response = await client.post(url, files=files, timeout=60.0)
            if response.status_code != 200:
                raise Exception(f"VPS Full Verification failed: {response.text}")
            return response.json()
