import os
import cv2
import sys

sys.path.append(os.getcwd())
from app.services.verification import verification_service

def test():
    img_dir = "app/static/uploads/verification"
    # Find all files in directory
    files = [f for f in os.listdir(img_dir)]
    if not files:
        print("No files found")
        return
        
    print(f"Found {len(files)} files. Scanning for a valid image...")
    
    img = None
    selected_file = None
    for file in files:
        img_path = os.path.join(img_dir, file)
        try:
            img = verification_service._prepare_image(img_path)
            if img is not None:
                selected_file = file
                print(f"Successfully prepared image: {file}")
                break
        except Exception as e:
            continue
            
    if img is None:
        print("Could not prepare any image file successfully.")
        return
        
    text = verification_service._run_tesseract_multi_psm(img)
    print("\n--- OCR TEXT ---")
    print(text)
    print("--- END OCR TEXT ---")
    
    rich_data = verification_service._extract_rich_ocr_data(text)
    print("\n--- RICH DATA ---")
    print(rich_data)
    print("--- END RICH DATA ---")

if __name__ == "__main__":
    test()
