import re

with open('app/static/js/caterer/bookings.js', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = re.compile(r'// --- KYC WARNING BANNER ---.*?var kycStatusEl = document.getElementById\(''modalKycStatus''\);\s*if \(kycStatusEl\) \{\s*;\s*primaryActionEl\.style\.display = ''block'';\s*\}\s*\}', re.DOTALL)

replacement = '''// --- KYC WARNING BANNER ---
        var kycStatusEl = document.getElementById('modalKycStatus');
        if (kycStatusEl) {
            if (!data.targetUserId || data.targetUserId === 'None' || data.targetUserId === '') {
                kycStatusEl.innerHTML = <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;"><strong>No website account</strong> &bull; Platform KYC: N/A</div>;
            } else if (!isVerified) {
                kycStatusEl.innerHTML = <span style="color: #c2410c; background: #ffedd5; padding: 2px 6px; border-radius: 4px; font-weight: 700;"><i class="fas fa-clock"></i> Verification Pending by Admin</span>;
            } else {
                kycStatusEl.innerHTML = <span style="color: #15803d; background: #dcfce7; padding: 2px 6px; border-radius: 4px; font-weight: 700;"><i class="fas fa-check-circle"></i> Identity Verified by Admin</span>;
            }
        }'''

new_content = pattern.sub(replacement, content)

with open('app/static/js/caterer/bookings.js', 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Fixed')
