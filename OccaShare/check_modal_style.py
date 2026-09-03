with open('manual_booking_modal_extracted.html', 'r', encoding='utf-8') as f:
    content = f.read()
    print('manualBookingModal in content:', 'manualBookingModal' in content)
    print('manBookingModal in content:', 'manBookingModal' in content)
    print('First 150 chars:', content[:150])
