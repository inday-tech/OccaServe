import os
import sys

# Add project root to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal, engine
from app.main import app
from app.db import models
from fastapi.testclient import TestClient

# Setup test DB (using same for simplicity, or in-memory sqlite)
# For this environment, we'll just use the app's db but usually we'd mock
client = TestClient(app)

def test_guest_booking_flow():
    # Ensure clean state for this email
    db = SessionLocal()
    existing_user = db.query(models.User).filter(models.User.email == "unit_test_guest@example.com").first()
    if existing_user:
        db.delete(existing_user)
        db.commit()
    
    # Create a caterer first if none exists
    caterer = db.query(models.CatererProfile).first()
    if not caterer:
         # Need an admin/user to create caterer or just insert one manually
         user = models.User(email="caterer@example.com", password_hash="hash", role="caterer")
         db.add(user)
         db.commit()
         caterer = models.CatererProfile(user_id=user.id, business_name="Test Caterer", slug="test-caterer")
         db.add(caterer)
         db.commit()
         db.refresh(caterer)
    
    caterer_id = caterer.id
    db.close()

    # Create dummy image files
    with open("test_id.jpg", "wb") as f:
        f.write(b"dummy_image_content")
    with open("test_selfie.jpg", "wb") as f:
        f.write(b"dummy_image_content")

    try:
        # files = {
        #     "id_document": ("test_id.jpg", open("test_id.jpg", "rb"), "image/jpeg"),
        #     "selfie": ("test_selfie.jpg", open("test_selfie.jpg", "rb"), "image/jpeg")
        # }
        
        # Use context managers to ensure files are closed
        with open("test_id.jpg", "rb") as f_id, open("test_selfie.jpg", "rb") as f_self:
            files = {
                "id_document": ("test_id.jpg", f_id, "image/jpeg"),
                "selfie": ("test_selfie.jpg", f_self, "image/jpeg")
            }

            data = {
                "caterer_id": str(caterer_id),
                "event_date": "2024-12-25",
                "guest_count": "50",
                "full_name": "Unit Test Guest",
                "email": "unit_test_guest@example.com",
                "phone": "555-0199",
                "special_requests": "Test request",
                "package_name": "Test Package"
            }

            response = client.post("/bookings/guest", data=data, files=files)
            
            # print(response.content)
            assert response.status_code == 200
            # Check for success message in HTML
            assert "Booking Request Sent!" in response.text
            assert "Identity Verified" in response.text
            
            # Check for Account Creation Message
            assert "Account Created Successfully" in response.text
            assert "We've generated a temporary password" in response.text

            # Verify User in DB
            # models is already imported at top level
            # SessionLocal is already imported at top level
            db = SessionLocal()
            user = db.query(models.User).filter(models.User.email == "unit_test_guest@example.com").first()
            assert user is not None
            assert user.role == "customer"
            assert user.status == "active"
            assert user.is_verified == True
            db.close()

    finally:
        # Cleanup
        if os.path.exists("test_id.jpg"):
            os.remove("test_id.jpg")
        if os.path.exists("test_selfie.jpg"):
            os.remove("test_selfie.jpg")

if __name__ == "__main__":
    test_guest_booking_flow()
