import os
import re
import glob

directory = r'C:\OccaServe\OccaShare\templates\caterer'
files = glob.glob(os.path.join(directory, '*.html'))

replacements = {
    r'(?i)#f97316': 'var(--primary-color)',
    r'(?i)#ff7b54': 'var(--primary-color)',
    r'(?i)#f59e0b': 'var(--accent-color)',
    r'(?i)#10b981': 'var(--accent-color)',
}

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    for pattern, repl in replacements.items():
        new_content = re.sub(pattern, repl, new_content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Updated {filepath}')

