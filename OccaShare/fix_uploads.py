import re

with open('app/routers/caterer_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern for update_profile single file uploads
p1 = '''    # Handle Single File Uploads
    logo_file = logo if (logo and logo.filename) else logo_brand
    for field_name, file_obj in [("logo", logo_file), ("cover_image", cover_image), ("gcash_qr", gcash_qr), ("maya_qr", maya_qr), ("bank_qr", bank_qr)]:
        if file_obj and file_obj.filename:
            ext = os.path.splitext(file_obj.filename)[1]
            filename = f"{field_name}_{uuid.uuid4()}{ext}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(file_obj.file, buffer)
            setattr(profile, f"{field_name}_url" if field_name != 'logo' else 'logo_url', f"/static/uploads/caterer/{filename}")'''

r1 = '''    import base64
    # Handle Single File Uploads
    logo_file = logo if (logo and logo.filename) else logo_brand
    for field_name, file_obj in [("logo", logo_file), ("cover_image", cover_image), ("gcash_qr", gcash_qr), ("maya_qr", maya_qr), ("bank_qr", bank_qr)]:
        if file_obj and file_obj.filename:
            try:
                content_bytes = await file_obj.read()
                if content_bytes:
                    encoded = base64.b64encode(content_bytes).decode("utf-8")
                    mime = file_obj.content_type or "image/jpeg"
                    data_url = f"data:{mime};base64,{encoded}"
                    setattr(profile, f"{field_name}_url" if field_name != 'logo' else 'logo_url', data_url)
            except Exception:
                pass'''

# Pattern for gallery
p2 = '''    # Handle Gallery Uploads (Multiple)
    if gallery:
        for file_obj in gallery:
            if file_obj.filename:
                ext = os.path.splitext(file_obj.filename)[1]
                filename = f"gallery_{uuid.uuid4()}{ext}"
                filepath = os.path.join(UPLOAD_DIR, filename)
                with open(filepath, "wb") as buffer:
                    shutil.copyfileobj(file_obj.file, buffer)
                
                new_gallery_item = models.CatererGallery(
                    caterer_id=profile.id,
                    media_url=f"/static/uploads/caterer/{filename}",
                    media_type="image"
                )
                db.add(new_gallery_item)'''

r2 = '''    # Handle Gallery Uploads (Multiple)
    if gallery:
        for file_obj in gallery:
            if file_obj.filename:
                try:
                    content_bytes = await file_obj.read()
                    if content_bytes:
                        encoded = base64.b64encode(content_bytes).decode("utf-8")
                        mime = file_obj.content_type or "image/jpeg"
                        data_url = f"data:{mime};base64,{encoded}"
                        
                        new_gallery_item = models.CatererGallery(
                            caterer_id=profile.id,
                            media_url=data_url,
                            media_type="image"
                        )
                        db.add(new_gallery_item)
                except Exception:
                    pass'''

if p1 in content:
    content = content.replace(p1, r1)
    print("Replaced single file uploads")
if p2 in content:
    content = content.replace(p2, r2)
    print("Replaced gallery uploads")

with open('app/routers/caterer_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
