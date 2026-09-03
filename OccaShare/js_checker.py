import re

def check_js_syntax(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove single line comments
    content = re.sub(r'//.*', '', content)
    # Remove block comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    # Simple state machine to find unclosed strings
    state = 'code'
    for i, char in enumerate(content):
        if state == 'code':
            if char == '"':
                state = 'dquote'
            elif char == "'":
                state = 'squote'
            elif char == '':
                state = 'bquote'
        elif state == 'dquote':
            if char == '"' and content[i-1] != '\\':
                state = 'code'
            elif char == '\n':
                print(f"Error: unclosed double quote around index {i}")
                print(content[max(0, i-50):i+50])
                return False
        elif state == 'squote':
            if char == "'" and content[i-1] != '\\':
                state = 'code'
            elif char == '\n':
                print(f"Error: unclosed single quote around index {i}")
                print(content[max(0, i-50):i+50])
                return False
        elif state == 'bquote':
            if char == '' and content[i-1] != '\\':
                state = 'code'
                
    if state != 'code':
        print(f"Error: unclosed string at end of file ({state})")
        return False
        
    print("No unclosed strings found!")
    return True

check_js_syntax('app/static/js/caterer/calendar.js')
