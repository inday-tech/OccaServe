import sys
with open(r'c:\OccaServe\OccaShare\templates\caterer\index.html', 'r', encoding='utf-8') as f:
    text = f.read()

for i, line in enumerate(text.split('\n')):
    if 'stats-grid-dashboard' in line and '<div' in line:
        for j in range(i, i+50):
            sys.stdout.buffer.write(f'{j}: {text.split(chr(10))[j].strip()}\n'.encode('utf-8'))
        break
