import re

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Strip existing blocks
    content = content.replace('{% block modals %}', '')
    
    # We will find where the content block should end.
    # The content block should end before <!-- Contract View Modal -->
    content = re.sub(r'<!-- Contract View Modal -->', r'{% endblock %}\n\n{% block modals %}\n<!-- Contract View Modal -->', content, count=1)
    
    # Move the error message to above the payment method for reuploadProofModal
    content = re.sub(
        r'(<div style="margin-bottom: 1rem; background: var\(--dm-slate-50\);.*?</div>\s*</div>)(\s*<div id="reuploadErrorMsg"[^>]*></div>)',
        r'\2\n            \1',
        content, flags=re.DOTALL
    )

    # Move the error message for balanceUploadErrorMsg if it exists
    # Wait, in the HTML, what is the ID for the error message in balanceUploadModal?
    # Let's check balanceUploadModal first, if it exists.
    
    # Clean up multiple endblocks
    # Ensure only ONE endblock before block modals
    content = re.sub(r'\{%\s*endblock\s*%\}\s*\{%\s*endblock\s*%\}\s*\{%\s*block modals\s*%\}', '{% endblock %}\n\n{% block modals %}', content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

fix_file(r'c:\OccaServe\OccaShare\templates\customer\booking_manage.html')
fix_file(r'c:\OccaServe\OccaShare\templates\customer\booking_manage_package.html')
print('Fixed!')
