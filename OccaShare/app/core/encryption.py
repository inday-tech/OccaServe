from .config import settings
from cryptography.fernet import Fernet
import os

# prioritize environment-based keys for persistence
ENCRYPTION_KEY = settings.KYC_ENCRYPTION_KEY

_key_source = "env"

if not ENCRYPTION_KEY:
    import base64
    import hashlib
    # Derive a key from SECRET_KEY so that all worker processes share the same key
    secret = settings.SECRET_KEY or "occaserve_default_fallback_secret_key"
    hashed = hashlib.sha256(secret.encode()).digest()
    ENCRYPTION_KEY = base64.urlsafe_b64encode(hashed).decode()
    _key_source = "derived"
    print(f"\n{'='*60}")
    print(f"[SECURITY] No KYC_ENCRYPTION_KEY found in environment variables.")
    print(f"[SECURITY] Derived key from SECRET_KEY for multi-worker consistency.")
    print(f"[SECURITY] Derived key: {ENCRYPTION_KEY}")
    print(f"[SECURITY] Please add this variable to your environment/Railway settings to persist it:")
    print(f"  KYC_ENCRYPTION_KEY={ENCRYPTION_KEY}")
    print(f"{'='*60}\n")

try:
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
    if _key_source == "env":
        print(f"[SECURITY] KYC_ENCRYPTION_KEY loaded successfully from environment")
except Exception as e:
    import base64
    import hashlib
    # Fallback to key derived from SECRET_KEY so workers don't mismatch
    secret = settings.SECRET_KEY or "occaserve_default_fallback_secret_key"
    hashed = hashlib.sha256(secret.encode()).digest()
    ENCRYPTION_KEY = base64.urlsafe_b64encode(hashed).decode()
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
    print(f"\n{'='*60}")
    print(f"[SECURITY CRITICAL] KYC_ENCRYPTION_KEY is INVALID: {e}")
    print(f"[SECURITY CRITICAL] Derived fallback key from SECRET_KEY.")
    print(f"[SECURITY CRITICAL] Fallback key: {ENCRYPTION_KEY}")
    print(f"[SECURITY CRITICAL] Please update your environment variables:")
    print(f"  KYC_ENCRYPTION_KEY={ENCRYPTION_KEY}")
    print(f"{'='*60}\n")

def encrypt_data(data: bytes) -> bytes:
    """Encrypt binary data."""
    return cipher_suite.encrypt(data)

def decrypt_data(data: bytes) -> bytes:
    """Decrypt binary data."""
    return cipher_suite.decrypt(data)

