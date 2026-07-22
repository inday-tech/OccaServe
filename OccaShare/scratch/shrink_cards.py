import os
import re

html_path = r'c:\OccaServe\OccaShare\templates\caterer\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace css padding to make it smaller
content = re.sub(r'\.card \{.*?padding: 20px;', '.card {\n        background: white;\n        border-radius: 12px;\n        box-shadow: var(--card-shadow);\n        padding: 15px;', content, flags=re.DOTALL)
content = re.sub(r'\.card-title \{.*?font-size: 1rem;.*?margin-bottom: 15px;', '.card-title {\n        font-size: 0.9rem;\n        font-weight: 600;\n        color: #1e293b;\n        margin-bottom: 10px;', content, flags=re.DOTALL)

content = re.sub(r'\.stat-card \{.*?padding: 20px;.*?gap: 8px;', '.stat-card {\n        background: white; border-radius: 12px; padding: 12px 15px;\n        border: 1px solid #e2e8f0; border-left: 4px solid var(--primary-color);\n        display: flex; flex-direction: column; gap: 4px;', content, flags=re.DOTALL)
content = re.sub(r'\.stat-value \{ font-size: 1\.8rem;', '.stat-value { font-size: 1.4rem;', content)

content = re.sub(r'\.action-item \{.*?padding: 12px 15px;', '.action-item {\n        display: flex; justify-content: space-between; align-items: center;\n        padding: 8px 12px;', content, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated CSS padding in index.html to make cards smaller')
