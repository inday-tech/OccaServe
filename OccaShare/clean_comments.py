import re

files = ['templates/caterer/customers.html', 'templates/caterer/bookings.html']
for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace('<!-- Iframe Modal for KYC -->', '<!-- General Iframe Modal -->')
    content = content.replace('<!-- Iframe Modal for MSA & KYC -->', '<!-- General Iframe Modal -->')
    content = content.replace('Personal identity fields are locked for compliance.', 'Personal fields are locked for data protection.')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
print('Cleaned comments')
