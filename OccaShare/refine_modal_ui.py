import re

filepath = r'c:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# I will find the window.openDishDetails function and completely replace it.
# First, isolate the function body.
pattern = re.compile(r'window\.openDishDetails = function\(id\) \{.*?\};\n\n\s*window\.openInventoryDetails', re.DOTALL)

new_dish_details = """window.openDishDetails = function(id) {
            const modal = document.getElementById('dish-cat-modal');
            const title = document.getElementById('dish-modal-cat-title');
            const body  = document.getElementById('dish-modal-body');
            const item = window.hubMenuItems.find(i => String(i.id) === String(id));
            if(!item) return;

            title.textContent = "Item Details";

            const img = item.image || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(item.name) + '&background=f1f5f9&color=FF7B54&size=200';
            
            const UNIT_MAP = {
                'per_serving': '', 'per_tray': ' / Tray', 'per_bilao': ' / Bilao',
                'per_pax': ' / Pax', 'per_hour': ' / Hr', 'per_unit': ' / Unit', 'per_set': ' / Set',
                'per_kg': ' / Kg', 'whole': ' / Whole'
            };
            const unitSuffix = item.pricing_unit ? (UNIT_MAP[item.pricing_unit] || '') : '';
            
            let priceDisplay = '';
            let optionsHtml = '';
            
            // Accurately handle all pricing types (Variants, Weight, Size, Fixed)
            if (item.variants && item.variants.length > 0) {
                optionsHtml = '<div style="margin-bottom:8px; font-weight:700; font-size:0.8rem;">Select Option:</div><select class="dish-row-qty" id="opt-' + item.id + '" style="width: 100%; border: 1px solid var(--hub-slate-200); border-radius: 8px; padding: 10px; font-size: 0.9rem; background:#fff;">' + item.variants.map(v => { 
                    let cap = v.serving_capacity ? (String(v.serving_capacity).toLowerCase().includes('pax') ? v.serving_capacity : v.serving_capacity + ' Pax') : ''; 
                    return `<option value="${v.variant_name}|${v.price}" ${v.status !== 'available' ? 'disabled' : ''}>${v.status !== 'available' ? '[UNAVAILABLE] ' : ''}₱${parseFloat(v.price).toLocaleString('en-PH', {minimumFractionDigits:0})} - ${v.variant_name} ${v.measurement ? '('+v.measurement+')' : ''} ${cap ? '| ' + cap : ''}</option>`; 
                }).join('') + '</select>';
                priceDisplay = optionsHtml;
            } else if (item.pricing_type === 'weight_based' && item.weight_prices && item.weight_prices.length > 0) {
                optionsHtml = '<div style="margin-bottom:8px; font-weight:700; font-size:0.8rem;">Select Weight:</div><select class="dish-row-qty" id="opt-' + item.id + '" style="width: 100%; border: 1px solid var(--hub-slate-200); border-radius: 8px; padding: 10px; font-size: 0.9rem; background:#fff;">' + item.weight_prices.map(wp => `<option value="${wp.weight_label}|${wp.price}">${wp.weight_label} - ₱${parseFloat(wp.price).toLocaleString('en-PH', {minimumFractionDigits:0})}${unitSuffix}</option>`).join('') + '</select>';
                priceDisplay = optionsHtml;
            } else if (item.pricing_type === 'size_based' && item.size_prices && item.size_prices.length > 0) {
                optionsHtml = '<div style="margin-bottom:8px; font-weight:700; font-size:0.8rem;">Select Size:</div><select class="dish-row-qty" id="opt-' + item.id + '" style="width: 100%; border: 1px solid var(--hub-slate-200); border-radius: 8px; padding: 10px; font-size: 0.9rem; background:#fff;">' + item.size_prices.map(sp => `<option value="${sp.size_name}|${sp.price}">${sp.size_name} - ₱${parseFloat(sp.price).toLocaleString('en-PH', {minimumFractionDigits:0})}${unitSuffix}</option>`).join('') + '</select>';
                priceDisplay = optionsHtml;
            } else {
                priceDisplay = `<div style="font-size: 1.4rem; font-weight: 900; color: var(--hub-primary);">₱${parseFloat(item.price).toLocaleString('en-PH', {minimumFractionDigits:2})}${unitSuffix}</div>`;
            }

            const isSelected = window.selectedItems.some(s => String(s.id) === String(item.id) && (s.type ? s.type === 'Menu' : true));
            const isFixedQty = ['whole', 'per_event', 'per event', 'package'].includes(String(item.pricing_unit).toLowerCase());
            
            const qtyHtml = isFixedQty ? 
                `<input type="hidden" id="mq-${item.id}" value="1"><span style="font-size:0.85rem;font-weight:800;color:var(--hub-slate-600);padding:10px 16px;background:#fff;border-radius:10px;border:1px solid var(--hub-slate-200);">1 (Fixed)</span>` : 
                `<div style="display:flex; align-items:center; gap:8px;"><span style="font-size:0.85rem; font-weight:700;">Qty:</span><input type="number" id="mq-${item.id}" value="1" min="1" ${isSelected ? 'disabled' : ''} style="width: 70px; padding:10px; border:1px solid var(--hub-slate-200); border-radius:10px; text-align:center; font-weight:800;"></div>`;

            // Make the image smaller and contained to address user's visual feedback on 'storage/size'
            body.innerHTML = `
                <div style="display:flex; flex-direction:column; gap:16px;">
                    <div style="position:relative; width:100%; height:180px; border-radius:12px; overflow:hidden; background:var(--hub-slate-50); box-shadow: inset 0 2px 4px rgba(0,0,0,0.05); display:flex; align-items:center; justify-content:center;">
                        <img src="${img}" style="width:100%; height:100%; object-fit:cover;">
                    </div>
                    <div>
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
                            <span style="font-size: 0.72rem; font-weight: 850; color: var(--hub-primary); text-transform: uppercase; letter-spacing:0.08em;">${item.category}</span>
                        </div>
                        <h3 style="font-size: 1.3rem; font-weight: 850; color: var(--hub-text-dark); margin: 0 0 6px 0; line-height:1.2;">${item.name}</h3>
                        ${item.description ? `<p style="font-size: 0.85rem; color: var(--hub-slate-600); margin: 0; line-height:1.5;">${item.description}</p>` : ''}
                    </div>
                    
                    <div style="background:var(--hub-slate-50); padding:16px; border-radius:12px; border:1px solid var(--hub-slate-100);">
                        ${priceDisplay}
                    </div>

                    <div style="display:flex; align-items:center; gap:12px; margin-top: 4px;">
                        ${item.price > 0 || (item.variants && item.variants.length > 0) || (item.weight_prices && item.weight_prices.length > 0) || (item.size_prices && item.size_prices.length > 0) ? `
                            ${qtyHtml}
                            <button class="btn-hub-main ${isSelected ? 'selected' : ''}" style="flex:1; padding: 12px; font-size: 0.9rem; font-weight:800; border-radius:10px; ${isSelected ? 'background:#10b981; box-shadow: 0 8px 15px rgba(16, 185, 129, 0.2);' : 'box-shadow: 0 8px 15px rgba(255, 123, 84, 0.2);'}" id="mbtn-${item.id}" onclick="window.toggleModalItem(${item.id})">
                                ${isSelected ? '<i class="fas fa-check"></i> Added' : '<i class="fas fa-cart-plus"></i> Add to Order'}
                            </button>
                        ` : '<span style="font-size:0.85rem; font-weight:800; color:var(--hub-slate-400); width:100%; text-align:center; padding:12px; background:var(--hub-slate-50); border-radius:10px;">Price Upon Request</span>'}
                    </div>
                </div>
            `;
            modal.classList.add('active');
        };

        window.openInventoryDetails"""

content = pattern.sub(new_dish_details, content)

# Now fix the inventory modal for smaller images as well
inv_pattern = re.compile(r'window\.openInventoryDetails = function\(id\) \{.*?\};\n\n\s*window\.openCategoryModal', re.DOTALL)

new_inv_details = """window.openInventoryDetails = function(id) {
            const modal = document.getElementById('dish-cat-modal');
            const title = document.getElementById('dish-modal-cat-title');
            const body  = document.getElementById('dish-modal-body');
            const item = window.hubInventoryItems.find(i => String(i.id) === String(id));
            if(!item) return;

            title.textContent = (item.type === 'Equipment') ? "Rental Details" : "Service Details";

            const UNIT_MAP = {
                'per_piece': '/pc', 'per_set': '/set', 'per_day': '/day', 'per_event': '/event',
                'per_hour': '/hr', 'per_person': '/person', 'per_session': '/session', 'piece': '/pc'
            };

            const img = item.image || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(item.name) + '&background=f1f5f9&color=FF7B54&size=200';
            const unitSuffix = UNIT_MAP[item.pricing_unit] || (item.pricing_unit ? '/' + item.pricing_unit : '');
            
            const priceDisplay = item.price > 0
                ? `<div style="font-size: 1.4rem; font-weight: 900; color: var(--hub-primary);">₱${parseFloat(item.price).toLocaleString('en-PH', {minimumFractionDigits:2})}${unitSuffix}</div>`
                : '<div style="font-size:0.85rem; font-weight:800; color:var(--hub-slate-500); padding:8px 0;">Included in Package</div>';

            const isPackageOnly = item.price === 0;
            const isEquipment = item.type === 'Equipment';
            const isSelected = window.selectedItems.some(s => String(s.id) === String(item.id) && s.type === item.type);
            const actionBtnId = `mbtn-${item.type}-${item.id}`;
            const qtyId = `mq-${item.type}-${item.id}`;

            const actionHtml = isPackageOnly
                ? `<span style="font-size:0.85rem;background:#fef3c7;color:#92400e;border:1px solid #fde68a;border-radius:10px;padding:12px 16px;font-weight:800;text-align:center;display:block;width:100%;"><i class="fas fa-box-open"></i> Available Only in Packages</span>`
                : `<div style="display:flex; align-items:center; gap:8px; width: 100%;">
                    <span style="font-size:0.85rem; font-weight:700;">Qty:</span>
                    <input type="number" id="${qtyId}" value="1" min="1" ${isSelected ? 'disabled' : ''} style="width: 70px; padding:10px; border:1px solid var(--hub-slate-200); border-radius:10px; text-align:center; font-weight:800;">
                    <button class="btn-hub-main ${isSelected ? 'selected' : ''}" id="${actionBtnId}" style="flex:1; padding: 12px; font-size: 0.9rem; font-weight:800; border-radius:10px; ${isSelected ? 'background:#10b981; box-shadow: 0 8px 15px rgba(16, 185, 129, 0.2);' : 'box-shadow: 0 8px 15px rgba(255, 123, 84, 0.2);'}" onclick="window.toggleInventoryModalItem(${item.id}, '${item.type}')">
                        ${isSelected ? '<i class="fas fa-check"></i> Added' : (isEquipment ? '<i class="fas fa-plus"></i> Rent Item' : '<i class="fas fa-plus"></i> Book Service')}
                    </button>
                  </div>`;

            body.innerHTML = `
                <div style="display:flex; flex-direction:column; gap:16px;">
                    <div style="position:relative; width:100%; height:180px; border-radius:12px; overflow:hidden; background:var(--hub-slate-50); box-shadow: inset 0 2px 4px rgba(0,0,0,0.05); display:flex; align-items:center; justify-content:center;">
                        <img src="${img}" style="width:100%; height:100%; object-fit:cover;">
                    </div>
                    <div>
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
                            <span style="font-size: 0.72rem; font-weight: 850; color: var(--hub-primary); text-transform: uppercase; letter-spacing:0.08em;">${item.category || item.type}</span>
                        </div>
                        <h3 style="font-size: 1.3rem; font-weight: 850; color: var(--hub-text-dark); margin: 0 0 6px 0; line-height:1.2;">${item.name}</h3>
                        ${item.description ? `<p style="font-size: 0.85rem; color: var(--hub-slate-600); margin: 0; line-height:1.5;">${item.description}</p>` : ''}
                    </div>
                    
                    <div style="background:var(--hub-slate-50); padding:16px; border-radius:12px; border:1px solid var(--hub-slate-100);">
                        ${priceDisplay}
                    </div>

                    <div style="display:flex; align-items:center; gap:12px; margin-top: 4px;">
                        ${actionHtml}
                    </div>
                </div>
            `;
            modal.classList.add('active');
        };

        window.openCategoryModal"""

content = inv_pattern.sub(new_inv_details, content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated Modal Rendering JS!")
