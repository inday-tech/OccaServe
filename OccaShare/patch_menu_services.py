import re

path = 'templates/caterer/menu.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """                                <option value="Rentals">Rentals</option>
                                <option value="Equipment">Equipment</option>
                                <option value="Other">Other</option>"""
replacement = """                                <option value="Rentals">Rentals</option>
                                <option value="Equipment">Equipment</option>
                                <option value="Services">Services</option>
                                <option value="Other">Other</option>"""
content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Added Services to Menu Categories")
