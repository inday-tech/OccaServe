import os
import re
import glob

directory = r'C:\OccaServe\OccaShare\templates\caterer'
files = glob.glob(os.path.join(directory, '*.html'))

pattern = re.compile(r'<div\s+class=\s*[\"\'][^\"]*occ-modal-header[^\"]*[\"\'][^>]*>', re.IGNORECASE)

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = pattern.sub(r'<div class="occ-modal-header glass-header">', content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Updated {filepath}')
