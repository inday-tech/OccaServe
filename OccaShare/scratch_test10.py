with open('app/static/js/caterer/bookings.js', 'r', encoding='utf-8') as f:
    js = f.read()

idx = js.find('bookingModalActionsTop')
if idx != -1:
    with open('scratch_test10_output.txt', 'w', encoding='utf-8') as fw:
        fw.write(js[idx+2000:idx+6000])
