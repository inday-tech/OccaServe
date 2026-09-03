import re

with open('app/static/js/caterer/bookings.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

replacement = '''
    // --- KYC GATEKEEPER ---
    // Only enforce for Packages. Ala Carte is exempt.
    const isWalkinBooking = rowBtn ? (rowBtn.dataset.bookingSource === 'Walk-in' || !rowBtn.dataset.targetUserId || rowBtn.dataset.targetUserId === 'None') : false;
    
    if (!isVerified && isPackage && !isWalkinBooking) {
'''

js_content = re.sub(
    r'// --- KYC GATEKEEPER ---\s*// Only enforce for Packages\. Ala Carte is exempt\.\s*if \(\!isVerified && isPackage\) \{',
    replacement.strip(),
    js_content
)

with open('app/static/js/caterer/bookings.js', 'w', encoding='utf-8') as f:
    f.write(js_content)
print('Fixed walkin KYC accept gatekeeper in bookings.js')
