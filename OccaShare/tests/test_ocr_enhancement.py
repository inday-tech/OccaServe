import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.services.verification import verification_service

def test_ocr_extraction():
    print("Testing Enhanced OCR Extraction...")
    
    sample_text = """
    REPUBLIC OF THE PHILIPPINES
    NATIONAL ID
    NAME: DELA CRUZ, JUAN PROTACIO
    ID NO: 1234-5678-9012-3456
    DATE OF BIRTH: 15-05-1990
    EXPIRY DATE: 15-05-2030
    ADDRESS: 123 MAGINHAWA ST., DILIMAN, QUEZON CITY, METRO MANILA
    """
    
    result = verification_service._extract_rich_ocr_data(sample_text)
    print(f"Extraction Result: {result}")
    
    expected = {
        "extracted_dob": "15-05-1990",
        "extracted_expiry": "15-05-2030",
        "extracted_address": "ADDRESS: 123 MAGINHAWA ST., DILIMAN, QUEZON CITY, METRO MANILA"
    }
    
    success = True
    for key, val in expected.items():
        if result.get(key) != val:
            print(f"FAILURE: Expected {key} to be '{val}', got '{result.get(key)}'")
            success = False
    
    if success:
        print("SUCCESS: OCR Extraction logic verified.")

if __name__ == "__main__":
    test_ocr_extraction()
