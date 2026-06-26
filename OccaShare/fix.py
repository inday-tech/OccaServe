import re
with open(r'C:\OccaServe\OccaShare\templates\caterer\packages.html', 'r', encoding='utf-8') as f:
    content = f.read()

advanced_costing = re.compile(r'<!-- Advanced Costing Accordion -->.*?<input type="hidden" name="internal_cost_per_pax" id="pkgInternalCostPerPax" value="0">\s*</div>', re.DOTALL)
content = advanced_costing.sub('<input type="hidden" name="internal_cost_per_pax" id="pkgInternalCostPerPax" value="0">', content)

pricing_form_row = re.compile(r'<div class="form-row-pro" style="grid-template-columns: 1fr 1fr 1fr;">')
content = pricing_form_row.sub('<div class="form-row-pro" style="display: flex; flex-wrap: wrap; gap: 1rem;">', content)

# Change individual items in that row to flex: 1
content = content.replace('<div class="form-group-pro" id="minGuestsGroup">', '<div class="form-group-pro" id="minGuestsGroup" style="flex: 1; min-width: 150px;">')
content = content.replace('<div class="form-group-pro" id="excessPaxGroup" style="display: none;">', '<div class="form-group-pro" id="excessPaxGroup" style="display: none; flex: 1; min-width: 150px;">')
content = content.replace('<div class="form-group-pro">', '<div class="form-group-pro" style="flex: 1; min-width: 150px;">', 2) # Just apply to the first couple

with open(r'C:\OccaServe\OccaShare\templates\caterer\packages.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
