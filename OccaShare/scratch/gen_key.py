from cryptography.fernet import Fernet
import base64

# Test current key
current_key = "vX-xY7r9B0_P8M2zN6L5k4J3i2H1g0F9E8D7C6B5A4I="
print(f"Current key length: {len(current_key)}")

try:
    f = Fernet(current_key.encode())
    print("Current key is VALID")
except Exception as e:
    print(f"Current key is INVALID: {e}")

# Generate a proper key
new_key = Fernet.generate_key().decode()
print(f"\nNew valid Fernet key: {new_key}")
print(f"New key length: {len(new_key)}")
