import glob

for f in glob.glob('templates/caterer/**/*.html', recursive=True):
    try:
        if 'id="eventModal"' in open(f, encoding='utf-8').read():
            print("Found in:", f)
    except Exception as e:
        pass
