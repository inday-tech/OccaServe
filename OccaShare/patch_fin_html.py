import re

path = 'templates/caterer/financials.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """                <span class="kpi-value" style="color: white; font-size: 1.5rem; display: flex; align-items: center; gap: 0.5rem;"><i class="fas fa-lock" style="font-size: 1rem; opacity: 0.7;"></i> Auto-calculated</span>
                <span class="trend-badge" style="color: rgba(255,255,255,0.9); background: transparent; padding: 0; font-size: 0.65rem; font-weight: 500; margin-top: 6px;">Total Rev - (Event Costs + Overhead)</span>"""
replacement = """                <span class="kpi-value" style="color: white; font-size: 1.5rem; display: flex; align-items: center; gap: 0.5rem;">₱{{ "{:,.2f}".format(net_profit if net_profit is defined else 0) }}</span>
                <span class="trend-badge" style="color: rgba(255,255,255,0.9); background: transparent; padding: 0; font-size: 0.65rem; font-weight: 500; margin-top: 6px;">Net Rev (after fee) - Total Costs</span>"""
content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Frontend financials patched!")
