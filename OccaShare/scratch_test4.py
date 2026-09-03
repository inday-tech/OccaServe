import glob

for f in glob.glob('templates/caterer/**/*.html', recursive=True):
    try:
        if 'id="bookingModal"' in open(f, encoding='utf-8').read():
            print("Found in:", f)
    except:
        pass
