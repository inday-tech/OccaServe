import os

# Search all templates for manFirstName
for fname in os.listdir('templates/caterer/'):
    fpath = f'templates/caterer/{fname}'
    if os.path.isfile(fpath):
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'manFirstName' in content:
                print(f"Found manFirstName in: {fname}")
