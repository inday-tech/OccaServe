import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings:
    # CORE CONFIG
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000")
    
    # EMAIL CONFIGURATION
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_FROM = os.getenv("MAIL_FROM", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_TLS = os.getenv("MAIL_TLS", "True") == "True"
    MAIL_SSL = os.getenv("MAIL_SSL", "False") == "True"

    # SOCIAL LOGIN CONFIGURATION
    FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID", "")
    FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET", "")
    
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    INSTAGRAM_CLIENT_ID = os.getenv("INSTAGRAM_CLIENT_ID", "")
    INSTAGRAM_CLIENT_SECRET = os.getenv("INSTAGRAM_CLIENT_SECRET", "")

    # SMS CONFIGURATION
    SMS_API_KEY = os.getenv("SMS_API_KEY", "")
    SMS_SENDER_NAME = os.getenv("SMS_SENDER_NAME", "OccaShare")
    SMS_PROVIDER = os.getenv("SMS_PROVIDER", "semaphore") # semaphore, twilio, or mock

    # KYC CONFIG
    KYC_ENCRYPTION_KEY = os.getenv("KYC_ENCRYPTION_KEY", "")

    # PAYMONGO CONFIG
    PAYMONGO_SECRET_KEY = os.getenv("PAYMONGO_SECRET_KEY", "")
    PAYMONGO_WEBHOOK_SIG_KEY = os.getenv("PAYMONGO_WEBHOOK_SIG_KEY", "")

    # SUPABASE STORAGE CONFIG
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

settings = Settings()
# Env reload trigger
