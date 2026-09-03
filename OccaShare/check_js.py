import re

with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Remove comments
js = re.sub(r'//.*', '', js)
js = re.sub(r'/\*.*?\*/', '', js, flags=re.DOTALL)

# Let's count unclosed { [ (
def check(text):
    b = 0
    p = 0
    s = 0
    in_str = False
    str_char = ''
    escape = False
    
    for i, c in enumerate(text):
        if not in_str:
            if c in ['\"', '\'', '\']:
                in_str = True
                str_char = c
            elif c == '{': b += 1
            elif c == '}': b -= 1
            elif c == '(': p += 1
            elif c == ')': p -= 1
            elif c == '[': s += 1
            elif c == ']': s -= 1
        else:
            if escape:
                escape = False
            elif c == '\\\\':
                escape = True
            elif c == str_char:
                in_str = False
                
    return b, p, s, in_str

b, p, s, in_str = check(js)
print(f'Braces: {b}, Parens: {p}, Brackets: {s}, InString: {in_str}')
