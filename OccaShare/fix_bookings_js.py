import re

with open('app/static/js/caterer/bookings.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace sourceText condition
content = content.replace(
    "const sourceText = (!data.targetUserId || data.targetUserId === 'None' || data.targetUserId === '') ? 'Walk-in Booking' : 'Online Booking';",
    "const isWalkin = (data.bookingSource === 'Walk-in' || !data.targetUserId || data.targetUserId === 'None' || data.targetUserId === '');\n    const sourceText = isWalkin ? 'Walk-in Booking' : 'Online Booking';"
)

# Replace KYC condition
content = content.replace(
    "if (!data.targetUserId || data.targetUserId === 'None' || data.targetUserId === '') {",
    "if (isWalkin) {"
)

# Replace Chat condition
content = content.replace(
    "if (!data.targetUserId || data.targetUserId === 'None' || data.targetUserId === '') {",
    "if (isWalkin) {"
)

with open('app/static/js/caterer/bookings.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated bookings.js')
