import sys
import os
import re

file_path = r'c:\OccaServe\OccaShare\app\routers\kyc.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Patch extract_id
target_extract = '''    # Save file temporarily or permanently
    filename = f"temp_ocr_{current_user.id}_{uuid.uuid4()}.enc"
    path = os.path.join(UPLOAD_DIR, filename)
    encrypted_content = encrypt_data(content)
    with open(path, "wb") as f:
        f.write(encrypted_content)
    
    id_url = f"/api/bookings/kyc/view/{filename}"'''

replace_extract = '''    # Store file directly as Base64 Data URI instead of saving locally
    import base64
    b64 = base64.b64encode(content).decode('utf-8')
    mime = id_document.content_type or "image/jpeg"
    actual_mime = "application/pdf" if "pdf" in mime.lower() else "image/jpeg"
    if "png" in mime.lower(): actual_mime = "image/png"
    id_url = f"data:{actual_mime};base64,{b64}"'''

# 2. Patch upload_id
target_upload = '''    # Encrypt data
    encrypted_content = encrypt_data(content)

    # Save Encrypted File
    filename = f"user_{current_user.id}_id_{uuid.uuid4()}.enc"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(encrypted_content)
    
    id_url = f"/api/bookings/kyc/view/{filename}"'''

replace_upload = '''    # Store directly as Base64 Data URI instead of saving locally
    import base64
    b64 = base64.b64encode(content).decode('utf-8')
    mime = id_document.content_type or "image/jpeg"
    actual_mime = "application/pdf" if "pdf" in mime.lower() else "image/jpeg"
    if "png" in mime.lower(): actual_mime = "image/png"
    id_url = f"data:{actual_mime};base64,{b64}"'''

# 3. Patch verify_full
target_verify = '''    # Save selfie frames (Encrypted)
    selfie_urls = []
    for i, file in enumerate(selfies[:3]):
        content = await file.read()
        file_error = validate_file_type_and_size(content, file.filename)
        if file_error:
             continue # Skip invalid ones

        encrypted_content = encrypt_data(content)
        filename = f"user_{current_user.id}_selfie_{i+1}_{uuid.uuid4()}.enc"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as f:
            f.write(encrypted_content)
        selfie_urls.append(f"/api/bookings/kyc/view/{filename}")'''

replace_verify = '''    # Save selfie frames (as Base64 Data URIs directly)
    import base64
    selfie_urls = []
    for i, file in enumerate(selfies[:3]):
        content = await file.read()
        file_error = validate_file_type_and_size(content, file.filename)
        if file_error:
             continue # Skip invalid ones

        b64 = base64.b64encode(content).decode('utf-8')
        mime = file.content_type or "image/jpeg"
        actual_mime = "image/png" if "png" in mime.lower() else "image/jpeg"
        selfie_urls.append(f"data:{actual_mime};base64,{b64}")'''

content = content.replace('\r\n', '\n')
target_extract = target_extract.replace('\r\n', '\n')
target_upload = target_upload.replace('\r\n', '\n')
target_verify = target_verify.replace('\r\n', '\n')

content = content.replace(target_extract, replace_extract)
content = content.replace(target_upload, replace_upload)
content = content.replace(target_verify, replace_verify)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied to kyc.py")
