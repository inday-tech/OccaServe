import re, uuid

def update_cache(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_version = str(uuid.uuid4())[:8]
    content = re.sub(r'main\.js\'\)\s*\}\?v=[0-9a-f]+', f"main.js') }}}}?v={new_version}", content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

update_cache(r'c:\OccaServe\OccaShare\templates\admin\layout.html')
update_cache(r'c:\OccaServe\OccaShare\templates\caterer\layout.html')
update_cache(r'c:\OccaServe\OccaShare\templates\customer\layout.html')
