with open('manual_booking_modal_extracted.html', 'r', encoding='utf-8') as f:
    modal_content = f.read()

with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

if '"manBookingModal"' not in content and '"manualBookingModal"' not in content:
    content = content.replace('{% endblock %}', modal_content + '\n{% endblock %}')
    with open('templates/caterer/calendar.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Injected modal into calendar.html')
else:
    print('Modal already in calendar.html')
