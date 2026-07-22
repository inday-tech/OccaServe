import re

f = r'c:\OccaServe\OccaShare\app\static\js\caterer\bookings.js'
with open(f, 'r', encoding='utf-8') as file:
    content = file.read()

old_show = """function showBookingDetails(btn) {
    var data = btn.dataset;
    currentBookingId = data.id;
    currentEventDate = data.eventDate;"""

new_show = """function showBookingDetails(btn) {
    var data = btn.dataset;
    currentBookingId = data.id;
    currentEventDate = data.eventDate;
    
    // --- POPULATE VERIFICATION TAB ---
    const vCustName = document.getElementById('vCustomerName'); if(vCustName) vCustName.innerText = data.customer || 'N/A';
    const vCustEmail = document.getElementById('vCustomerEmail'); if(vCustEmail) vCustEmail.innerText = data.email || 'N/A';
    const vCustContact = document.getElementById('vCustomerContact'); if(vCustContact) vCustContact.innerText = data.contact || 'N/A';
    const vCustAddress = document.getElementById('vCustomerAddress'); if(vCustAddress) vCustAddress.innerText = data.venue || 'N/A';
    
    const vBookType = document.getElementById('vBookingType'); if(vBookType) vBookType.innerText = data.eventType || 'N/A';
    const vEventDateEl = document.getElementById('vEventDate'); if(vEventDateEl) vEventDateEl.innerText = data.eventDate || 'N/A';
    const vVenue = document.getElementById('vVenue'); if(vVenue) vVenue.innerText = data.venue || 'N/A';
    const vGuestCount = document.getElementById('vGuestCount'); if(vGuestCount) vGuestCount.innerText = data.guestCount || 'N/A';
    
    const vAmountPaid = document.getElementById('vAmountPaid'); if(vAmountPaid) vAmountPaid.innerText = data.amount || '0.00';
    const vRefNumber = document.getElementById('vRefNumber'); if(vRefNumber) vRefNumber.innerText = data.paymentRef || 'N/A';
    const vPaymentStatus = document.getElementById('vPaymentStatus'); 
    if(vPaymentStatus) {
        let pStatus = data.paymentStatus || 'pending';
        let pColor = '#d97706'; let pBg = '#fef3c7';
        if (pStatus === 'paid' || pStatus === 'fully_paid') { pColor = '#16a34a'; pBg = '#dcfce3'; }
        vPaymentStatus.innerHTML = `<span class="badge" style="background: ${pBg}; color: ${pColor};">${pStatus.replace('_', ' ').toUpperCase()}</span>`;
    }
    // ---------------------------------"""

content = content.replace(old_show, new_show)

with open(f, 'w', encoding='utf-8') as out:
    out.write(content)
print('Updated bookings.js with verification tab populator')
