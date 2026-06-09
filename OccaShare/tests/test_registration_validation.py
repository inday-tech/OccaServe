import os
import sys
from typing import Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routers.auth import is_dummy_email, is_dummy_phone
from app.core.utils import is_valid_business_name, is_valid_person_name

def test_email_validation():
    print("Testing email validation...")
    # Only Gmail allowed
    assert is_dummy_email("mizzy.events@gmail.com") is None
    assert is_dummy_email("mizzy.events@yahoo.com") == "Only @gmail.com addresses are permitted for platform security"
    assert is_dummy_email("mizzy.events@hotmail.com") == "Only @gmail.com addresses are permitted for platform security"
    
    # Specific patterns (disposable/placeholder)
    assert is_dummy_email("aaa@gmail.com") == "Please use a real, professional email prefix"
    # repetitive chars (local part)
    assert is_dummy_email("aaabbb@gmail.com") == "Invalid email pattern (repetitive characters detected)"

def test_phone_validation():
    print("Testing phone validation...")
    res1 = is_dummy_phone("09171234567")
    print(f"DEBUG: is_dummy_phone('09171234567') -> '{res1}'")
    assert res1 is None # 11 digits
    assert is_dummy_phone("091712345678") == "Mobile number must be exactly 11 digits"
    
    # No 3+ repetitive digits
    assert is_dummy_phone("09111234567") == "Mobile number contains too many repetitive digits (e.g., 111)"
    assert is_dummy_phone("09177734567") == "Mobile number contains too many repetitive digits (e.g., 111)"
    assert is_dummy_phone("09171222567") == "Mobile number contains too many repetitive digits (e.g., 111)"
    
    # Real number check (dummy list)
    assert is_dummy_phone("09123456789") == "Please use a real mobile number"

def test_password_complexity():
    print("Testing password complexity via registration endpoint (simulated)...")
    from app.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    # Test internal validation in /auth/register
    # We'll use invalid data to see if it returns those errors
    
    # 1. Missing uppercase
    response = client.post("/auth/register", data={
        "full_name": "Mizzy Garcia",
        "email": "mizzy.garcia@gmail.com",
        "mobile_number": "09171234567",
        "address": "123 Serenity St, Quezon City",
        "password": "password123!",
        "confirm_password": "password123!",
        "role": "customer"
    })
    assert "Password must include: uppercase" in response.text
    
    # 2. Missing number
    response = client.post("/auth/register", data={
        "full_name": "Mizzy Garcia",
        "email": "mizzy.garcia@gmail.com",
        "mobile_number": "09171234567",
        "address": "123 Serenity St, Quezon City",
        "password": "Password!",
        "confirm_password": "Password!",
        "role": "customer"
    })
    assert "Password must include: number" in response.text
    
    # 3. Missing special character
    response = client.post("/auth/register", data={
        "full_name": "Mizzy Garcia",
        "email": "mizzy.garcia@gmail.com",
        "mobile_number": "09171234567",
        "address": "123 Serenity St, Quezon City",
        "password": "Password123",
        "confirm_password": "Password123",
        "role": "customer"
    })
    assert "Password must include: symbol" in response.text
    
    # 4. Valid Gmail check
    response = client.post("/auth/register", data={
        "full_name": "Mizzy Garcia",
        "email": "mizzy.garcia@yahoo.com",
        "mobile_number": "09171234567",
        "address": "123 Serenity St, Quezon City",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "role": "customer"
    })
    assert "Gmail only (@gmail.com)" in response.text

def test_business_name_validation():
    print("Testing business name validation...")
    # Valid business names (including new chars)
    assert is_valid_business_name("Gab Hub's Imported Cuisines") is None
    assert is_valid_business_name("Mary's Kitchen & Catering") is None
    assert is_valid_business_name("R-Events, Inc.") is None
    assert is_valid_business_name("GAB HUBS IMPORTEDS AND RESTORANTE") is None
    
    # Check that person names with accidental keyboard walks are allowed
    assert is_valid_person_name("David Samuel") is None
    assert is_valid_person_name("Lucas Diaz") is None
    
    # Invalid characters (e.g. symbol '@' or '#')
    assert is_valid_business_name("Gab @ Hub") == "Business name should only contain letters, numbers, spaces, dots, apostrophes, hyphens, commas, and ampersands"
    # Purely numeric
    assert is_valid_business_name("12345") == "Business name cannot be purely numeric"
    # Too short
    assert is_valid_business_name("Ab") == "Business name must be at least 3 characters"

if __name__ == "__main__":
    try:
        test_email_validation()
        test_phone_validation()
        test_business_name_validation()
        test_password_complexity()
        print("\nSUCCESS: All registration validation tests passed!")
    except AssertionError as e:
        print(f"\nFAILURE: Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
