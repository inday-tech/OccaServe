import re
files = ['templates/caterer/bookings.html', 'templates/caterer/orders.html', 'templates/caterer/index.html']
for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove 'Needs KYC Audit' tags in booking rows
    content = re.sub(r'<span[^>]*>Needs KYC Audit</span>', '', content)
    content = re.sub(r'<span title=\"Needs KYC Audit\"[^>]*>.*?</span>', '', content)
    
    # Remove 'View KYC' buttons
    content = re.sub(r'<button[^>]*id=\"linkViewCustomerAudit\"[^>]*>.*?</button>', '', content)
    
    # Remove 'Customer KYC submissions'
    content = re.sub(r'<p>Customer KYC submissions.</p>', '', content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Cleaned {filepath}')
