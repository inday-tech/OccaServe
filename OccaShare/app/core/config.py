import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings:
    # CORE CONFIG
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000")
    
    # EMAIL CONFIGURATION — read fresh from env each time so .env changes
    # are picked up without needing a full server restart
    @property
    def MAIL_USERNAME(self):
        load_dotenv(override=True)
        return os.getenv("MAIL_USERNAME", "")

    @property
    def MAIL_PASSWORD(self):
        load_dotenv(override=True)
        return os.getenv("MAIL_PASSWORD", "")

    @property
    def MAIL_FROM(self):
        load_dotenv(override=True)
        return os.getenv("MAIL_FROM", "")

    @property
    def MAIL_PORT(self):
        return int(os.getenv("MAIL_PORT", 587))

    @property
    def MAIL_SERVER(self):
        return os.getenv("MAIL_SERVER", "smtp.gmail.com")

    @property
    def MAIL_TLS(self):
        return os.getenv("MAIL_TLS", "True") == "True"

    @property
    def MAIL_SSL(self):
        return os.getenv("MAIL_SSL", "False") == "True"

    # SOCIAL LOGIN CONFIGURATION
    FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID", "")
    FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET", "")
    
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    INSTAGRAM_CLIENT_ID = os.getenv("INSTAGRAM_CLIENT_ID", "")
    INSTAGRAM_CLIENT_SECRET = os.getenv("INSTAGRAM_CLIENT_SECRET", "")

    # SMS CONFIGURATION
    SMS_API_KEY = os.getenv("SMS_API_KEY", "")
    SMS_SENDER_NAME = os.getenv("SMS_SENDER_NAME", "OccaServe")
    SMS_PROVIDER = os.getenv("SMS_PROVIDER", "semaphore") # semaphore, twilio, or mock

    # KYC CONFIG
    KYC_ENCRYPTION_KEY = os.getenv("KYC_ENCRYPTION_KEY", "")

    # PAYMONGO CONFIG
    PAYMONGO_SECRET_KEY = os.getenv("PAYMONGO_SECRET_KEY", "")
    PAYMONGO_WEBHOOK_SIG_KEY = os.getenv("PAYMONGO_WEBHOOK_SIG_KEY", "")

    # SUPABASE STORAGE CONFIG
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

    # CLOUDINARY CONFIG
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")

settings = Settings()
# Env reload trigger
