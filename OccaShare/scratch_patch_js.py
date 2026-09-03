import re

file_path = "templates/caterer/calendar.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace openSidebarEventModal
old_func = r"function openSidebarEventModal\(element\) \{.*?// Ensure modal exists.*?if \(modal\) \{.*?modal\.style\.display = 'flex';.*?\}.*?\}"
new_func = """function openSidebarEventModal(element) {
        const modal = document.getElementById('eventModal');
        
        // Basic data extraction
        const id = element.getAttribute('data-id');
        const customer = element.getAttribute('data-customer') || 'Walk-in Customer';
        const type = element.getAttribute('data-type');
        const title = element.getAttribute('data-title');
        const datetime = element.getAttribute('data-datetime');
        const venue = element.getAttribute('data-venue');
        const packageInfo = element.getAttribute('data-package');
        const paymentStatus = element.getAttribute('data-payment-status') || 'unpaid';
        const bookingStatus = element.getAttribute('data-booking-status') || 'confirmed';
        const prepStatus = element.getAttribute('data-prep-status') || 'not_started';
        const prepDate = element.getAttribute('data-prep-date') || 'TBD';
        const email = element.getAttribute('data-email') || 'N/A';
        const phone = element.getAttribute('data-phone') || 'N/A';
        const total = parseFloat(element.getAttribute('data-total') || '0');
        const paid = parseFloat(element.getAttribute('data-paid') || '0');
        const balance = total - paid;
        
        // DOM Elements
        document.getElementById('detBookingId').textContent = id;
        document.getElementById('evModalBookingId').value = id;
        document.getElementById('detEventHeader').textContent = `${type} • ${datetime}`;
        
        // Status Badges
        const bStatusMap = {
            'pending': { label: 'Pending Confirmation', icon: 'clock', class: 'ps-badge-pending' },
            'confirmed': { label: 'Confirmed', icon: 'check-circle', class: 'ps-badge-confirmed' },
            'completed': { label: 'Completed', icon: 'check-double', class: 'ps-badge-completed' },
            'cancelled': { label: 'Cancelled', icon: 'times-circle', class: 'ps-badge-cancelled' }
        };
        const pStatusMap = {
            'unpaid': { label: 'Unpaid', icon: 'money-bill', class: 'ps-badge-payment' },
            'partially_paid': { label: 'Partially Paid', icon: 'adjust', class: 'ps-badge-ongoing' },
            'fully_paid': { label: 'Fully Paid', icon: 'check', class: 'ps-badge-confirmed' },
            'overdue': { label: 'Overdue', icon: 'exclamation-triangle', class: 'ps-badge-cancelled' }
        };
        
        const bStat = bStatusMap[bookingStatus] || { label: bookingStatus, icon: 'info', class: 'ps-badge-default' };
        const pStat = pStatusMap[paymentStatus] || { label: paymentStatus, icon: 'money-bill', class: 'ps-badge-default' };
        
        document.getElementById('detBookingStatusBadge').className = bStat.class;
        document.getElementById('detBookingStatusBadge').innerHTML = `<i class="fas fa-${bStat.icon}" style="margin-right: 4px;"></i> ${bStat.label}`;
        
        document.getElementById('detPaymentStatusBadge').className = pStat.class;
        document.getElementById('detPaymentStatusBadge').innerHTML = `<i class="fas fa-${pStat.icon}" style="margin-right: 4px;"></i> ${pStat.label}`;
        
        // Next Action Banner Logic
        const nextActionBanner = document.getElementById('nextActionBanner');
        const nextActionText = document.getElementById('nextActionText');
        const nextActionButton = document.getElementById('nextActionButton');
        
        if (bookingStatus === 'cancelled' || bookingStatus === 'completed') {
            nextActionBanner.style.display = 'none';
        } else if (balance > 0) {
            nextActionBanner.style.display = 'block';
            nextActionBanner.style.borderLeftColor = 'var(--primary-color)';
            nextActionText.textContent = `Collect remaining balance of ₱${balance.toLocaleString('en-US', {minimumFractionDigits:2})}.`;
            nextActionButton.textContent = 'Send Payment Reminder';
            nextActionButton.onclick = () => sendPaymentReminder(id);
        } else if (prepStatus === 'not_started') {
            nextActionBanner.style.display = 'block';
            nextActionBanner.style.borderLeftColor = '#10b981';
            nextActionText.textContent = `Start preparation for the upcoming event.`;
            nextActionButton.textContent = 'Open Preparation Checklist';
            nextActionButton.onclick = () => managePreparation(id);
        } else {
            nextActionBanner.style.display = 'none';
        }

        // Customer Info
        document.getElementById('detCustomer').textContent = customer;
        document.getElementById('detCustomerPhone').textContent = phone;
        document.getElementById('detCustomerEmail').textContent = email;
        
        // Event Info
        let typeDisplay = type;
        if (type === 'CAPACITY_FULL') typeDisplay = 'Special Event'; // Fallback fix
        document.getElementById('detType').textContent = typeDisplay;
        document.getElementById('detPackage').textContent = packageInfo;
        
        const guestsMatch = packageInfo.match(/(\\d+)\\s*Guests/);
        document.getElementById('detGuests').textContent = guestsMatch ? `${guestsMatch[1]} Pax` : '--- Pax';
        document.getElementById('detVenue').textContent = venue;
        
        // Financials
        document.getElementById('detTotal').textContent = `₱${total.toLocaleString('en-US', {minimumFractionDigits:2})}`;
        document.getElementById('detPaid').textContent = `₱${paid.toLocaleString('en-US', {minimumFractionDigits:2})}`;
        document.getElementById('detBalance').textContent = `₱${balance.toLocaleString('en-US', {minimumFractionDigits:2})}`;
        
        // Preparation
        const prepStatusMap = {
            'not_started': 'Not Started',
            'scheduled': 'Scheduled',
            'in_preparation': 'In Preparation',
            'ready': 'Ready for Event',
            'completed': 'Completed'
        };
        document.getElementById('detPrepStatus').textContent = prepStatusMap[prepStatus] || prepStatus;
        document.getElementById('detPrepDate').textContent = prepDate === 'TBD' ? 'Not Scheduled' : `Scheduled: ${prepDate}`;
        
        if (modal) {
            modal.style.display = 'flex';
        }
    }"""

content = re.sub(old_func, new_func, content, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("openSidebarEventModal patched.")
