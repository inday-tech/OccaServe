
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.email import EmailService
from app.core.config import settings

def test_email():
    print(f"Testing email to: {settings.MAIL_USERNAME}")
    print(f"Server: {settings.MAIL_SERVER}:{settings.MAIL_PORT}")
    print(f"From: {settings.MAIL_FROM}")
    
    success = EmailService.send_verification_email(settings.MAIL_USERNAME, "123456")
    if success:
        print("Email sent successfully!")
    else:
        print("Failed to send email. Check stdout/stderr for errors.")

if __name__ == "__main__":
    test_email()
