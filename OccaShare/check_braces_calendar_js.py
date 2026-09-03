with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    text = f.read()

count = 0
for i, char in enumerate(text):
    if char == '{': count += 1
    elif char == '}': count -= 1
    if count < 0:
        print(f"Negative brace count at {i}")

print(f"Final brace count: {count}")
