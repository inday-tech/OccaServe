with open("app/static/js/caterer/calendar.js", "r", encoding="utf-8") as f:
    js = f.read()

idx = js.find("openSidebarEventModal")
print(js[idx:idx+1000])
