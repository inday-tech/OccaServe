with open('templates/caterer/calendar_backup.html', 'r', encoding='utf-8') as f:
    text = f.read()

start = text.find('<!-- Manage Availability Modal -->')
if start != -1:
    end = text.find('<!-- Walk-in Booking Modal -->', start)
    if end == -1: end = text.find('<script>', start)
    with open('extracted_avail.html', 'w', encoding='utf-8') as out:
        out.write(text[start:end])
    print('Extracted avail successfully.')
else:
    print('Not found')
