import codecs

with codecs.open('c:\\OccaServe\\OccaShare\\templates\\customer\\caterer_profile_view.html', 'r', 'utf-8') as f:
    lines = f.readlines()

in_func = False
for i, line in enumerate(lines):
    if 'window.openPackageModal' in line:
        in_func = True
    if in_func:
        print(f'Line {i+1}: {line.rstrip()}')
        if '}' == line.strip() and i > 1200:
            break
