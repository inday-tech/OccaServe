import re

filepath = r'c:\OccaServe\OccaShare\app\services\notification.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

helper_func = '''    @staticmethod
    def _determine_notif_type(title: str, current_type: str = "info") -> str:
        """Auto-detects the semantic notification type for proper UI icons."""
        if current_type in ["Booking", "Payment", "Review", "Verification", "Customer", "Message"]:
            return current_type
            
        lower_title = title.lower()
        if any(k in lower_title for k in ['booking', 'event', 'reservation', 'contract', 'cancelled', 'rejected']):
            return "Booking"
        elif any(k in lower_title for k in ['payment', 'balance', 'deadline', 'settlement', 'downpayment', 'commission', 'proof']):
            return "Payment"
        elif any(k in lower_title for k in ['review', 'rate', 'feedback']):
            return "Review"
        elif any(k in lower_title for k in ['identity', 'verify', 'verification', 'kyc', 'alert', 'application', 'account status']):
            return "Verification"
        elif any(k in lower_title for k in ['customer', 'profile']):
            return "Customer"
        elif any(k in lower_title for k in ['message', 'chat']):
            return "Message"
            
        return "info"
'''

# Insert the helper function after the first method
content = re.sub(r'(\s+@staticmethod\s+async def _send_sms.*?return False)', r'\1\n\n' + helper_func, content, flags=re.DOTALL)

# Now replace all instantiations of models.Notification to use the helper for type
content = re.sub(r'(notif = models\.Notification\([\s\S]*?type=)([^,]+)(,?)', r'\1NotificationService._determine_notif_type(title, \2)\3', content)
content = re.sub(r'(new_notif = models\.Notification\([\s\S]*?title=)([^,]+),([\s\S]*?)(\s*\))', 
                 lambda m: m.group(1) + m.group(2) + ',' + m.group(3) + f',\n            type=NotificationService._determine_notif_type({m.group(2).strip()})\n        )', 
                 content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated notification service')
