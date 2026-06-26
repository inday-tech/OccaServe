import re
import codecs

with open(r'C:\OccaServe\OccaShare\templates\caterer\packages.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Fix peso (the weird characters we saw)
content = content.replace('Ã¢â€šÂ±', '₱')
content = content.replace('â‚±', '₱')

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

with open(r'C:\OccaServe\OccaShare\app\static\js\caterer\packages.js', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Fix grouping in menu
old_menu_render = '''        if (foodLibrary.length === 0) {
            container.innerHTML = '<div class="text-center py-5 text-slate-400 text-xs">Your menu library is currently empty.</div>';
        } else {
            container.innerHTML = foodLibrary.map(item => {
                const isSelected = linkedIds.includes(item.id);
                return `
                    <div class="menu-select-card ${isSelected ? 'selected' : ''}" 
                         data-id="${item.id}" 
                         data-cost="${item.cost_price || 0}"
                         onclick="window.toggleLibItemSelectCard(this, '${item.id}')">
                        <div class="select-badge"><i class="fas fa-check"></i></div>
                        ${item.image_url 
                            ? `<img src="${item.image_url}" alt="${item.name}">`
                            : `<div class="no-dish-image">
                                 <i class="fas fa-caret-down"></i>
                                 <span>NO DISH IMAGE</span>
                               </div>`
                        }
                        <h6>${item.name}</h6>
                        <span class="category-tag">${item.category}</span>
                        <div class="cost-tag">₱${(item.cost_price || 0).toFixed(2)} cost</div>
                        <input type="checkbox" name="linked_menu_ids" value="${item.id}" ${isSelected ? 'checked' : ''} style="display:none;">
                    </div>
                `;
            }).join('');
        }'''

new_menu_render = '''        if (foodLibrary.length === 0) {
            container.innerHTML = '<div class="text-center py-5 text-slate-400 text-xs">Your menu library is currently empty.</div>';
        } else {
            // Group by category
            const grouped = {};
            foodLibrary.forEach(item => {
                const cat = item.category || 'Other';
                if (!grouped[cat]) grouped[cat] = [];
                grouped[cat].push(item);
            });
            
            let html = '';
            for (const [cat, items] of Object.entries(grouped)) {
                html += `
                    <div style="grid-column: 1 / -1; margin-top: 1rem; border-bottom: 2px solid #f1f5f9; padding-bottom: 0.5rem;">
                        <h5 style="font-size: 0.9rem; font-weight: 800; color: #1e293b; margin: 0; text-transform: uppercase;">${cat}</h5>
                    </div>
                `;
                html += items.map(item => {
                    const isSelected = linkedIds.includes(item.id);
                    return `
                        <div class="menu-select-card ${isSelected ? 'selected' : ''}" 
                             data-id="${item.id}" 
                             data-cost="${item.cost_price || 0}"
                             onclick="window.toggleLibItemSelectCard(this, '${item.id}')">
                            <div class="select-badge"><i class="fas fa-check"></i></div>
                            ${item.image_url 
                                ? `<img src="${item.image_url}" alt="${item.name}">`
                                : `<div class="no-dish-image">
                                     <i class="fas fa-caret-down"></i>
                                     <span>NO DISH IMAGE</span>
                                   </div>`
                            }
                            <h6>${item.name}</h6>
                            <span class="category-tag">${item.category}</span>
                            <div class="cost-tag">₱${(item.price || item.cost_price || 0).toFixed(2)} price</div>
                            <input type="checkbox" name="linked_menu_ids" value="${item.id}" ${isSelected ? 'checked' : ''} style="display:none;">
                        </div>
                    `;
                }).join('');
            }
            container.innerHTML = html;
        }'''

content = content.replace(old_menu_render, new_menu_render)

old_addons_render = '''                    <div class="menu-select-card ${isSelected ? 'selected' : ''}" 
                         data-id="${item.id}" 
                         data-cost="${item.cost_price || 0}"
                         onclick="window.toggleLibItemSelectCard(this, '${item.id}')">
                        <div class="select-badge"><i class="fas fa-check"></i></div>
                        ${item.image_url 
                            ? `<img src="${item.image_url}" alt="${item.name}">`
                            : `<div class="no-dish-image">
                                 <i class="fas fa-box"></i>
                                 <span>NO IMAGE</span>
                               </div>`
                        }
                        <h6>${item.name}</h6>
                        <span class="category-tag">${item.category || 'Add-on'}</span>
                        <div class="cost-tag">₱${(item.cost_price || 0).toFixed(2)} cost</div>
                        <input type="checkbox" name="linked_menu_ids" value="${item.id}" ${isSelected ? 'checked' : ''} style="display:none;">
                    </div>'''

new_addons_render = '''                    <div class="menu-select-card ${isSelected ? 'selected' : ''}" 
                         data-id="${item.id}" 
                         data-cost="${item.cost_price || 0}"
                         onclick="window.toggleLibItemSelectCard(this, '${item.id}')">
                        <div class="select-badge"><i class="fas fa-check"></i></div>
                        ${item.image_url 
                            ? `<img src="${item.image_url}" alt="${item.name}">`
                            : `<div class="no-dish-image">
                                 <i class="fas fa-box"></i>
                                 <span>NO IMAGE</span>
                               </div>`
                        }
                        <h6>${item.name}</h6>
                        <span class="category-tag">${item.category || 'Add-on'}</span>
                        <div class="cost-tag">₱${(item.price || item.cost_price || 0).toFixed(2)} price</div>
                        <input type="checkbox" name="linked_menu_ids" value="${item.id}" ${isSelected ? 'checked' : ''} style="display:none;">
                    </div>'''

content = content.replace(old_addons_render, new_addons_render)

old_js_append = '''        // Populate Add-ons Tab
        const addonsGrid = document.getElementById('addonsGrid');
        if (addonsGrid) {
            const addonsLibrary = library.filter(item => item.is_addon === true);
            if (addonsLibrary.length === 0) {
                addonsGrid.innerHTML = '<div class="text-center py-5 text-slate-400 text-xs" style="grid-column: 1 / -1;">No add-ons available in your inventory.</div>';
            } else {
                addonsGrid.innerHTML = addonsLibrary.map(item => {'''

new_js_append = '''        // Populate Add-ons Tab
        const addonsGrid = document.getElementById('addonsGrid');
        if (addonsGrid) {
            const addonsLibrary = library.filter(item => item.is_addon === true);
            if (addonsLibrary.length > 0) {
                // Remove the "no add-ons" placeholder if it exists (but keep server-rendered items)
                const noAddons = addonsGrid.querySelector('.text-center');
                if (noAddons && noAddons.innerText.includes('No add-ons available')) noAddons.remove();
                
                addonsGrid.innerHTML += addonsLibrary.map(item => {'''

content = content.replace(old_js_append, new_js_append)

old_calc = '''        let ingCostPerPax = 0;
        for (const [cat, costs] of Object.entries(selectedDishesByCategory)) {
            costs.sort((a, b) => b - a);
            const limit = rules[cat] ? parseInt(rules[cat]) : costs.length;
            const effectiveLimit = Math.min(limit, costs.length);
            for (let i = 0; i < effectiveLimit; i++) {
                ingCostPerPax += costs[i];
            }
        }

        const ingDisplay = document.getElementById('pkgIngredientCostDisplay');
        if (ingDisplay) {
            ingDisplay.innerText = '₱' + ingCostPerPax.toFixed(2) + ' / pax';
            ingDisplay.dataset.cost = ingCostPerPax;
        }
    }

    const ingDisplay = document.getElementById('pkgIngredientCostDisplay');
    const ingCostPerPax = parseFloat(ingDisplay?.dataset?.cost) || 0;'''

new_calc = '''        let ingCostPerPaxVar = 0;
        for (const [cat, costs] of Object.entries(selectedDishesByCategory)) {
            costs.sort((a, b) => b - a);
            const limit = rules[cat] ? parseInt(rules[cat]) : costs.length;
            const effectiveLimit = Math.min(limit, costs.length);
            for (let i = 0; i < effectiveLimit; i++) {
                ingCostPerPaxVar += costs[i];
            }
        }
        
        window._tempIngCostPerPax = ingCostPerPaxVar;
    }

    const ingCostPerPax = window._tempIngCostPerPax || 0;'''

content = content.replace(old_calc, new_calc)

# Fix pesos ONLY the known corruptions:
content = content.replace('Ã¢â€šÂ±', '₱')
content = content.replace('â‚±', '₱')

# And applying the rPrice fix
old_rprice = '''    if (rName && form) {
        rName.innerText = form.name.value || 'Untitled Package';
        rType.innerText = form.service_type.value || 'General';
        
        const mode = form.pricing_mode ? form.pricing_mode.value : 'per_pax';
        rMode.innerText = mode === 'fixed' ? 'Fixed (Event Based)' : 'Per Pax (Guest Based)';
        
        rPrice.innerText = '₱' + manualPrice.toLocaleString(undefined, { minimumFractionDigits: 2 }) + (mode === 'fixed' ? ' total' : ' / pax');
        rROI.innerText = margin.toFixed(1) + '%';
        rROI.style.color = margin < 0 ? '#ef4444' : '#1e293b';

        const resType = form.reservation_fee_type ? form.reservation_fee_type.value : 'fixed';
        const resVal = form.reservation_fee_value ? parseFloat(form.reservation_fee_value.value) || 0 : 0;
        rRes.innerText = resType === 'percentage' ? resVal + '%' : '₱' + resVal.toLocaleString();
        
        const rExcessContainer = document.getElementById('reviewExcessPaxContainer');
        const rExcess = document.getElementById('reviewExcessPax');
        if (rExcessContainer && rExcess) {
            if (mode === 'fixed') {
                const excessVal = parseFloat(form.additional_guest_price?.value) || 0;
                rExcess.innerText = '₱' + excessVal.toLocaleString(undefined, { minimumFractionDigits: 2 });
                rExcessContainer.style.display = 'block';
            } else {
                rExcessContainer.style.display = 'none';
            }
        }
        
        rDishes.innerText = document.querySelectorAll('#tab-menu .menu-select-card.selected').length;
        rServices.innerText = document.querySelectorAll('#tab-perks .menu-select-card.selected').length;'''

new_rprice = '''    if (rName && form) {
        rName.innerText = form.name.value || 'Untitled Package';
        if (rType) rType.innerText = form.service_type.value || 'General';
        
        const mode = form.pricing_mode ? form.pricing_mode.value : 'per_pax';
        if (rMode) rMode.innerText = mode === 'fixed' ? 'Fixed (Event Based)' : 'Per Pax (Guest Based)';
        
        if (rPrice) rPrice.innerText = '₱' + manualPrice.toLocaleString(undefined, { minimumFractionDigits: 2 }) + (mode === 'fixed' ? ' total' : ' / pax');
        if (rROI) {
            rROI.innerText = margin.toFixed(1) + '%';
            rROI.style.color = margin < 0 ? '#ef4444' : '#1e293b';
        }

        const resType = form.reservation_fee_type ? form.reservation_fee_type.value : 'fixed';
        const resVal = form.reservation_fee_value ? parseFloat(form.reservation_fee_value.value) || 0 : 0;
        if (rRes) rRes.innerText = resType === 'percentage' ? resVal + '%' : '₱' + resVal.toLocaleString();
        
        const rExcessContainer = document.getElementById('reviewExcessPaxContainer');
        const rExcess = document.getElementById('reviewExcessPax');
        if (rExcessContainer && rExcess) {
            if (mode === 'fixed') {
                const excessVal = parseFloat(form.additional_guest_price?.value) || 0;
                rExcess.innerText = '₱' + excessVal.toLocaleString(undefined, { minimumFractionDigits: 2 });
                rExcessContainer.style.display = 'block';
            } else {
                rExcessContainer.style.display = 'none';
            }
        }
        
        if (rDishes) rDishes.innerText = document.querySelectorAll('#tab-menu .menu-select-card.selected').length;
        if (rServices) rServices.innerText = document.querySelectorAll('#tab-perks .menu-select-card.selected').length;'''

content = content.replace(old_rprice, new_rprice)

with open(r'C:\OccaServe\OccaShare\app\static\js\caterer\packages.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done JS!')
