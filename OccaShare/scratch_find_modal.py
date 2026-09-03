import glob

for filename in glob.glob('templates/caterer/**/*.html', recursive=True):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            if 'id="bookingModal"' in f.read():
                print(filename)
    except:
        pass
