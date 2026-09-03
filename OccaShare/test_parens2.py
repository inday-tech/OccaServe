with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    js = f.read()

count = 0
for i, char in enumerate(js):
    if char == '(': count += 1
    elif char == ')': count -= 1
    
    if count < 0:
        print(f"Error at index {i}, near:\n{js[i-50:i+50]}")
        break

print(f"Final count: {count}")
