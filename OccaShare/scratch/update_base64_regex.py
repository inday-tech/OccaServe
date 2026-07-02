import os
import re

f = r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py'
with open(f, 'r', encoding='utf-8') as file:
    content = file.read()

target1 = """def process_base64_image(content_bytes: bytes, max_size=(600, 600), quality=75) -> str:
    \"\"\"Compress uploaded image to WebP base64 data URL to reduce payload size.\"\"\"
    import base64
    import io
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(content_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=quality)
        encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/webp;base64,{encoded}"
    except Exception:
        encoded = base64.b64encode(content_bytes).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded}\""""

replacement1 = """def process_base64_image(content_bytes: bytes, max_size=(600, 600), quality=75) -> str:
    \"\"\"Saves image locally as WebP and returns URL instead of base64.\"\"\"
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
    return f"/static/uploads/caterer/{filename}\""""

content = content.replace(target1, replacement1)

# Now target 2 using regex to handle the special character safely
content = re.sub(
    r"data_url = f\"data:\{mime\};base64,\{base64\.b64encode\(content_bytes\)\.decode\('utf-8'\)\}\"\s+profile\.permit_url = data_url",
    r"ext = '.pdf' if 'pdf' in mime.lower() else '.jpg'\n                        import uuid, os\n                        filename = f'permit_{uuid.uuid4().hex}{ext}'\n                        filepath = os.path.join(UPLOAD_DIR, filename)\n                        with open(filepath, 'wb') as _f:\n                            _f.write(content_bytes)\n                        data_url = f'/static/uploads/caterer/{filename}'\n                        profile.permit_url = data_url",
    content
)

with open(f, 'w', encoding='utf-8') as out:
    out.write(content)
print('Replaced base64 implementation with local filesystem!')
