import glob, re

def clean_button_icons():
    files = glob.glob(r'c:\OccaServe\OccaShare\templates\caterer\*.html')
    for fpath in files:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find buttons inside .occ-modal-footer or similar and remove <i> tags
        # A simple way is to match <button ...> ... <i class="..."></i> ... </button>
        # We will use re.sub with a custom function to process each button
        
        def replace_icon_in_button(match):
            button_html = match.group(0)
            
            # Only remove <i> if the button is a standard action button (primary/secondary)
            if 'btn-primary' in button_html or 'btn-secondary' in button_html:
                cleaned_button = re.sub(r'<i\s+class=[\'"][^\'"]*[\'"][^>]*></i>\s*', '', button_html)
                return cleaned_button
            
            return button_html

        # Match any button
        new_content = re.sub(r'<button[^>]*>.*?</button>', replace_icon_in_button, content, flags=re.IGNORECASE|re.DOTALL)
        
        if new_content != content:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Removed icons in {fpath}")

if __name__ == '__main__':
    clean_button_icons()
