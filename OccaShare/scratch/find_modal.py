import codecs

with codecs.open('c:\\OccaServe\\OccaShare\\templates\\customer\\caterer_profile_view.html', 'r', 'utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'document.getElementById("packageModalContent").innerHTML' in line or 'function showPackageModal' in line or 'window.showPackageModal' in line or 'function openPkg' in line:
        print(f'Line {i+1}: {line.strip()}')
