import re

f = r'c:\OccaServe\OccaShare\app\static\js\caterer\packages.js'
with open(f, 'r', encoding='utf-8') as file:
    content = file.read()

old_proceed = """window.proceedToAddonConfig = function() {
    const selected = document.querySelectorAll('#addonPickerGrid .addon-picker-card.selected');
    if (selected.length === 0) {
        alert("Please select at least one item.");
        return;
    }
    
    const container = document.getElementById('addonConfigFormsContainer');
    container.innerHTML = '';
    
    selected.forEach(card => {
        const id = card.dataset.id;
        const name = card.dataset.name;
        const price = card.dataset.price;
        
        // Check if already configured to avoid duplicates
        const existing = configuredAddons[currentAddonType].find(a => String(a.id) === String(id));
        if (existing) {
            container.innerHTML += `<div style="padding: 1rem; background: #fffbeb; border: 1px solid #fde68a; border-radius: 0.5rem; margin-bottom: 1rem; font-size: 0.85rem; color: #92400e;"><strong>${name}</strong> is already configured as an add-on.</div>`;
            return;
        }

        container.innerHTML += `
            <div class="addon-config-item" data-id="${id}" data-name="${name}" style="background: white; border: 1px solid #e2e8f0; border-radius: 0.5rem; padding: 1.25rem; margin-bottom: 1rem;">
                <h5 style="margin: 0 0 1rem 0; font-size: 0.95rem; font-weight: 800; color: #1e293b; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.5rem;">${name}</h5>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div class="form-group-pro">
                        <label>Additional Price (₱) *</label>
                        <input type="number" class="control-pro cfg-price" value="${price}" min="0" required>
                    </div>
                    <div class="form-group-pro">
                        <label>Max Quantity (Optional)</label>
                        <input type="number" class="control-pro cfg-max" placeholder="No limit" min="1">
                    </div>
                </div>
            </div>
        `;
    });
    
    safeCloseModal('addonPickerModal');
    if (container.innerHTML.trim() !== '') {
        safeOpenModal('addonConfigModal');
    }
};

window.saveAddonConfig = function() {
    const items = document.querySelectorAll('.addon-config-item');
    let hasError = false;
    
    items.forEach(el => {
        const id = el.dataset.id;
        const name = el.dataset.name;
        const priceInput = el.querySelector('.cfg-price');
        const maxInput = el.querySelector('.cfg-max');
        
        const price = parseFloat(priceInput.value);
        if (isNaN(price) || price < 0) {
            priceInput.style.borderColor = 'red';
            hasError = true;
            return;
        }
        
        const max = parseInt(maxInput.value);
        
        configuredAddons[currentAddonType].push({
            id: id,
            name: name,
            price: price,
            max_quantity: isNaN(max) ? null : max,
            is_enabled: true
        });
    });
    
    if (hasError) return;
    
    safeCloseModal('addonConfigModal');
    renderAddonLists();
};"""

new_proceed = """
window.proceedToAddonConfig = function() {
    const selected = document.querySelectorAll('#addonPickerGrid .addon-picker-card.selected');
    if (selected.length === 0) {
        alert("Please select at least one item.");
        return;
    }
    
    const container = document.getElementById('addonConfigFormsContainer');
    container.innerHTML = '';
    
    selected.forEach(card => {
        const id = card.dataset.id;
        const name = card.dataset.name;
        const basePrice = card.dataset.price;
        
        const existing = configuredAddons[currentAddonType].find(a => String(a.id) === String(id));
        if (existing) {
            container.innerHTML += `<div style="padding: 1rem; background: #fffbeb; border: 1px solid #fde68a; border-radius: 0.5rem; margin-bottom: 1rem; font-size: 0.85rem; color: #92400e;"><strong>${name}</strong> is already configured as an add-on.</div>`;
            return;
        }

        let fieldsHtml = '';
        
        if (currentAddonType === 'menu') {
            fieldsHtml = `
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div class="form-group-pro">
                        <label>Additional Price (₱) *</label>
                        <input type="number" class="control-pro cfg-price" value="${basePrice}" min="0" required>
                    </div>
                    <div class="form-group-pro">
                        <label>Selection Type</label>
                        <select class="control-pro cfg-selection-type" onchange="window.toggleAddonQtyFields(this)">
                            <option value="single">Single Selection (No Quantity)</option>
                            <option value="multiple">Multiple Selection</option>
                        </select>
                    </div>
                </div>
                <div class="addon-qty-fields" style="display: none; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem;">
                    <div class="form-group-pro">
                        <label>Minimum Quantity</label>
                        <input type="number" class="control-pro cfg-min" value="1" min="1">
                    </div>
                    <div class="form-group-pro">
                        <label>Maximum Quantity (Optional)</label>
                        <input type="number" class="control-pro cfg-max" placeholder="No limit" min="1">
                    </div>
                </div>
            `;
        } else if (currentAddonType === 'equipment') {
            fieldsHtml = `
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div class="form-group-pro">
                        <label>Additional Price (₱) *</label>
                        <input type="number" class="control-pro cfg-price" value="${basePrice}" min="0" required>
                    </div>
                    <div class="form-group-pro">
                        <label>Rental Unit</label>
                        <input type="text" class="control-pro" value="Per Piece" disabled style="background:#f1f5f9;">
                        <input type="hidden" class="cfg-selection-type" value="multiple">
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem;">
                    <div class="form-group-pro">
                        <label>Minimum Quantity</label>
                        <input type="number" class="control-pro cfg-min" value="1" min="1">
                    </div>
                    <div class="form-group-pro">
                        <label>Maximum Quantity *</label>
                        <input type="number" class="control-pro cfg-max" placeholder="Required based on inventory" min="1" required>
                    </div>
                </div>
            `;
        } else if (currentAddonType === 'service') {
            fieldsHtml = `
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div class="form-group-pro">
                        <label>Additional Price (₱) *</label>
                        <input type="number" class="control-pro cfg-price" value="${basePrice}" min="0" required>
                    </div>
                    <div class="form-group-pro">
                        <label>Service Model</label>
                        <select class="control-pro cfg-selection-type" onchange="window.toggleAddonQtyFields(this)">
                            <option value="single">Single Service (No Quantity)</option>
                            <option value="manpower">Manpower Service (Requires Quantity)</option>
                        </select>
                    </div>
                </div>
                <div class="addon-qty-fields" style="display: none; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem;">
                    <div class="form-group-pro">
                        <label>Minimum Staff</label>
                        <input type="number" class="control-pro cfg-min" value="1" min="1">
                    </div>
                    <div class="form-group-pro">
                        <label>Maximum Staff *</label>
                        <input type="number" class="control-pro cfg-max" placeholder="Required" min="1">
                    </div>
                </div>
            `;
        }

        container.innerHTML += `
            <div class="addon-config-item" data-id="${id}" data-name="${name}" style="background: white; border: 1px solid #e2e8f0; border-radius: 0.5rem; padding: 1.25rem; margin-bottom: 1rem;">
                <h5 style="margin: 0 0 1rem 0; font-size: 0.95rem; font-weight: 800; color: #1e293b; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.5rem;">${name}</h5>
                ${fieldsHtml}
            </div>
        `;
    });
    
    safeCloseModal('addonPickerModal');
    if (container.innerHTML.trim() !== '') {
        safeOpenModal('addonConfigModal');
    }
};

window.toggleAddonQtyFields = function(selectEl) {
    const container = selectEl.closest('.addon-config-item');
    const qtyFields = container.querySelector('.addon-qty-fields');
    if (selectEl.value === 'multiple' || selectEl.value === 'manpower') {
        qtyFields.style.display = 'grid';
    } else {
        qtyFields.style.display = 'none';
    }
};

window.saveAddonConfig = function() {
    const items = document.querySelectorAll('.addon-config-item');
    let hasError = false;
    
    items.forEach(el => {
        const id = el.dataset.id;
        const name = el.dataset.name;
        
        const priceInput = el.querySelector('.cfg-price');
        const price = parseFloat(priceInput.value);
        if (isNaN(price) || price < 0) {
            priceInput.style.borderColor = 'red';
            hasError = true;
            return;
        } else {
            priceInput.style.borderColor = '#e2e8f0';
        }

        let selType = 'single';
        const selInput = el.querySelector('.cfg-selection-type');
        if (selInput) selType = selInput.value;

        let min = null;
        let max = null;
        
        if (selType === 'multiple' || selType === 'manpower' || currentAddonType === 'equipment') {
            const minInput = el.querySelector('.cfg-min');
            const maxInput = el.querySelector('.cfg-max');
            
            min = parseInt(minInput.value);
            if (isNaN(min) || min < 1) min = 1;

            max = parseInt(maxInput.value);
            
            if (currentAddonType === 'equipment' && isNaN(max)) {
                maxInput.style.borderColor = 'red';
                hasError = true;
                return;
            } else if (selType === 'manpower' && isNaN(max)) {
                maxInput.style.borderColor = 'red';
                hasError = true;
                return;
            } else {
                if (maxInput) maxInput.style.borderColor = '#e2e8f0';
            }

            if (!isNaN(max) && max < min) {
                if(maxInput) maxInput.style.borderColor = 'red';
                alert(`Maximum limit cannot be less than minimum for ${name}.`);
                hasError = true;
                return;
            }
        }

        configuredAddons[currentAddonType].push({
            id: id,
            name: name,
            price: price,
            selection_type: selType,
            min_quantity: min,
            max_quantity: isNaN(max) ? null : max,
            is_enabled: true
        });
    });
    
    if (hasError) return;
    
    safeCloseModal('addonConfigModal');
    renderAddonLists();
};
"""

content = content.replace(old_proceed, new_proceed)

# Also update renderAddonRow to display the new properties nicely
old_row = """function renderAddonRow(addon, type, index) {
    return `
        <div style="display: flex; justify-content: space-between; align-items: center; background: white; border: 1px solid #e2e8f0; border-radius: 0.5rem; padding: 0.75rem 1rem;">
            <div>
                <div style="font-weight: 800; color: #1e293b; font-size: 0.9rem;">
                    <i class="fas fa-check-circle text-green-500 mr-1" style="font-size:0.8rem;"></i> ${addon.name}
                </div>
                <div style="font-size: 0.75rem; color: #64748b; font-weight: 600; margin-top: 4px;">
                    +₱${addon.price.toLocaleString()} ${addon.max_quantity ? `| Max: ${addon.max_quantity}` : ''}
                </div>
            </div>
            <div>
                <button type="button" onclick="window.removeAddon('${type}', ${index})" style="background: none; border: none; color: #ef4444; font-size: 1rem; cursor: pointer; padding: 0.5rem;"><i class="fas fa-trash-alt"></i></button>
            </div>
        </div>
    `;
}"""

new_row = """function renderAddonRow(addon, type, index) {
    let details = `+₱${addon.price.toLocaleString()}`;
    
    if (addon.selection_type === 'multiple' || type === 'equipment') {
        details += ` | Qty: ${addon.min_quantity} to ${addon.max_quantity || 'unlimited'}`;
    } else if (addon.selection_type === 'manpower') {
        details += ` | Staff: ${addon.min_quantity} to ${addon.max_quantity}`;
    } else {
        details += ` | Single Selection`;
    }

    return `
        <div style="display: flex; justify-content: space-between; align-items: center; background: white; border: 1px solid #e2e8f0; border-radius: 0.5rem; padding: 0.75rem 1rem;">
            <div>
                <div style="font-weight: 800; color: #1e293b; font-size: 0.9rem;">
                    <i class="fas fa-check-circle text-green-500 mr-1" style="font-size:0.8rem;"></i> ${addon.name}
                </div>
                <div style="font-size: 0.75rem; color: #64748b; font-weight: 600; margin-top: 4px;">
                    ${details}
                </div>
            </div>
            <div>
                <button type="button" onclick="window.removeAddon('${type}', ${index})" style="background: none; border: none; color: #ef4444; font-size: 1rem; cursor: pointer; padding: 0.5rem;"><i class="fas fa-trash-alt"></i></button>
            </div>
        </div>
    `;
}"""

content = content.replace(old_row, new_row)

with open(f, 'w', encoding='utf-8') as out:
    out.write(content)
print('Updated packages.js')
