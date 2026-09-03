import re

with open('app/static/js/caterer/bookings.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove viewCustomerKyc function
content = re.sub(r'window\.viewCustomerKyc = function\(event\) \{[\s\S]*?\};', '', content)

# Replace the KYC warning message in confirmAcceptBooking
old_msg = "'This customer has not submitted identity verification (KYC). Are you sure you want to accept this booking?<br><br><small style=\"color:#64748b;\">Recommendation: Audit their identity on the Compliance page first to prevent fake bookings.</small>'"
new_msg = "'This customer has not yet been verified by the Admin. Are you sure you want to accept this booking?'"
content = content.replace(old_msg, new_msg)

with open('app/static/js/caterer/bookings.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('Cleaned bookings.js')
