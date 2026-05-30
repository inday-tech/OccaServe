import sys
import re

filepath = r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = {
    'Preparation Started! ??': 'Preparation Started!',
    'Ready for Delivery! ??': 'Ready for Delivery!',
    'Order is in Transit! ??': 'Order is in Transit!',
    'Caterer has Arrived! ??': 'Caterer has Arrived!',
    'Dining Setup Ongoing ???': 'Dining Setup Ongoing',
    'Transaction Completed! ??': 'Transaction Completed!',
    'Booking Confirmed! ??': 'Booking Confirmed!',
    'Payment Fully Verified! ??': 'Payment Fully Verified!',
    'Booking Cancelled ?': 'Booking Cancelled',
    'Booking Rejected ?': 'Booking Rejected',
    'Event Service Completed ?': 'Event Service Completed',
    '?? High Risk Payment Detected! Check AI Scan details.': 'High Risk Payment Detected! Check AI Scan details.'
}

for old, new in replacements.items():
    content = content.replace(old, new)
    # Also handle some generic emoji replacements just in case some missed
    # (Optional, but manual is safer)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Emojis removed from caterer_dashboard.py')
