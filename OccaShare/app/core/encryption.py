from .config import settings
from cryptography.fernet import Fernet
import os

# prioritize environment-based keys for persistence
ENCRYPTION_KEY = settings.KYC_ENCRYPTION_KEY

_key_source = "env"
_secret_key = settings.SECRET_KEY or ""
_secure_key_available = bool(ENCRYPTION_KEY)


def _has_configured_secret(secret: str) -> bool:
    normalized = secret.strip().lower()
    return len(secret) >= 32 and not any(
        marker in normalized for marker in ("your-secret", "change-me", "changeme", "default", "example")
    )

if not ENCRYPTION_KEY:
    import base64
    import hashlib
    # Derive a key from SECRET_KEY so that all worker processes share the same key
    secret = _secret_key or "occaserve_default_fallback_secret_key"
    hashed = hashlib.sha256(secret.encode()).digest()
    ENCRYPTION_KEY = base64.urlsafe_b64encode(hashed).decode()
    _key_source = "derived-secret" if _has_configured_secret(_secret_key) else "unsafe-fallback"

try:
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
except Exception:
    import base64
    import hashlib
    # Fallback to key derived from SECRET_KEY so workers don't mismatch
    secret = _secret_key or "occaserve_default_fallback_secret_key"
    hashed = hashlib.sha256(secret.encode()).digest()
    ENCRYPTION_KEY = base64.urlsafe_b64encode(hashed).decode()
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
    _key_source = "derived-secret" if _has_configured_secret(_secret_key) else "unsafe-fallback"
    _secure_key_available = False


def require_secure_encryption_key() -> None:
    """Prevent new sensitive files being stored with a known development key."""
    if not _secure_key_available and _key_source == "unsafe-fallback":
        raise RuntimeError("Configure KYC_ENCRYPTION_KEY or a strong SECRET_KEY before storing identity documents.")

def encrypt_data(data: bytes) -> bytes:
    """Encrypt binary data."""
    return cipher_suite.encrypt(data)

def decrypt_data(data: bytes) -> bytes:
    """Decrypt binary data."""
    return cipher_suite.decrypt(data)

