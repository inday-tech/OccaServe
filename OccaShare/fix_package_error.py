import re

filepath = r'c:\OccaServe\OccaShare\templates\customer\booking_manage_package.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Move the error message to above the payment method for reuploadProofModal
content = re.sub(
    r'(<div style="margin-bottom: 1rem; background: var\(--dm-slate-50\);.*?</div>\s*</div>)(\s*<div id="reuploadErrorMsg"[^>]*></div>)',
    r'\2\n            \1',
    content, flags=re.DOTALL
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed package reuploadErrorMsg!')
