import os
import glob

replacements = {
    'Logistics & Venue Details': 'Event Details',
    'Guest Logistics': 'Number of Guests',
    'PAX Commitment': 'Guests',
    'Menu Selection Registry': 'Selected Menu',
    'Official Contractual Selection': 'Your Selected Items',
    'Intelligence Actions': 'Actions',
    'Official Archive': 'Your Documents',
    'Transaction History': 'Payment History',
    'Secured by Paymongo Compliance': 'Secured by PayMongo',
    'Signed Legal Commitment': 'View Service Agreement',
    'Contract Total': 'Total Amount',
    'Settled Amount': 'Amount Paid',
    'Fulfillment Details': 'Event Details',
    'Financials & Settlement': 'Payment Details'
}

files = glob.glob('c:/OccaServe/OccaShare/templates/customer/booking_manage*.html')
for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)

print(f'Processed {len(files)} files.')
