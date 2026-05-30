import re

filepath = r'c:\OccaServe\OccaShare\templates\customer\booking_wizard\step_payment.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Move the uploadErrorMsg below the file input
content = re.sub(
    r'(<div id="uploadErrorMsg".*?</div>)(\s*<div style="margin-bottom: 1.25rem;">.*?<input type="file" id="proofImageInput".*?>.*?</div>)',
    r'\2\n\n                      \1',
    content, flags=re.DOTALL
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed step payment!')
