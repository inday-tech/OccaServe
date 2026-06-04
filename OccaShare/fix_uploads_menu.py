import re

with open('app/routers/caterer_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern for add_menu_item
p1 = '''    image_url = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1]
        filename = f"menu_{uuid.uuid4()}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = f"/static/uploads/caterer/{filename}"'''

r1 = '''    import base64
    image_url = None
    if image and image.filename:
        try:
            content_bytes = await image.read()
            if content_bytes:
                encoded = base64.b64encode(content_bytes).decode("utf-8")
                mime = image.content_type or "image/jpeg"
                image_url = f"data:{mime};base64,{encoded}"
        except Exception:
            pass'''

# Pattern for update_menu_item
p2 = '''    if image and image.filename:
        ext = os.path.splitext(image.filename)[1]
        filename = f"menu_{uuid.uuid4()}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        item.image_url = f"/static/uploads/caterer/{filename}"'''

r2 = '''    import base64
    if image and image.filename:
        try:
            content_bytes = await image.read()
            if content_bytes:
                encoded = base64.b64encode(content_bytes).decode("utf-8")
                mime = image.content_type or "image/jpeg"
                item.image_url = f"data:{mime};base64,{encoded}"
        except Exception:
            pass'''

if p1 in content:
    content = content.replace(p1, r1)
    print("Replaced add_menu_item image logic")
if p2 in content:
    content = content.replace(p2, r2)
    print("Replaced update_menu_item image logic")

with open('app/routers/caterer_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
