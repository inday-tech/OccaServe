import sys
import os
import re

file_path = r'c:\OccaServe\OccaShare\app\services\verification.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Patch _prepare_image
target_prepare_image = '''    def _prepare_image(self, encrypted_path: str, apply_crop: bool = True) -> np.ndarray:
        """Decrypts a file, handles EXIF orientation, and returns an OpenCV BGR image."""
        filename = os.path.basename(encrypted_path.replace('\\\\', '/'))
        real_path = os.path.join("app/static/uploads/verification", filename)
        
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"KYC document not found at {real_path}")

        try:
            with open(real_path, "rb") as f:
                raw_data = f.read()
            
            # Try to decrypt
            try:
                decrypted_data = decrypt_data(raw_data)
                print(f"[KYC DEBUG] Decrypted {filename} successfully.")
            except Exception:
                decrypted_data = raw_data
                print(f"[KYC DEBUG] {filename} was not encrypted, proceeding with raw bytes.")'''

replace_prepare_image = '''    def _prepare_image(self, encrypted_path: str, apply_crop: bool = True) -> np.ndarray:
        """Decrypts a file, handles EXIF orientation, and returns an OpenCV BGR image."""
        if encrypted_path.startswith("data:image"):
            import base64
            base64_data = encrypted_path.split(",")[1]
            decrypted_data = base64.b64decode(base64_data)
        else:
            filename = os.path.basename(encrypted_path.replace('\\\\', '/'))
            real_path = os.path.join("app/static/uploads/verification", filename)
            
            if not os.path.exists(real_path):
                raise FileNotFoundError(f"KYC document not found at {real_path}")
    
            try:
                with open(real_path, "rb") as f:
                    raw_data = f.read()
                
                # Try to decrypt
                try:
                    decrypted_data = decrypt_data(raw_data)
                    print(f"[KYC DEBUG] Decrypted {filename} successfully.")
                except Exception:
                    decrypted_data = raw_data
                    print(f"[KYC DEBUG] {filename} was not encrypted, proceeding with raw bytes.")'''

# 2. Patch _prepare_image_with_status
target_prepare_image_status = '''    def _prepare_image_with_status(self, encrypted_path: str) -> Tuple[np.ndarray, bool]:
        """Decrypts a file, handles EXIF orientation, and returns (OpenCV_BGR_image, crop_succeeded)."""
        filename = os.path.basename(encrypted_path.replace('\\\\', '/'))
        real_path = os.path.join("app/static/uploads/verification", filename)
        
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"KYC document not found at {real_path}")

        try:
            with open(real_path, "rb") as f:
                raw_data = f.read()
            
            try:
                decrypted_data = decrypt_data(raw_data)
            except Exception:
                decrypted_data = raw_data'''

replace_prepare_image_status = '''    def _prepare_image_with_status(self, encrypted_path: str) -> Tuple[np.ndarray, bool]:
        """Decrypts a file, handles EXIF orientation, and returns (OpenCV_BGR_image, crop_succeeded)."""
        if encrypted_path.startswith("data:image"):
            import base64
            base64_data = encrypted_path.split(",")[1]
            decrypted_data = base64.b64decode(base64_data)
        else:
            filename = os.path.basename(encrypted_path.replace('\\\\', '/'))
            real_path = os.path.join("app/static/uploads/verification", filename)
            
            if not os.path.exists(real_path):
                raise FileNotFoundError(f"KYC document not found at {real_path}")
    
            try:
                with open(real_path, "rb") as f:
                    raw_data = f.read()
                
                try:
                    decrypted_data = decrypt_data(raw_data)
                except Exception:
                    decrypted_data = raw_data'''

# 3. Patch verify_identity_v2 reading logic
target_vps_read = '''                    # Read ID image
                    id_filename = os.path.basename(id_path.replace('\\\\', '/'))
                    id_real_path = os.path.join("app/static/uploads/verification", id_filename)
                    with open(id_real_path, "rb") as f:
                        id_raw_data = f.read()
                    try:
                        id_decrypted = decrypt_data(id_raw_data)
                    except Exception:
                        id_decrypted = id_raw_data
                    
                    files.append(("img1", ("id_card.jpg", id_decrypted, "image/jpeg")))
                    
                    # Read and decrypt selfie images
                    for i, sp in enumerate(selfie_paths):
                        selfie_filename = os.path.basename(sp.replace('\\\\', '/'))
                        selfie_real_path = os.path.join("app/static/uploads/verification", selfie_filename)
                        with open(selfie_real_path, "rb") as f:
                            selfie_raw_data = f.read()
                        try:
                            selfie_decrypted = decrypt_data(selfie_raw_data)
                        except Exception:
                            selfie_decrypted = selfie_raw_data'''

replace_vps_read = '''                    # Read ID image
                    if id_path.startswith("data:image"):
                        import base64
                        id_decrypted = base64.b64decode(id_path.split(",")[1])
                    else:
                        id_filename = os.path.basename(id_path.replace('\\\\', '/'))
                        id_real_path = os.path.join("app/static/uploads/verification", id_filename)
                        with open(id_real_path, "rb") as f:
                            id_raw_data = f.read()
                        try:
                            id_decrypted = decrypt_data(id_raw_data)
                        except Exception:
                            id_decrypted = id_raw_data
                    
                    files.append(("img1", ("id_card.jpg", id_decrypted, "image/jpeg")))
                    
                    # Read and decrypt selfie images
                    for i, sp in enumerate(selfie_paths):
                        if sp.startswith("data:image"):
                            import base64
                            selfie_decrypted = base64.b64decode(sp.split(",")[1])
                        else:
                            selfie_filename = os.path.basename(sp.replace('\\\\', '/'))
                            selfie_real_path = os.path.join("app/static/uploads/verification", selfie_filename)
                            with open(selfie_real_path, "rb") as f:
                                selfie_raw_data = f.read()
                            try:
                                selfie_decrypted = decrypt_data(selfie_raw_data)
                            except Exception:
                                selfie_decrypted = selfie_raw_data'''

content = content.replace('\r\n', '\n')
target_prepare_image = target_prepare_image.replace('\r\n', '\n')
target_prepare_image_status = target_prepare_image_status.replace('\r\n', '\n')
target_vps_read = target_vps_read.replace('\r\n', '\n')

content = content.replace(target_prepare_image, replace_prepare_image)
content = content.replace(target_prepare_image_status, replace_prepare_image_status)
content = content.replace(target_vps_read, replace_vps_read)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied to verification.py")
