import codecs

with codecs.open('c:\\OccaServe\\OccaShare\\templates\\caterer\\packages.html', 'r', 'utf-8') as f:
    for i, line in enumerate(f):
        if 'name="image"' in line or 'type="file"' in line:
            print(f'Line {i+1}: {line.strip()}')
