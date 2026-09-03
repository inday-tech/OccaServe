with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('id="eventModal"')
end_idx = content.find('id="internalScheduleViewModal"')
if end_idx == -1: end_idx = idx + 3000

with open('scratch_modal_output.txt', 'w', encoding='utf-8') as fw:
    fw.write(content[idx:end_idx])
