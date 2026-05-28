import glob, re

def update_buttons():
    files = glob.glob(r'c:\OccaServe\OccaShare\templates\caterer\*.html')
    files.append(r'c:\OccaServe\OccaShare\templates\caterer\layout.html')
    
    for fpath in files:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Update Cancel buttons
        # Match <button type="button" class="anything" onclick="foo" style="bar">Cancel</button>
        # We capture the onclick attribute (group 1)
        new_content = re.sub(
            r'<button\s+type=[\'"]button[\'"][^>]*?(onclick=[\'"][^\'"]+[\'"])[^>]*>\s*Cancel\s*</button>',
            r'<button type="button" class="btn-secondary-pro" \1>Cancel</button>',
            content,
            flags=re.IGNORECASE
        )
        
        # Also Close buttons that act like cancel
        new_content = re.sub(
            r'<button\s+type=[\'"]button[\'"][^>]*?(onclick=[\'"][^\'"]+[\'"])[^>]*>\s*Close\s*</button>',
            r'<button type="button" class="btn-secondary-pro" \1>Close</button>',
            new_content,
            flags=re.IGNORECASE
        )

        # Update Primary Save buttons (excluding Archive Now which is destructive)
        # We capture the type, id, form, onclick, etc., if any, but it's simpler to just match Save X
        # Let's match all primary buttons that have btn-primary, btn-primary-pro
        # and strip their inline styles if they are not destructive.
        
        # Replace class="btn-primary" with class="btn-primary-pro"
        new_content = re.sub(r'class=[\'"]btn-primary[\'"]', 'class="btn-primary-pro"', new_content)
        new_content = re.sub(r'class=[\'"]btn-secondary[\'"]', 'class="btn-secondary-pro"', new_content)

        # Clean up inline styles for Cancel, Close, and Save buttons
        new_content = re.sub(
            r'(<button[^>]*?class=[\'"](?:btn-primary-pro|btn-secondary-pro)[\'"][^>]*?)style=[\'"][^\'"]*[\'"]([^>]*>)',
            r'\1\2',
            new_content
        )
        
        if new_content != content:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {fpath}")

if __name__ == '__main__':
    update_buttons()
