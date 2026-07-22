import codecs
with codecs.open('c:\\OccaServe\\OccaShare\\templates\\customer\\caterer_profile_view.html', 'r', 'utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'id="pkg-modal"' in line:
        for j in range(max(0, i-5), min(len(lines), i+15)):
            print(f'{j+1}: {lines[j].rstrip()}')
        break
