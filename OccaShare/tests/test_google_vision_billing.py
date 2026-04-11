import sys
import os
import io

# Add project root to sys.path
sys.path.append(os.getcwd())

from google.cloud import vision

def check_google_vision():
    print("Checking Google Vision API Status...")
    client = vision.ImageAnnotatorClient()
    
    # Path to a test image
    test_img_path = "app/static/uploads/verification/test_id.jpg"
    
    if not os.path.exists(test_img_path):
        print(f"ERROR: Test image not found at {test_img_path}")
        return

    try:
        with io.open(test_img_path, 'rb') as image_file:
            content = image_file.read()
        
        image = vision.Image(content=content)
        # Simple text detection to test connection/billing
        response = client.text_detection(image=image)
        
        if response.error.message:
            print(f"FAILED: Google Vision API Error: {response.error.message}")
            if "BILLING_DISABLED" in response.error.message:
                print("ACTION REQUIRED: Billing is still disabled in Google Console.")
            return

        annotations = response.text_annotations
        if annotations:
            print("SUCCESS: Google Vision API is WORKING!")
            print(f"Detected Text Preview: {annotations[0].description[:100]}...")
        else:
            print("WARNING: API worked but no text was detected. Check the image content.")
            
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to call Google Vision API: {e}")

if __name__ == "__main__":
    check_google_vision()
