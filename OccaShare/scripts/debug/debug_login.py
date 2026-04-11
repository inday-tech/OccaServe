from fastapi.testclient import TestClient
from app.main import app
from app import models
from app.database import SessionLocal

def debug_login():
    client = TestClient(app)
    
    email = "admin@occaserve.com"
    password = "Password123!"
    
    print(f"Attempting login for: {email} with password: {password}")
    
    # 1. Check DB directly first
    db = SessionLocal()
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        print("ERROR: User not found in database!")
        return
    
    print(f"User found in DB. Role: {user.role}, Status: {user.status}, Verified: {user.is_verified}")
    print(f"Password Hash in DB: {user.password_hash[:10]}...")
    
    # 2. Try Login Endpoint
    response = client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=False # follow_redirects for TestClient/httpx
    )
    
    print(f"Login Response Code: {response.status_code}")
    if response.status_code == 303:
        print(f"Success! Redirecting to: {response.headers.get('location')}")
        print(f"Cookies: {response.cookies.get('access_token')}")
    else:
        print("Login Failed!")
        print(response.text)

if __name__ == "__main__":
    debug_login()
