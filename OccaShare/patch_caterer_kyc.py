import sys
import base64
import re

file_path = r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

target_save_file = '''    def save_file(file_obj, prefix):
        if not file_obj or not file_obj.filename: return None
        
        content = file_obj.file.read()
        from ..core.utils import validate_file_type_and_size
        error = validate_file_type_and_size(content, file_obj.filename)
        if error:
            raise ValueError(error)
            
        ext = file_obj.filename.split('.')[-1].lower()
        filename = f"user_{user.id}_{prefix}_{int(time.time())}.{ext}"
        filepath = os.path.join(upload_dir, filename)
        
        with open(filepath, "wb") as buffer:
            buffer.write(encrypt_data(content))
        return f"/api/bookings/kyc/view/{filename}"'''

replace_save_file = '''    def save_file(file_obj, prefix):
        if not file_obj or not file_obj.filename: return None
        
        content = file_obj.file.read()
        from ..core.utils import validate_file_type_and_size
        error = validate_file_type_and_size(content, file_obj.filename)
        if error:
            raise ValueError(error)
            
        # Instead of saving locally, convert directly to Base64
        import base64
        b64 = base64.b64encode(content).decode('utf-8')
        mime = file_obj.content_type or "image/jpeg"
        actual_mime = "application/pdf" if "pdf" in mime.lower() else "image/jpeg"
        if "png" in mime.lower(): actual_mime = "image/png"
        return f"data:{actual_mime};base64,{b64}"'''

content = content.replace('\r\n', '\n')
target_save_file = target_save_file.replace('\r\n', '\n')

content = content.replace(target_save_file, replace_save_file)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied to caterer_dashboard.py submit_verification save_file")
