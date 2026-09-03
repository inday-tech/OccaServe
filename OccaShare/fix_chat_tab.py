import re

with open('app/static/js/caterer/bookings.js', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = re.compile(r'if \(modalSourceMobile\) modalSourceMobile\.innerText = sourceText;', re.DOTALL)

replacement = '''if (modalSourceMobile) modalSourceMobile.innerText = sourceText;

    // Chat Tab Conditional Rendering
    const tabBtnChat = document.getElementById('tabBtnChat');
    const chatOnlineView = document.getElementById('chatOnlineView');
    const chatWalkinView = document.getElementById('chatWalkinView');
    if (tabBtnChat) {
        if (!data.targetUserId || data.targetUserId === 'None' || data.targetUserId === '') {
            tabBtnChat.innerHTML = '<span>Communication</span>';
            if (chatOnlineView) chatOnlineView.style.display = 'none';
            if (chatWalkinView) chatWalkinView.style.display = 'flex';
            
            // Set SMS and Email Links
            const smsLink = document.getElementById('walkinCommSms');
            const emailLink = document.getElementById('walkinCommEmail');
            if (smsLink && data.contact) smsLink.href = 'sms:' + data.contact;
            if (emailLink && data.email) emailLink.href = 'mailto:' + data.email;
        } else {
            tabBtnChat.innerHTML = '<span>Consultation</span>';
            if (chatOnlineView) chatOnlineView.style.display = 'flex';
            if (chatWalkinView) chatWalkinView.style.display = 'none';
        }
    }'''

new_content = pattern.sub(replacement, content)

with open('app/static/js/caterer/bookings.js', 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Fixed Chat Tab')
