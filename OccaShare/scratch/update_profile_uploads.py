import os
import re

f = r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py'
with open(f, 'r', encoding='utf-8') as file:
    content = file.read()

target = """        size_map = {"logo": (400, 400), "cover_image": (1200, 600), "gcash_qr": (300, 300), "maya_qr": (300, 300), "bank_qr": (300, 300)}
        for field_name, file_obj in [("logo", logo_file), ("cover_image", cover_image), ("gcash_qr", gcash_qr), ("maya_qr", maya_qr), ("bank_qr", bank_qr), ("permit", permit_file)]:
            if file_obj and file_obj.filename:
                try:
                    content_bytes = await file_obj.read()
                    if not content_bytes:
                        if field_name == 'permit':
                            return RedirectResponse(url="/caterer/profile?error_msg=The+uploaded+business+permit+file+is+empty.+Please+upload+a+valid+document.", status_code=303)
                        continue
                    
                    if field_name == 'permit':
                        # Permit may be PDF — store raw base64
                        mime = file_obj.content_type or "image/jpeg"
                        if mime.lower() not in ["image/png", "image/jpeg", "image/jpg", "application/pdf"]:
                            return RedirectResponse(url="/caterer/profile?error_msg=Invalid+business+permit+file+type.+Only+PNG,+JPEG,+and+PDF+are+allowed.", status_code=303)
                        data_url = f"data:{mime};base64,{base64.b64encode(content_bytes).decode('utf-8')}"
                        profile.permit_url = data_url
                        profile.permit_status = 'Pending Review'
                        profile.verification_status = 'Pending Review'
                        profile.is_verified = False
                        if profile.user:
                            profile.user.is_verified = False
                    else:
                        max_size = size_map.get(field_name, (600, 600))
                        data_url = process_base64_image(content_bytes, max_size=max_size)
                        attr_name = 'logo_url' if field_name == 'logo' else f"{field_name}_url"
                        setattr(profile, attr_name, data_url)
                        if field_name == 'logo':
                            db_user = db.query(models.User).filter(models.User.id == user.id).first()
                            if db_user:
                                db_user.profile_image_url = data_url
                except Exception as e:
                    import traceback
                    print(f"[IMAGE UPLOAD ERROR] Failed on {field_name}: {str(e)}")
                    traceback.print_exc()"""

replacement = """        size_map = {"logo": (400, 400), "cover_image": (1200, 600), "gcash_qr": (300, 300), "maya_qr": (300, 300), "bank_qr": (300, 300)}
        for field_name, file_obj in [("logo", logo_file), ("cover_image", cover_image), ("gcash_qr", gcash_qr), ("maya_qr", maya_qr), ("bank_qr", bank_qr), ("permit", permit_file)]:
            if file_obj and file_obj.filename:
                try:
                    content_bytes = await file_obj.read()
                    if not content_bytes:
                        if field_name == 'permit':
                            return RedirectResponse(url="/caterer/profile?error_msg=The+uploaded+business+permit+file+is+empty.+Please+upload+a+valid+document.", status_code=303)
                        continue
                    
                    if field_name == 'permit':
                        # Permit may be PDF — save it locally instead of raw base64 to avoid memory crashing Postgres!
                        mime = file_obj.content_type or "image/jpeg"
                        if mime.lower() not in ["image/png", "image/jpeg", "image/jpg", "application/pdf"]:
                            return RedirectResponse(url="/caterer/profile?error_msg=Invalid+business+permit+file+type.+Only+PNG,+JPEG,+and+PDF+are+allowed.", status_code=303)
                        
                        ext = ".pdf" if mime.lower() == "application/pdf" else ".jpg"
                        filename = f"permit_{uuid.uuid4().hex}{ext}"
                        filepath = os.path.join(UPLOAD_DIR, filename)
                        with open(filepath, "wb") as f:
                            f.write(content_bytes)
                            
                        file_url = f"/static/uploads/caterer/{filename}"
                        profile.permit_url = file_url
                        profile.permit_status = 'Pending Review'
                        profile.verification_status = 'Pending Review'
                        profile.is_verified = False
                        if profile.user:
                            profile.user.is_verified = False
                    else:
                        # For logos and QRs, convert to WebP and save locally instead of base64 string
                        from PIL import Image
                        import io
                        max_size = size_map.get(field_name, (600, 600))
                        
                        try:
                            image = Image.open(io.BytesIO(content_bytes))
                            if image.mode in ("RGBA", "P"): image = image.convert("RGB")
                            image.thumbnail(max_size, Image.Resampling.LANCZOS)
                            buf = io.BytesIO()
                            image.save(buf, format="WEBP", quality=85)
                            processed_bytes = buf.getvalue()
                        except Exception as img_e:
                            print(f"Error processing image {field_name}: {img_e}")
                            processed_bytes = content_bytes # Fallback
                            
                        filename = f"{field_name}_{uuid.uuid4().hex}.webp"
                        filepath = os.path.join(UPLOAD_DIR, filename)
                        with open(filepath, "wb") as f:
                            f.write(processed_bytes)
                            
                        file_url = f"/static/uploads/caterer/{filename}"
                        attr_name = 'logo_url' if field_name == 'logo' else f"{field_name}_url"
                        setattr(profile, attr_name, file_url)
                        
                        if field_name == 'logo':
                            db_user = db.query(models.User).filter(models.User.id == user.id).first()
                            if db_user:
                                db_user.profile_image_url = file_url
                except Exception as e:
                    import traceback
                    print(f"[IMAGE UPLOAD ERROR] Failed on {field_name}: {str(e)}")
                    traceback.print_exc()"""

if target in content:
    content = content.replace(target, replacement)
    with open(f, 'w', encoding='utf-8') as out:
        out.write(content)
    print('Updated caterer_dashboard.py to save profile images locally instead of base64')
else:
    print('Target not found')
