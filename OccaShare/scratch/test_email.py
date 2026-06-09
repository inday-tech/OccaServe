import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set env vars to load .env file
from dotenv import load_dotenv
load_dotenv()

from app.services.email import EmailService
from app.core.config import settings

print(f"MAIL_SERVER: {settings.MAIL_SERVER}")
print(f"MAIL_PORT: {settings.MAIL_PORT}")
print(f"MAIL_USERNAME: {settings.MAIL_USERNAME}")

# Try sending email
res = EmailService.send_caterer_account_created_email(
    email="naomicaragay654@gmail.com",
    password="TemporaryPassword123!",
    business_name="Test Caterer"
)
print(f"Send result: {res}")
