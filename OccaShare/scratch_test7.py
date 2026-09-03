with open('templates/caterer/bookings.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('id="bookingDetailModal"')
end_idx = content.find('id="rejectReasonModal"')
if end_idx == -1: end_idx = idx + 10000

print(content[idx:idx+1000])
