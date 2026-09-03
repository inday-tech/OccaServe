import re

with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

replacement = '''window.sendPaymentReminder = function(id) {
    if (!id) id = document.getElementById('evModalBookingId').value;
    if (!id) return;
    
    if (window.copyInvoiceLink) {
        window.copyInvoiceLink(id);
    } else {
        const url = window.location.origin + '/customer/booking/' + id + '/invoice';
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(url).then(() => {
                if(window.showNotification) showNotification('Invoice Link Copied!', 'You can now send this payment link/invoice to the customer via FB.', 'success');
                else alert('Invoice Link Copied!\\n' + url);
            }).catch(err => {
                if(window.showNotification) showNotification('Error', 'Failed to copy invoice link', 'error');
                else alert('Failed to copy: ' + url);
            });
        } else {
            // Fallback for non-secure contexts
            const el = document.createElement('textarea');
            el.value = url;
            document.body.appendChild(el);
            el.select();
            document.execCommand('copy');
            document.body.removeChild(el);
            if(window.showNotification) showNotification('Invoice Link Copied!', 'You can now send this payment link/invoice to the customer via FB.', 'success');
            else alert('Invoice Link Copied!\\n' + url);
        }
    }
};'''

js_content = re.sub(r'window\.sendPaymentReminder = function\(id\) \{[\s\S]*?\}\s*;\s*(?=window\.managePreparation)', replacement + '\n\n', js_content)

with open('app/static/js/caterer/calendar.js', 'w', encoding='utf-8') as f:
    f.write(js_content)
print('Fixed clipboard fallback')
