from .config import settings
from cryptography.fernet import Fernet
import os

# prioritize environment-based keys for persistence
ENCRYPTION_KEY = settings.KYC_ENCRYPTION_KEY

_key_source = "env"

if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    _key_source = "generated"
    print(f"\n{'='*60}")
    print(f"[SECURITY] No KYC_ENCRYPTION_KEY found in .env")
    print(f"[SECURITY] Generated new key: {ENCRYPTION_KEY}")
    print(f"[SECURITY] Add this to your .env file to persist it:")
    print(f"  KYC_ENCRYPTION_KEY={ENCRYPTION_KEY}")
    print(f"{'='*60}\n")

try:
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
    if _key_source == "env":
        print(f"[SECURITY] KYC_ENCRYPTION_KEY loaded successfully from .env")
except Exception as e:
    # Key is invalid — generate a new valid one and warn loudly
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
    print(f"\n{'='*60}")
    print(f"[SECURITY CRITICAL] KYC_ENCRYPTION_KEY in .env is INVALID: {e}")
    print(f"[SECURITY CRITICAL] Files encrypted with the old key CANNOT be decrypted!")
    print(f"[SECURITY CRITICAL] Generated new valid key: {ENCRYPTION_KEY}")
    print(f"[SECURITY CRITICAL] Update your .env file:")
    print(f"  KYC_ENCRYPTION_KEY={ENCRYPTION_KEY}")
    print(f"{'='*60}\n")

def encrypt_data(data: bytes) -> bytes:
    """Encrypt binary data."""
    return cipher_suite.encrypt(data)

def decrypt_data(data: bytes) -> bytes:
    """Decrypt binary data."""
    return cipher_suite.decrypt(data)

