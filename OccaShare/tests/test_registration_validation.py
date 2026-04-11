import os
import sys
from typing import Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routers.auth import is_dummy_email, is_dummy_phone

def test_email_validation():
    print("Testing email validation...")
    # Only Gmail allowed
    assert is_dummy_email("mizzy.events@gmail.com") is None
    assert is_dummy_email("mizzy.events@yahoo.com") == "Only Gmail addresses are allowed"
    assert is_dummy_email("mizzy.events@hotmail.com") == "Only Gmail addresses are allowed"
    
    # Specific patterns (disposable/placeholder)
    assert is_dummy_email("aaa@gmail.com") == "Disposable or placeholder email addresses are not allowed"
    # repetitive chars (local part)
    assert is_dummy_email("aaabbb@gmail.com") == "Invalid email pattern (repetitive characters)"

def test_phone_validation():
    print("Testing phone validation...")
    res1 = is_dummy_phone("09171234567")
    print(f"DEBUG: is_dummy_phone('09171234567') -> '{res1}'")
    assert res1 is None # 11 digits
    assert is_dummy_phone("091712345678") == "Mobile number cannot exceed 11 digits"
    
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
    assert "Password must contain at least one uppercase letter" in response.text
    
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
    assert "Password must contain at least one number" in response.text
    
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
    assert "Password must contain at least one special character" in response.text
    
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
    assert "Only Gmail addresses are allowed" in response.text

if __name__ == "__main__":
    try:
        test_email_validation()
        test_phone_validation()
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
