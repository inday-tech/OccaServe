import re
with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r'//.*', '', text)
text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
text = re.sub(r'\"[^\"]*\"', '', text)
text = re.sub(r'\'[^\']*\'', '', text)
text = re.sub(r'\[^\]*\', '', text)
print('Open:', text.count('{'), 'Close:', text.count('}'))
