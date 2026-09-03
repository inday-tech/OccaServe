import re

with open('templates/caterer/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('<span class="kpi-value">?{{ "{:,.2f}".format(outstanding_balance) }}</span>', '<span class="kpi-value">?{{ "{:,.2f}".format(outstanding_balance) }}</span>')

with open('templates/caterer/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed Peso sign")
