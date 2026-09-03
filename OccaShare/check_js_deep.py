with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    js = f.read()

print('File size:', len(js), 'chars')
print('Lines:', js.count('\n'))

# Check backtick balance per line
lines = js.split('\n')
for i, line in enumerate(lines):
    count = line.count('')
    if count % 2 != 0:
        print(f'ODD backtick on line {i+1}: {line[:120]}')

# Check FullCalendar init
fc_init = js.find('new FullCalendar.Calendar')
print()
print('FullCalendar init at char:', fc_init)
if fc_init > 0:
    print('Context:', repr(js[fc_init:fc_init+80]))
