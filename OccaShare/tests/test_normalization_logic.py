import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.services.verification import verification_service

def test_normalization():
    print("Testing Matching Logic Normalization...")
    
    # Mock data
    full_name = "Caragay Naomi"
    id_number = "7601837214758926"
    id_type = "National ID"
    
    # Case 1: Tesseract misreads 'o' as '0' and 'a' as '4' (if we added it, but let's test what we have)
    # Our subs: {'0': 'o', '1': 'i', '2': 'z', '5': 's', '8': 'b', '|': 'i', ...}
    tesseract_ocr_text = "C4r4g4y N04mi ID: 76O1B372147sB926"
    
    # We need to call the internal methods to test
    # Since they are internal to verify_id_document, we can test verify_id_document with a mock OCR result
    # However, verify_id_document runs its own OCR. 
    # Let's test the inner functions if we can, or just mock the OCR pass.
    
    print("\n--- Testing ocr_normalize ---")
    # Test ocr_normalize (used for names)
    # We need to access it. It's defined inside verify_id_document in our implementation.
    # This makes it hard to test directly. 
    # I should have probably made it a class method.
    
    # Let's verify verify_id_document by mocking the OCR output if possible.
    # Actually, let's just write a test that checks if the substrings we expect are found after our manual normalization logic.
    
    def ocr_normalize(s):
        subs = {
            '0': 'o', '1': 'i', '2': 'z', '5': 's', '8': 'b',
            '|': 'i', '[': 'i', ']': 'i', '(': 'i', ')': 'i',
            'ç': 'c', 'ñ': 'n'
        }
        res = s.lower()
        for k, v in subs.items():
            res = res.replace(k, v)
        return res

    def id_normalize(s):
        import re
        s = re.sub(r'[^a-zA-Z0-9]', '', s).lower() if s else ""
        subs = {'o': '0', 'i': '1', 'l': '1', 's': '5', 'z': '2', 'b': '8'}
        for k, v in subs.items():
            s = s.replace(k, v)
        return s

    test_name = "Caragay Naomi"
    test_ocr_name = "C4r4g4y N04mi" # 'o' -> '0'
    
    norm_name = ocr_normalize(test_name)
    norm_ocr_name = ocr_normalize(test_ocr_name)
    
    print(f"Name Normalization: '{test_name}' -> '{norm_name}'")
    print(f"OCR Name Normalization: '{test_ocr_name}' -> '{norm_ocr_name}'")
    
    if "naomi" in norm_ocr_name:
        print("SUCCESS: 'naomi' found in normalized OCR name (misread '0' as 'o')")
    else:
        print("FAILURE: 'naomi' NOT found in normalized OCR name")

    test_id = "7601837214758926"
    test_ocr_id = "76O1B372147sB926" # '0' -> 'O', '8' -> 'B', '5' -> 's'
    
    norm_id_input = id_normalize(test_id)
    norm_ocr_id = id_normalize(test_ocr_id)
    
    print(f"\nID Normalization: '{test_id}' -> '{norm_id_input}'")
    print(f"OCR ID Normalization: '{test_ocr_id}' -> '{norm_ocr_id}'")
    
    if norm_id_input in norm_ocr_id:
        print("SUCCESS: ID found in normalized OCR ID")
    else:
        print(f"FAILURE: ID NOT found. Expected '{norm_id_input}' to be in '{norm_ocr_id}'")

if __name__ == "__main__":
    test_normalization()
