import re

filepath = r'c:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the toggleHubItem call
content = re.sub(
    r'onclick="window\.toggleHubItem\([^)]+\)"',
    r'onclick="window.toggleModalItem(${item.id})"',
    content
)

# Replace the toggleInventoryItem call inside the modal JS
content = re.sub(
    r'onclick="window\.toggleInventoryItem\([^)]+\)"',
    r'onclick="window.toggleInventoryModalItem(${item.id}, \'${item.type}\')"!',
    content
)
# Wait, I shouldn't just run blind regex. Let me do a specific replacement.
