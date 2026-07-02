import re

file_path = r"c:\OccaServe\OccaShare\app\static\js\caterer\packages.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# We will append the new addon logic to the end of packages.js
# And we need to remove the old Addon rendering in loadPkgMenuLibrary

new_addon_logic = """
// ==========================================
// OPTIONAL ADD-ONS WIZARD LOGIC (v17)
// ==========================================
let currentAddonType = null;
let configuredAddons = { menu: [], service: [], equipment: [] };
let globalPkgLibrary = [];

// Overwrite loadPkgMenuLibrary to store library globally and fetch existing addons
const originalLoad = window.loadPkgMenuLibrary;
window.loadPkgMenuLibrary = async function() {
    const pkgId = getActivePackageId();

    try {
        const [libRes, linkedRes, addonsRes] = await Promise.all([
            fetch('/caterer/api/menu'),
            pkgId ? fetch(`/caterer/packages/${pkgId}/menu`) : Promise.resolve({ json: () => [] }),
            pkgId ? fetch(`/caterer/packages/${pkgId}/addons`) : Promise.resolve({ json: () => ({ menu: [], service: [], equipment: [] }) })
        ]);

        globalPkgLibrary = await libRes.json();
        const linkedItems = pkgId ? await linkedRes.json() : [];
        const linkedIds = Array.isArray(linkedItems) ? linkedItems.map(i => i.id) : [];
        
        configuredAddons = pkgId ? await addonsRes.json() : { menu: [], service: [], equipment: [] };

        const menuContainer = document.getElementById('pkgMenuLibraryContainer');
        const eqContainer = document.getElementById('inc-equipment-grid');
        const svcContainer = document.getElementById('inc-services-grid');

        if (menuContainer) menuContainer.innerHTML = '';
        if (eqContainer) eqContainer.innerHTML = '';
        if (svcContainer) svcContainer.innerHTML = '';

        const foodCats = [];
        const eqCats = [];
        const svcCats = [];

        globalPkgLibrary.forEach(item => {
            if (String(item.id).startsWith('eq_')) {
                eqCats.push(item);
            } else if (String(item.id).startsWith('svc_')) {
                svcCats.push(item);
            } else {
                foodCats.push(item);
            }
        });

        const renderCard = (item) => {
            const isSelected = linkedIds.includes(item.id);
            return `
                <div class="menu-select-card ${isSelected ? 'selected' : ''}" 
                     data-id="${item.id}"
                     data-category="${item.category}"
                     onclick="window.toggleLibItemSelectCard(this, '${item.id}')"
                     style="position: relative; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 0.5rem; padding: 1.25rem 0.75rem; border: 1px solid ${isSelected ? 'var(--primary-color)' : '#e2e8f0'}; border-radius: 0.75rem; cursor: pointer; transition: all 0.2s; background: ${isSelected ? '#f0fdf4' : 'white'};">
                    
                    <div style="position: absolute; top: 10px; right: 10px; font-size: 1.2rem; color: ${isSelected ? 'var(--primary-color)' : '#cbd5e1'};">
                        ${isSelected ? '<i class="fas fa-check-circle"></i>' : '<i class="far fa-circle"></i>'}
                    </div>

                    <img src="${item.image_url || DISH_PLACEHOLDER}" onerror="this.src='${DISH_PLACEHOLDER}'" style="width: 56px; height: 56px; border-radius: 50%; object-fit: cover; border: 2px solid #f8fafc;">
                    
                    <div style="flex: 1; width: 100%;">
                        <h6 style="margin: 0; font-size: 0.85rem; font-weight: 800; color: #1e293b; line-height: 1.2;">${item.name}</h6>
                        <div style="font-size: 0.65rem; font-weight: 800; color: var(--primary-color); text-transform: uppercase; margin-top: 4px;">${item.category}</div>
                    </div>
                    <input type="checkbox" name="linked_menu_ids" value="${item.id}" ${isSelected ? 'checked' : ''} style="display:none;">
                </div>
            `;
        };

        if (eqContainer && eqCats.length > 0) eqContainer.innerHTML = eqCats.map(i => renderCard(i)).join('');
        else if (eqContainer) eqContainer.innerHTML = '<div style="grid-column: 1/-1; color: #94a3b8; font-size: 0.85rem; padding: 1rem 0;">No equipment found in your library.</div>';

        if (svcContainer && svcCats.length > 0) svcContainer.innerHTML = svcCats.map(i => renderCard(i)).join('');
        else if (svcContainer) svcContainer.innerHTML = '<div style="grid-column: 1/-1; color: #94a3b8; font-size: 0.85rem; padding: 1rem 0;">No services found in your library.</div>';

        if (menuContainer && foodCats.length > 0) {
            const grouped = {};
            foodCats.forEach(item => {
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
                html += items.map(i => renderCard(i)).join('');
            }
            menuContainer.innerHTML = html;
        } else if (menuContainer) {
            menuContainer.innerHTML = '<div class="text-center py-5 text-slate-400">Your menu library is empty.</div>';
        }

        updateSelectionRulesBuilder();
        renderAddonLists();
    } catch (e) {
        console.error('[Packages] Menu library fetch error:', e);
    }
};

window.openAddonPicker = function(type) {
    currentAddonType = type;
    const title = document.getElementById('addonPickerTitle');
    const grid = document.getElementById('addonPickerGrid');
    if (!title || !grid) return;
    
    title.innerText = `Select ${type.charAt(0).toUpperCase() + type.slice(1)} Add-ons`;
    
    let items = [];
    if (type === 'equipment') {
        items = globalPkgLibrary.filter(i => String(i.id).startsWith('eq_'));
    } else if (type === 'service') {
        items = globalPkgLibrary.filter(i => String(i.id).startsWith('svc_'));
    } else {
        items = globalPkgLibrary.filter(i => !String(i.id).startsWith('eq_') && !String(i.id).startsWith('svc_'));
    }
    
    grid.innerHTML = items.map(item => `
        <div class="addon-picker-card" 
             data-id="${item.id}"
             data-name="${item.name.replace(/"/g, '&quot;')}"
             data-price="${item.price || 0}"
             onclick="window.toggleAddonPickerCard(this)"
             style="position: relative; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 0.5rem; padding: 1rem 0.5rem; border: 1px solid #e2e8f0; border-radius: 0.5rem; cursor: pointer; transition: all 0.2s; background: white;">
            
            <div style="position: absolute; top: 8px; right: 8px; font-size: 1rem; color: #cbd5e1;">
                <i class="far fa-square"></i>
            </div>
            
            <h6 style="margin: 0; font-size: 0.8rem; font-weight: 800; color: #1e293b; line-height: 1.2;">${item.name}</h6>
            <div style="font-size: 0.65rem; font-weight: 700; color: #64748b;">₱${(item.price || 0).toLocaleString()}</div>
        </div>
    `).join('');
    
    safeOpenModal('addonPickerModal');
};

window.closeAddonPicker = () => safeCloseModal('addonPickerModal');
window.closeAddonConfig = () => safeCloseModal('addonConfigModal');

window.toggleAddonPickerCard = function(card) {
    const isSelected = card.classList.contains('selected');
    if (isSelected) {
        card.classList.remove('selected');
        card.style.background = 'white';
        card.style.borderColor = '#e2e8f0';
        card.querySelector('i').className = 'far fa-square text-slate-300';
    } else {
        card.classList.add('selected');
        card.style.background = '#f0fdf4';
        card.style.borderColor = '#22c55e';
        card.querySelector('i').className = 'fas fa-check-square text-green-500';
    }
};

window.filterAddonPicker = function() {
    const query = document.getElementById('addonPickerSearch')?.value.toLowerCase() || '';
    document.querySelectorAll('#addonPickerGrid .addon-picker-card').forEach(card => {
        const name = card.dataset.name.toLowerCase();
        card.style.display = name.includes(query) ? 'flex' : 'none';
    });
};

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
};

function renderAddonLists() {
    // Menu
    const mList = document.getElementById('pkg-addons-menu-list');
    if (mList) {
        if (configuredAddons.menu.length === 0) {
            mList.innerHTML = '<div class="text-slate-400 text-sm italic">No menu add-ons configured.</div>';
        } else {
            mList.innerHTML = configuredAddons.menu.map((a, i) => renderAddonRow(a, 'menu', i)).join('');
        }
        document.getElementById('hidden_menu_addons').value = JSON.stringify(configuredAddons.menu);
    }
    
    // Service
    const sList = document.getElementById('pkg-addons-service-list');
    if (sList) {
        if (configuredAddons.service.length === 0) {
            sList.innerHTML = '<div class="text-slate-400 text-sm italic">No service add-ons configured.</div>';
        } else {
            sList.innerHTML = configuredAddons.service.map((a, i) => renderAddonRow(a, 'service', i)).join('');
        }
        document.getElementById('hidden_service_addons').value = JSON.stringify(configuredAddons.service);
    }
    
    // Equipment
    const eList = document.getElementById('pkg-addons-equipment-list');
    if (eList) {
        if (configuredAddons.equipment.length === 0) {
            eList.innerHTML = '<div class="text-slate-400 text-sm italic">No equipment add-ons configured.</div>';
        } else {
            eList.innerHTML = configuredAddons.equipment.map((a, i) => renderAddonRow(a, 'equipment', i)).join('');
        }
        document.getElementById('hidden_equipment_addons').value = JSON.stringify(configuredAddons.equipment);
    }
}

function renderAddonRow(addon, type, index) {
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
}

window.removeAddon = function(type, index) {
    if (confirm("Remove this add-on from the package?")) {
        configuredAddons[type].splice(index, 1);
        renderAddonLists();
    }
};

// End Addons Logic
"""

# Now we need to remove the old redundant loadPkgMenuLibrary body from packages.js
# We can do this by regex or string split.
split_point = "// Menu Library Loading"
if split_point in content:
    content = content.split(split_point)[0]
    
    content += "\n" + new_addon_logic
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("packages.js addons module injected.")
else:
    print("Could not find the split point.")

