import os
import re

css_files = [
    r"C:\OccaServe\OccaShare\app\static\css\caterer\alert_modal.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\bookings.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\calendar.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\compliance.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\compliance_verify.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\contract_view.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\customers.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\index.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\ingredients.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\layout.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\menu.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\notifications.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\packages.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\payments.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\profile.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\profile_edit.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\reports.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\reviews.css",
    r"C:\OccaServe\OccaShare\app\static\css\caterer\wall.css",
    r"C:\OccaServe\OccaShare\app\static\css\shared\contract_formal.css",
    r"C:\OccaServe\OccaShare\app\static\css\shared\dashboard_premium.css"
]

def map_size(val_str):
    if val_str.endswith('px'):
        val = float(val_str.replace('px', ''))
        if val <= 12: return 'var(--text-xs)'
        if val <= 14: return 'var(--text-sm)'
        if val <= 16: return 'var(--text-base)'
        if val <= 20: return 'var(--text-lg)'
        if val <= 28: return 'var(--text-xl)'
        return 'var(--text-2xl)'
    elif val_str.endswith('rem'):
        val = float(val_str.replace('rem', ''))
        if val <= 0.8: return 'var(--text-xs)'
        if val <= 0.9: return 'var(--text-sm)'
        if val <= 1.05: return 'var(--text-base)'
        if val <= 1.2: return 'var(--text-lg)'
        if val <= 1.6: return 'var(--text-xl)'
        return 'var(--text-2xl)'
    return None

# Pattern specifically targeting font-size lines to avoid changing icon sizes etc where possible,
# but usually font-size is used for text and icons. Icon sizes in rem are fine to map to text sizes.
pattern = re.compile(r'font-size:\s*([0-9.]+(?:px|rem))\s*(?:!important)?\s*;')

for file_path in css_files:
    if not os.path.exists(file_path):
        continue
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    def replacer(match):
        original = match.group(0)
        val_str = match.group(1)
        # Check if it already uses a var
        if 'var(' in original:
            return original
        
        # Don't replace really large font sizes like 4rem
        if val_str.endswith('rem') and float(val_str.replace('rem', '')) > 2.5:
            return original
        if val_str.endswith('px') and float(val_str.replace('px', '')) > 40:
            return original

        new_val = map_size(val_str)
        if new_val:
            if '!important' in original:
                return f'font-size: {new_val} !important;'
            return f'font-size: {new_val};'
        return original

    # We also need to be careful with layout.css root vars where --text-xs is defined
    if "layout.css" in file_path:
        # Don't replace lines defining the vars themselves
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            if line.strip().startswith('--text-'):
                new_lines.append(line)
            else:
                new_lines.append(pattern.sub(replacer, line))
        new_content = '\n'.join(new_lines)
    else:
        new_content = pattern.sub(replacer, content)

    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {file_path}")
print("Done.")
