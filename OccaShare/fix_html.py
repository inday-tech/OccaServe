import re
with open(r'C:\OccaServe\OccaShare\templates\caterer\packages.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Fix peso (the weird characters we saw)
content = content.replace('Ã¢â€šÂ±', '₱')
content = content.replace('â‚±', '₱')
content = content.replace(',', '₱')

# Remove Advanced Costing Accordion
advanced_costing = re.compile(r'<!-- Advanced Costing Accordion -->.*?<input type="hidden" name="internal_cost_per_pax" id="pkgInternalCostPerPax" value="0">\s*</div>', re.DOTALL)
content = advanced_costing.sub('<input type="hidden" name="internal_cost_per_pax" id="pkgInternalCostPerPax" value="0">', content)

# Fix pricing row layout
pricing_form_row = re.compile(r'<div class="form-row-pro" style="grid-template-columns: 1fr 1fr 1fr;">')
content = pricing_form_row.sub('<div class="form-row-pro" style="display: flex; flex-wrap: wrap; gap: 1rem;">', content)

content = content.replace('<div class="form-group-pro" id="minGuestsGroup">', '<div class="form-group-pro" id="minGuestsGroup" style="flex: 1; min-width: 150px;">')
content = content.replace('<div class="form-group-pro" id="excessPaxGroup" style="display: none;">', '<div class="form-group-pro" id="excessPaxGroup" style="display: none; flex: 1; min-width: 150px;">')
content = content.replace('<div class="form-group-pro">', '<div class="form-group-pro" style="flex: 1; min-width: 150px;">', 2)

# Add is_addon check
content = content.replace('{% for item in services %}', '{% for item in services %}\n                                      {% if not item.is_addon %}')
content = content.replace('{% endfor %}\n                                  {% else %}', '{% endif %}\n                                      {% endfor %}\n                                  {% else %}')

# Update Addons grid to render services that are addons
old_html = '<div class="menu-grid-scroll" id="addonsGrid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 1rem;">'
new_html = '''<div class="menu-grid-scroll" id="addonsGrid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 1rem;">
                                  {% if services %}
                                      {% for item in services %}
                                      {% if item.is_addon %}
                                      <div class="menu-select-card" data-id="{{ item.id }}" data-cost="{{ item.cost_price or 0 }}" onclick="window.toggleLibItemSelectCard(this, '{{ item.id }}')" style="position: relative; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 0.5rem; padding: 1.25rem 0.75rem; border: 1px solid #e2e8f0; border-radius: var(--border-radius, 0.75rem); cursor: pointer; transition: all 0.2s; background: white;">
                                          <div class="select-badge" style="position: absolute; top: 10px; right: 10px; font-size: 1.2rem; color: #cbd5e1; transition: all 0.2s;"><i class="fas fa-check"></i></div>
                                          {% if item.image_url %}
                                              <img src="{{ item.image_url }}" alt="{{ item.name }}" style="width: 64px; height: 64px; border-radius: 50%; object-fit: cover; border: 3px solid #f8fafc; margin-bottom: 0.25rem; box-shadow: 0 4px 8px rgba(0,0,0,0.06);">
                                          {% else %}
                                              <div style="width: 64px; height: 64px; border-radius: 50%; background: #f1f5f9; display: flex; align-items: center; justify-content: center; margin-bottom: 0.25rem;">
                                                  <i class="fas fa-box" style="font-size: 1.5rem; color: #94a3b8;"></i>
                                              </div>
                                          {% endif %}
                                          <div style="flex: 1; width: 100%;">
                                              <h6 style="margin: 0; font-size: 0.85rem; font-weight: 800; color: #1e293b;">{{ item.name }}</h6>
                                              <div style="font-size: 0.65rem; font-weight: 800; color: var(--primary-color); text-transform: uppercase; margin-top: 6px;">{{ item.category or 'Add-on' }}</div>
                                              <div style="font-size: 0.75rem; color: #64748b; font-weight: 700; margin-top: 2px;">₱{{ "{:,.2f}".format(item.cost_price or 0) }} cost</div>
                                          </div>
                                          <input type="checkbox" name="linked_menu_ids" value="{{ item.id }}" style="display:none;">
                                      </div>
                                      {% endif %}
                                      {% endfor %}
                                  {% endif %}'''
content = content.replace(old_html, new_html)

# Update version
content = re.sub(r'packages.js\?v=\d+\.\d+', 'packages.js?v=35.0', content)
content = re.sub(r'packages.css\?v=\d+\.\d+', 'packages.css?v=35.0', content)

with open(r'C:\OccaServe\OccaShare\templates\caterer\packages.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done HTML!')
