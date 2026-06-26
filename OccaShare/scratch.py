import re

with open(r'c:\OccaServe\OccaShare\templates\caterer\packages.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
lines = text.split('\n')
stack = []

for i, line in enumerate(lines):
    for m in re.finditer(r'<div([^>]*)>|</div\s*>|<form([^>]*)>|</form\s*>', line):
        tag = m.group()
        if tag.startswith('</'):
            if stack:
                stack.pop()
            else:
                print(f'Mismatched closing tag at line {i+1}: {tag}')
        else:
            class_match = re.search(r'class=[\'\"]([^\'\"]*)[\'\"]', tag)
            id_match = re.search(r'id=[\'\"]([^\'\"]*)[\'\"]', tag)
            desc = tag.split()[0][1:]
            if id_match: desc += f'#{id_match.group(1)}'
            if class_match: desc += f'.{class_match.group(1).split()[0]}'
            stack.append((i+1, desc))

    if 'id=\"pkgWizardFooter\"' in line:
        print(f'Stack at pkgWizardFooter (line {i+1}):')
        for s in stack:
            print(f'  Line {s[0]}: {s[1]}')
