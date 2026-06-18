import re

filepath = 'c:/OccaServe/OccaShare/app/routers/caterer_dashboard.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove specific lines that cause errors
content = re.sub(r'^\s*archived_ingredients\s*=\s*\[ing for ing in profile\.ingredients if ing\.is_archived\]\n?', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*"archived_ingredients":\s*archived_ingredients,\n?', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*all_ingredients\s*=\s*\[i for i in user\.caterer_profile\.ingredients if not i\.is_archived\]\n?', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*"ingredients":\s*all_ingredients,\n?', '', content, flags=re.MULTILINE)

# Optional: Disable or blank out ingredient endpoints by changing their paths or logic if needed.
# For now, let's just write back the fixed content to resolve the immediate AttributeError.
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Cleaned up ingredients references in caterer_dashboard.py')
