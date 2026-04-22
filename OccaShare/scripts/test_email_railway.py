"""
Test email sending on Railway environment
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Test email credentials
print("=" * 50)
print("EMAIL CONFIGURATION TEST")
print("=" * 50)

MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
MAIL_FROM = os.getenv("MAIL_FROM", "")
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000")

print(f"From Email: {MAIL_FROM}")
print(f"SMTP Server: {MAIL_SERVER}:{MAIL_PORT}")
print(f"Site URL: {SITE_URL}")
print(f"Password configured: {'Yes' if MAIL_PASSWORD else 'No'}")
print()

# Test connection
print("Testing SMTP connection...")
try:
    import smtplib
    server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10)
    server.starttls()
    
    # Clean password (remove spaces)
    clean_password = MAIL_PASSWORD.replace(" ", "").strip() if MAIL_PASSWORD else ""
    
    print(f"  → Connected to {MAIL_SERVER}")
    print(f"  → Attempting login with {MAIL_USERNAME}...")
    
    server.login(MAIL_USERNAME, clean_password)
    print(f"  ✓ LOGIN SUCCESSFUL!")
    
    server.quit()
    print()
    print("✅ Email configuration is working!")
    
except smtplib.SMTPAuthenticationError as e:
    print(f"  ✗ LOGIN FAILED: {str(e)}")
    print()
    print("❌ Email authentication error!")
    print("   Check:")
    print("   - Gmail App Password is correct")
    print("   - 2-Factor Authentication is enabled")
    print("   - https://myaccount.google.com/apppasswords")
    sys.exit(1)
    
except smtplib.SMTPException as e:
    print(f"  ✗ SMTP ERROR: {str(e)}")
    print()
    print("❌ SMTP connection error!")
    print("   Check firewall and port 587 access")
    sys.exit(1)
    
except Exception as e:
    print(f"  ✗ ERROR: {str(e)}")
    sys.exit(1)

print()
print("=" * 50)
print("RECOMMENDATIONS:")
print("=" * 50)
print("1. Update SITE_URL in Railway to your Railway domain")
print("2. Ensure MAIL_PASSWORD is 16-character Gmail App Password")
print("3. Check Gmail account 2FA is enabled")
print("4. For production, consider using SendGrid or Resend")
