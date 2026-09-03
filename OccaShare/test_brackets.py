with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    text = f.read()

count_paren = 0
count_brack = 0
for i, char in enumerate(text):
    if char == '(': count_paren += 1
    elif char == ')': count_paren -= 1
    elif char == '[': count_brack += 1
    elif char == ']': count_brack -= 1

print(f"Paren count: {count_paren}, Bracket count: {count_brack}")
