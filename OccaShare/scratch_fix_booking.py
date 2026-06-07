with open(r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('''        return {
            "exists": True, 
            "name": f"{existing_user.first_name} {existing_user.last_name}".strip(),
            "email": existing_user.email,
            "contact": existing_user.phone_number
        }''', '''        return {
            "exists": True, 
            "name": f"{existing_user.first_name} {existing_user.last_name}".strip(),
            "email": existing_user.email,
            "contact": existing_user.phone_number,
            "role": existing_user.role
        }''')

with open(r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

with open(r'c:\OccaServe\OccaShare\app\static\js\caterer\calendar.js', 'r', encoding='utf-8') as f:
    content2 = f.read()

content2 = content2.replace('''                if (data.exists) {
                    badge.style.borderLeftColor = '#0ea5e9';''', '''                if (data.exists) {
                    if (data.role === 'caterer' || data.role === 'admin') {
                        window.setFieldError('manCustEmail', 'Security Violation: This email is registered to a Caterer or Admin account. Only customer accounts can be used for walk-in bookings.');
                        btn.innerHTML = 'Create Booking';
                        btn.disabled = false;
                        return;
                    }
                    badge.style.borderLeftColor = '#0ea5e9';''')

with open(r'c:\OccaServe\OccaShare\app\static\js\caterer\calendar.js', 'w', encoding='utf-8') as f:
    f.write(content2)
