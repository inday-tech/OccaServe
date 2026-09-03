with open("app/static/js/caterer/calendar.js", "r", encoding="utf-8") as f:
    js = f.read()

idx = js.find("openManualBookingModal")
print(js[idx-100:idx+300])
