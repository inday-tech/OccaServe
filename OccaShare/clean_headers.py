import glob
import re

for filepath in glob.glob('templates/caterer/*.html'):
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Remove inline styles from page-header
    new_html = re.sub(r'<div class="page-header" style="[^"]*">', r'<div class="page-header">', html)
    
    if new_html != html:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_html)
        print(f"Cleaned page-header in {filepath}")
        
    # Also standardize `<div class="dash-header">` to `<div class="page-header">` just in case
    new_html2 = re.sub(r'<div class="dash-header">', r'<div class="page-header">', new_html)
    new_html2 = re.sub(r'<div class="dash-title">', r'<div class="header-title-group">', new_html2)
    
    if new_html2 != new_html:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_html2)
        print(f"Converted dash-header to page-header in {filepath}")
