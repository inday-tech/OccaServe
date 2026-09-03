with open('app/static/js/caterer/bookings.js', 'r', encoding='utf-8') as f:
    js = f.read()

idx = js.find('modalHistoryTimeline')
if idx != -1:
    with open('scratch_test8_output.txt', 'w', encoding='utf-8') as fw:
        fw.write(js[idx-1000:idx+2000])
