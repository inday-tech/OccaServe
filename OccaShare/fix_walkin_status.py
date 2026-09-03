import re

with open('app/routers/caterer_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = re.compile(r'status="confirmed",\s*payment_status=payment_status,')
replacement = 'status="confirmed" if (amount_paid > 0 or payment_status == "paid") else "pending",\npayment_status=payment_status,'

content = content.replace('status="confirmed", \n            payment_status=payment_status, ', replacement)

# Because there might be spacing issues, I'll use regex.
content = re.sub(r'status="confirmed",\s*payment_status=payment_status,', replacement, content)

with open('app/routers/caterer_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated caterer_dashboard.py')
