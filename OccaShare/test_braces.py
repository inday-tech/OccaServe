def check_brackets(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    brackets = {'{': '}', '[': ']', '(': ')'}
    stack = []
    
    for i, char in enumerate(content):
        # Ignore comments and strings roughly? This is hard.
        pass

# Let's just find "try {" without a matching "catch" or something.
import re
with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    js = f.read()

# I will find all `try {` and see if they have a matching `catch`.
# Instead of doing that, let me just find `try {` near the end of the file where I suspect the dangling code is.
idx = js.rfind('try {')
if idx != -1:
    print(js[idx-500:idx+2500])

