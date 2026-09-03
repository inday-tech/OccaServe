with open('templates/caterer/bookings.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('id="bookingDetailModal"')
end_idx = content.find('id="rejectReasonModal"')
if end_idx == -1: end_idx = idx + 15000

with open('scratch_booking_modal.html', 'w', encoding='utf-8') as fw:
    fw.write(content[idx:end_idx])
