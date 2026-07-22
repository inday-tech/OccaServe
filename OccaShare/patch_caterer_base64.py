import sys
import base64
import re

file_path = r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update process_base64_image
target_func = '''def process_base64_image(content_bytes: bytes, max_size=(600, 600), quality=75) -> str:
    """Saves image locally as WebP and returns URL instead of base64."""
    import io
    import uuid
    import os
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(content_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=quality)
        file_bytes = buf.getvalue()
        ext = ".webp"
    except Exception:
        file_bytes = content_bytes
        ext = ".jpg"
        
    filename = f"img_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(file_bytes)
    return f"/static/uploads/caterer/{filename}"'''

replace_func = '''def process_base64_image(content_bytes: bytes, max_size=(600, 600), quality=75) -> str:
    """Compresses image and returns a base64 Data URI."""
    import io
    import base64
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(content_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=quality)
        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        return f"data:image/webp;base64,{b64}"
    except Exception:
        # Fallback to direct base64 if not an image
        b64 = base64.b64encode(content_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{b64}"'''

# 2. Update permit file upload
target_permit = '''                if field_name == 'permit':
                    # Permit may be PDF — store raw base64
                    mime = file_obj.content_type or "image/jpeg"
                    if mime.lower() not in ["image/png", "image/jpeg", "image/jpg", "application/pdf"]:
                        return RedirectResponse(url="/caterer/profile?error_msg=Invalid+business+permit+file+type.+Only+PNG,+JPEG,+and+PDF+are+allowed.", status_code=303)
                    ext = '.pdf' if 'pdf' in mime.lower() else '.jpg'
                    import uuid, os
                    filename = f'permit_{uuid.uuid4().hex}{ext}'
                    filepath = os.path.join(UPLOAD_DIR, filename)
                    with open(filepath, 'wb') as _f:
                        _f.write(content_bytes)
                    data_url = f'/static/uploads/caterer/{filename}'
                    profile.permit_url = data_url'''

replace_permit = '''                if field_name == 'permit':
                    import base64
                    # Permit may be PDF — store raw base64
                    mime = file_obj.content_type or "image/jpeg"
                    if mime.lower() not in ["image/png", "image/jpeg", "image/jpg", "application/pdf"]:
                        return RedirectResponse(url="/caterer/profile?error_msg=Invalid+business+permit+file+type.+Only+PNG,+JPEG,+and+PDF+are+allowed.", status_code=303)
                    
                    # Convert document directly to base64
                    b64 = base64.b64encode(content_bytes).decode('utf-8')
                    # Standardize mime if necessary
                    actual_mime = "application/pdf" if "pdf" in mime.lower() else "image/jpeg"
                    data_url = f"data:{actual_mime};base64,{b64}"
                    profile.permit_url = data_url'''

content = content.replace('\r\n', '\n')
target_func = target_func.replace('\r\n', '\n')
target_permit = target_permit.replace('\r\n', '\n')

content = content.replace(target_func, replace_func)
content = content.replace(target_permit, replace_permit)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied to caterer_dashboard.py")
