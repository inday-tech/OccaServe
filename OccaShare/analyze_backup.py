with open('templates/caterer/calendar_backup.html', 'r', encoding='utf-8') as f:
    content = f.read()
    
import re
blocks = re.findall(r'\{% block \w+ %\}', content)
endblocks = len(re.findall(r'\{% endblock %\}', content))
print(f"Backup - Blocks: {blocks}")
print(f"Backup - Endblocks: {endblocks}")
print(f"Backup - Total chars: {len(content)}")
print(f"Backup line 1-10:")
for i, line in enumerate(content.split('\n')[:10]):
    print(f"  {i+1}: {line[:100]}")
