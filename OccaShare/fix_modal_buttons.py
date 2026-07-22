import re

filepath = r'c:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix Menu button
content = re.sub(
    r"onclick=\"window\.toggleHubItem\('[^']+', '[^']+', '[^']+', '[^']+'\)\"",
    r"onclick=\"window.toggleModalItem(${item.id})\"",
    content
)

# Fix Inventory button
content = re.sub(
    r"onclick=\"window\.toggleInventoryItem\('[^']+', '[^']+', [^,]+, '[^']+', '[^']+', '[^']+', '[^']+'\)\"",
    r"onclick=\"window.toggleInventoryModalItem(${item.id}, '${item.type}')\"",
    content
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated Modal Buttons!")
