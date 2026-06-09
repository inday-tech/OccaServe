def is_keyboard_walk(text: str) -> bool:
    walks = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm', '1234567890', 'poiuytrewq', 'lkjhgfdsa', 'mnbvcxz']
    s = text.lower()
    if len(s) < 3:
        return False
    for walk in walks:
        for i in range(len(walk) - 2):
            sub = walk[i:i+3]
            if sub in s:
                print(f"Matched keyboard walk substring: {sub} (from walk: {walk})")
                return True
    return False

name = "GAB HUBS IMPORTEDS AND RESTORANTE"
clean_name = name.replace(" ", "")
print(f"clean_name = {clean_name}")
print(f"is_keyboard_walk = {is_keyboard_walk(clean_name)}")
