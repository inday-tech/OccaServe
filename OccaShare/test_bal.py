import re
with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    text = f.read()

t = re.sub(r'//.*', '', text)
t = re.sub(r'/\*.*?\*/', '', t, flags=re.DOTALL)
t = re.sub(r'\"(?:\\.|[^\\\"])*\"', '\"\"', t)
t = re.sub(r'\'(?:\\.|[^\\\'])*\'', '\'\'', t)
t = re.sub(r'\(?:\\.|[^\\\])*\', '\\', t)

print('Parens:', t.count('(') - t.count(')'))
print('Braces:', t.count('{') - t.count('}'))
print('Brackets:', t.count('[') - t.count(']'))
