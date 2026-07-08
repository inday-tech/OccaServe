import sys
import base64
import re

file_path = r'c:\OccaServe\OccaShare\app\routers\caterer_portfolio.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace process_image_to_bytes with process_image_to_base64
target_func = '''def process_image_to_bytes(file: UploadFile, max_size=(1920, 1080), quality=85) -> bytes:
    """Compresses image to WebP and returns bytes."""
    try:
        content = file.file.read()
        image = Image.open(io.BytesIO(content))
        
        # Convert to RGB if necessary (e.g., from RGBA or P)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
            
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        image.save(buf, format="WEBP", quality=quality)
        return buf.getvalue()
    except Exception as e:
        print(f"Error processing image: {e}")
        raise HTTPException(status_code=400, detail="Invalid image file format")'''

replace_func = '''def process_image_to_base64(file: UploadFile, max_size=(1920, 1080), quality=85) -> str:
    import base64
    """Compresses image to WebP and returns base64 string."""
    try:
        content = file.file.read()
        image = Image.open(io.BytesIO(content))
        
        # Convert to RGB if necessary (e.g., from RGBA or P)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
            
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        image.save(buf, format="WEBP", quality=quality)
        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        return f"data:image/webp;base64,{b64}"
    except Exception as e:
        print(f"Error processing image: {e}")
        raise HTTPException(status_code=400, detail="Invalid image file format")'''

# Replace Cover Photo Logic
target_cover = '''    # 2. Process Cover Photo
    if cover_photo and cover_photo.filename:
        # Save main cover image locally
        filename = f"{uuid.uuid4().hex}.webp"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        img_bytes = process_image_to_bytes(cover_photo, max_size=(1920, 1080), quality=85)
        
        with open(filepath, "wb") as f:
            f.write(img_bytes)
            
        cover_url = f"/static/uploads/portfolios/{filename}"
        
        if cover_url:
            db.add(models.PortfolioImage(portfolio_id=new_portfolio.id, image_url=cover_url, is_cover=True))
        else:
            raise HTTPException(status_code=500, detail="Failed to save cover photo locally.")'''

replace_cover = '''    # 2. Process Cover Photo
    if cover_photo and cover_photo.filename:
        cover_url = process_image_to_base64(cover_photo, max_size=(1920, 1080), quality=85)
        if cover_url:
            db.add(models.PortfolioImage(portfolio_id=new_portfolio.id, image_url=cover_url, is_cover=True))
        else:
            raise HTTPException(status_code=500, detail="Failed to process cover photo.")'''

# Replace Additional Photos Logic
target_additional = '''    # 3. Process Additional Photos (Limit to 10 for safety)
    if additional_photos:
        count = 0
        for photo in additional_photos:
            if photo.filename and count < 10:
                img_bytes = process_image_to_bytes(photo, max_size=(1920, 1080), quality=85)
                
                filename = f"{uuid.uuid4().hex}.webp"
                filepath = os.path.join(UPLOAD_DIR, filename)
                
                with open(filepath, "wb") as f:
                    f.write(img_bytes)
                    
                img_url = f"/static/uploads/portfolios/{filename}"
                
                if img_url:
                    db.add(models.PortfolioImage(portfolio_id=new_portfolio.id, image_url=img_url, is_cover=False))
                    count += 1'''

replace_additional = '''    # 3. Process Additional Photos (Limit to 10 for safety)
    if additional_photos:
        count = 0
        for photo in additional_photos:
            if photo.filename and count < 10:
                img_url = process_image_to_base64(photo, max_size=(1920, 1080), quality=85)
                if img_url:
                    db.add(models.PortfolioImage(portfolio_id=new_portfolio.id, image_url=img_url, is_cover=False))
                    count += 1'''

# Replace Delete Logic
target_delete = '''    # Delete images from Disk
    for img in portfolio.images:
        try:
            # Handle Local File Deletion
            filename = img.image_url.split('/')[-1]
            filepath = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
            # Delete thumbnail if cover
            if img.is_cover:
                thumb_path = os.path.join(THUMBNAIL_DIR, f"thumb_{filename}")
                if os.path.exists(thumb_path):
                    os.remove(thumb_path)
        except Exception as e:
            print(f"Error deleting image {img.image_url}: {e}")'''

replace_delete = '''    # Base64 images are stored in DB, no local files to delete
    pass'''


content = content.replace('\r\n', '\n')
target_func = target_func.replace('\r\n', '\n')
target_cover = target_cover.replace('\r\n', '\n')
target_additional = target_additional.replace('\r\n', '\n')
target_delete = target_delete.replace('\r\n', '\n')

content = content.replace(target_func, replace_func)
content = content.replace(target_cover, replace_cover)
content = content.replace(target_additional, replace_additional)
content = content.replace(target_delete, replace_delete)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied to portfolio")
