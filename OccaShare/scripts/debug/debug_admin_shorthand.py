from fastapi.testclient import TestClient
from app.main import app
from app import models
from app.database import SessionLocal

def test_admin_shorthand():
    client = TestClient(app)
    
    # Credentials
    username = "admin"
    password = "Password123!"
    
    print(f"Attempting login with SHORTHAND: {username}")
    
    # Try Login Endpoint
    response = client.post(
        "/auth/login",
        data={"email": username, "password": password},
        follow_redirects=False
    )
    
    print(f"Login Response Code: {response.status_code}")
    if response.status_code == 303:
        location = response.headers.get('location')
        print(f"Success! Redirecting to: {location}")
        if location == "/admin/dashboard":
            print("VERIFICATION PASSED: Shorthand 'admin' redirects to admin dashboard.")
        else:
            print(f"VERIFICATION FAILED: Unexpected redirect to {location}")
    else:
        print("Login Failed!")
        print(response.text)

if __name__ == "__main__":
    test_admin_shorthand()
