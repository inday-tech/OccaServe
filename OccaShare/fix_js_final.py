import re
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
                const noAddons = addonsGrid.querySelector('.no-addons-placeholder');
                if (noAddons) noAddons.remove();
                
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
