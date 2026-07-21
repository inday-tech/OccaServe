import re

filepath = r'c:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace openInventoryModal(category) with openInventoryDetails(id)
content = re.sub(
    r"onclick=\"window.openInventoryModal\('\{\{ item\.category or '(Service|Equipment)' \}\}'\)\"",
    r'onclick="window.openInventoryDetails({{ item.id }})"',
    content
)

# Inject openDishDetails and openInventoryDetails javascript right before openCategoryModal
js_functions = """
        // ---- Phase 3: Inline View Details Modals ----
        window.openDishDetails = function(id) {
            const modal = document.getElementById('dish-cat-modal');
            const title = document.getElementById('dish-modal-cat-title');
            const body  = document.getElementById('dish-modal-body');
            const item = window.hubMenuItems.find(i => String(i.id) === String(id));
            if(!item) return;

            title.textContent = item.name;

            const img = item.image || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(item.name) + '&background=f1f5f9&color=FF7B54&size=200';
            
            const UNIT_MAP = {
                'per_serving': '', 'per_tray': ' / Tray', 'per_bilao': ' / Bilao',
                'per_pax': ' / Pax', 'per_hour': ' / Hr', 'per_unit': ' / Unit', 'per_set': ' / Set',
                'per_kg': ' / Kg', 'whole': ' / Whole'
            };
            const unitSuffix = item.pricing_unit ? (UNIT_MAP[item.pricing_unit] || '') : '';
            
            let priceDisplay = '';
            let optionsHtml = '';
            if (item.variants && item.variants.length > 0) {
                optionsHtml = '<select class="dish-row-qty" id="opt-' + item.id + '" style="width: 100%; margin-bottom: 12px; border: 1px solid var(--hub-slate-200); border-radius: 6px; padding: 6px; font-size: 0.8rem;">' + item.variants.map(v => { 
                    let cap = v.serving_capacity ? (String(v.serving_capacity).toLowerCase().includes('pax') ? v.serving_capacity : v.serving_capacity + ' Pax') : ''; 
                    return `<option value="${v.variant_name}|${v.price}" ${v.status !== 'available' ? 'disabled' : ''}>${v.status !== 'available' ? '[UNAVAILABLE] ' : ''}₱${parseFloat(v.price).toLocaleString('en-PH', {minimumFractionDigits:0})} - ${v.variant_name} ${v.measurement ? '('+v.measurement+')' : ''} ${cap ? '| ' + cap : ''}</option>`; 
                }).join('') + '</select>';
                priceDisplay = optionsHtml;
            } else {
                priceDisplay = `<div style="font-size: 1.25rem; font-weight: 800; color: var(--hub-primary); margin-bottom: 12px;">₱${parseFloat(item.price).toLocaleString('en-PH', {minimumFractionDigits:2})}${unitSuffix}</div>`;
            }

            const isSelected = window.selectedItems.some(s => String(s.id) === String(item.id) && (s.type ? s.type === 'Menu' : true));
            const isFixedQty = ['whole', 'per_event', 'per event', 'package'].includes(String(item.pricing_unit).toLowerCase());
            
            const qtyHtml = isFixedQty ? 
                `<input type="hidden" id="mq-${item.id}" value="1"><span style="font-size:0.8rem;font-weight:700;color:var(--hub-slate-500);padding:6px 12px;background:var(--hub-slate-50);border-radius:6px;border:1px solid var(--hub-slate-200); margin-right:8px;">Qty: 1 (Fixed)</span>` : 
                `<div style="display:flex; align-items:center; gap:8px; margin-right:8px;"><span style="font-size:0.8rem; font-weight:700;">Qty:</span><input type="number" id="mq-${item.id}" value="1" min="1" ${isSelected ? 'disabled' : ''} style="width: 60px; padding:6px; border:1px solid var(--hub-slate-200); border-radius:6px; text-align:center;"></div>`;

            body.innerHTML = `
                <div style="display:flex; flex-direction:column; gap:12px;">
                    <img src="${img}" style="width:100%; height:200px; object-fit:cover; border-radius:12px; background:var(--hub-slate-50);">
                    <div>
                        <div style="font-size: 0.75rem; font-weight: 700; color: var(--hub-slate-400); text-transform: uppercase;">${item.category}</div>
                        <h3 style="font-size: 1.25rem; font-weight: 800; color: var(--hub-text-dark); margin: 4px 0;">${item.name}</h3>
                        ${item.description ? `<p style="font-size: 0.85rem; color: var(--hub-slate-600); margin: 8px 0;">${item.description}</p>` : ''}
                    </div>
                    ${priceDisplay}
                    <div style="display:flex; align-items:center; border-top: 1px solid var(--hub-slate-100); padding-top: 12px; margin-top: auto;">
                        ${item.price > 0 || (item.variants && item.variants.length > 0) ? `
                            ${qtyHtml}
                            <button class="btn-hub-main ${isSelected ? 'selected' : ''}" style="flex:1; padding: 8px; font-size: 0.85rem; ${isSelected ? 'background:#10b981;' : ''}" id="mbtn-${item.id}" onclick="window.toggleHubItem('${item.id}', '${item.name.replace(/'/g, '\\\'')}', '${item.pricing_type}', '${item.pricing_unit || ''}')">
                                ${isSelected ? '<i class="fas fa-check"></i> Added' : '<i class="fas fa-plus"></i> Add to Order'}
                            </button>
                        ` : '<span style="font-size:0.85rem; font-weight:700; color:var(--hub-slate-400);">Contact caterer for pricing</span>'}
                    </div>
                </div>
            `;
            modal.classList.add('active');
        };

        window.openInventoryDetails = function(id) {
            const modal = document.getElementById('dish-cat-modal');
            const title = document.getElementById('dish-modal-cat-title');
            const body  = document.getElementById('dish-modal-body');
            const item = window.hubInventoryItems.find(i => String(i.id) === String(id));
            if(!item) return;

            title.textContent = item.name;

            const UNIT_MAP = {
                'per_piece': '/pc', 'per_set': '/set', 'per_day': '/day', 'per_event': '/event',
                'per_hour': '/hr', 'per_person': '/person', 'per_session': '/session', 'piece': '/pc'
            };

            const img = item.image || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(item.name) + '&background=f1f5f9&color=FF7B54&size=200';
            const unitSuffix = UNIT_MAP[item.pricing_unit] || (item.pricing_unit ? '/' + item.pricing_unit : '');
            
            const priceDisplay = item.price > 0
                ? `<div style="font-size: 1.25rem; font-weight: 800; color: var(--hub-primary); margin-bottom: 12px;">₱${parseFloat(item.price).toLocaleString('en-PH', {minimumFractionDigits:2})}${unitSuffix}</div>`
                : '<div style="font-size:0.85rem; font-weight:700; color:var(--hub-slate-400); margin-bottom: 12px;">Included in Package</div>';

            const isPackageOnly = item.price === 0;
            const isEquipment = item.type === 'Equipment';
            const isSelected = window.selectedItems.some(s => String(s.id) === String(item.id) && s.type === item.type);
            const actionBtnId = `mbtn-${item.type}-${item.id}`;
            const qtyId = `mq-${item.type}-${item.id}`;

            const actionHtml = isPackageOnly
                ? `<span style="font-size:0.85rem;background:#fef3c7;color:#92400e;border:1px solid #fde68a;border-radius:8px;padding:8px 16px;font-weight:700;text-align:center;display:block;width:100%;"><i class="fas fa-box-open"></i> Available Only in Packages</span>`
                : `<div style="display:flex; align-items:center; gap:8px; width: 100%;">
                    <span style="font-size:0.8rem; font-weight:700;">Qty:</span>
                    <input type="number" id="${qtyId}" value="1" min="1" ${isSelected ? 'disabled' : ''} style="width: 60px; padding:6px; border:1px solid var(--hub-slate-200); border-radius:6px; text-align:center;">
                    <button class="btn-hub-main ${isSelected ? 'selected' : ''}" id="${actionBtnId}" style="flex:1; padding: 8px; font-size: 0.85rem; ${isSelected ? 'background:#10b981;' : ''}" onclick="window.toggleInventoryItem('${item.id}', '${item.name.replace(/'/g, '\\\'')}', ${item.price}, '${item.type}', '${item.pricing_unit || ''}', '${qtyId}', '${actionBtnId}')">
                        ${isSelected ? '<i class="fas fa-check"></i> Added' : (isEquipment ? '<i class="fas fa-plus"></i> Rent' : '<i class="fas fa-plus"></i> Book')}
                    </button>
                  </div>`;

            body.innerHTML = `
                <div style="display:flex; flex-direction:column; gap:12px;">
                    <img src="${img}" style="width:100%; height:200px; object-fit:cover; border-radius:12px; background:var(--hub-slate-50);">
                    <div>
                        <div style="font-size: 0.75rem; font-weight: 700; color: var(--hub-slate-400); text-transform: uppercase;">${item.category || item.type}</div>
                        <h3 style="font-size: 1.25rem; font-weight: 800; color: var(--hub-text-dark); margin: 4px 0;">${item.name}</h3>
                        ${item.description ? `<p style="font-size: 0.85rem; color: var(--hub-slate-600); margin: 8px 0;">${item.description}</p>` : ''}
                    </div>
                    ${priceDisplay}
                    <div style="display:flex; align-items:center; border-top: 1px solid var(--hub-slate-100); padding-top: 12px; margin-top: auto;">
                        ${actionHtml}
                    </div>
                </div>
            `;
            modal.classList.add('active');
        };

        window.openCategoryModal = function(cat) {"""

content = content.replace("        window.openCategoryModal = function(cat) {", js_functions)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated JS functions!")
