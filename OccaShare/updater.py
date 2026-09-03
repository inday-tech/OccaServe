import glob
import re

for filepath in glob.glob('templates/caterer/*.html'):
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Increment v=12.8 to v=12.9
    new_html = re.sub(r'\?v=12\.8', '?v=12.9', html)
    
    if new_html != html:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_html)
        print(f"Updated CSS version in {filepath}")
