import re
with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'r', encoding='utf-8') as f:
    content = f.read()

scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
for i, s in enumerate(scripts):
    with open(rf'C:\OccaServe\OccaShare\script_{i}.js', 'w', encoding='utf-8') as f:
        f.write(s)
print(f"Extracted {len(scripts)} scripts")
