import re

file_path = r"c:\OccaServe\OccaShare\app\static\js\caterer\packages.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_logic = """                     onclick="window.toggleLibItemSelectCard(this, ${item.id})\""""
new_logic = """                     onclick="window.toggleLibItemSelectCard(this, '${item.id}')\""""

if old_logic in content:
    content = content.replace(old_logic, new_logic)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Logic replaced successfully.")
else:
    print("Could not find the old logic.")
