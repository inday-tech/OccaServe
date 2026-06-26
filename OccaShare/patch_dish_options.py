import re
with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to change the JS for `window.openCategoryModal` and `toggleModalItem`.
# For the UI, we should add a <select> if it's weight_based or size_based.
# Since rewriting this large JS block is error-prone via regex, I'll extract it, modify it locally, and write it back.

start_marker = "body.innerHTML = items.map(item => {"
end_marker = "}).join('');"

idx_start = content.find(start_marker)
idx_end = content.find(end_marker, idx_start)

if idx_start != -1 and idx_end != -1:
    block = content[idx_start:idx_end + len(end_marker)]
    
    new_block = """body.innerHTML = items.map(item => {
                const img = item.image || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=200';
                const unitSuffix = item.pricing_unit ? (UNIT_MAP[item.pricing_unit] || '') : '';
                let priceDisplay = '';
                let optionsHtml = '';
                
                if (item.pricing_type === 'weight_based' && item.weight_prices && item.weight_prices.length > 0) {
                    optionsHtml = '<select class="dish-row-qty" id="opt-' + item.id + '" style="width: auto; margin-right: 4px; border: 1px solid var(--hub-slate-200); border-radius: 6px; padding: 4px 8px; font-size: 0.75rem;">' + item.weight_prices.map(wp => `<option value="${wp.weight_label}|${wp.price}">${wp.weight_label} - \u20b1${parseFloat(wp.price).toLocaleString('en-PH', {minimumFractionDigits:0})}</option>`).join('') + '</select>';
                    priceDisplay = '<span style="font-size:0.75rem;font-weight:800;color:var(--hub-brand);">Weight Options Available</span>';
                } else if (item.pricing_type === 'size_based' && item.size_prices && item.size_prices.length > 0) {
                    optionsHtml = '<select class="dish-row-qty" id="opt-' + item.id + '" style="width: auto; margin-right: 4px; border: 1px solid var(--hub-slate-200); border-radius: 6px; padding: 4px 8px; font-size: 0.75rem;">' + item.size_prices.map(sp => `<option value="${sp.size_name}|${sp.price}">${sp.size_name} - \u20b1${parseFloat(sp.price).toLocaleString('en-PH', {minimumFractionDigits:0})}</option>`).join('') + '</select>';
                    priceDisplay = '<span style="font-size:0.75rem;font-weight:800;color:var(--hub-brand);">Size Options Available</span>';
                } else {
                    priceDisplay = item.price > 0
                        ? '\u20b1' + parseFloat(item.price).toLocaleString('en-PH', {minimumFractionDigits:2}) + unitSuffix
                        : '<span style="font-size:0.78rem;font-weight:700;color:var(--hub-slate-400);">Included in Package</span>';
                }
                
                const isSelected = window.selectedItems.some(s => String(s.id) === String(item.id) && (s.type ? s.type === 'Menu' : true));

                const dietHtml = (item.dietary_tags && item.dietary_tags.length > 0)
                    ? item.dietary_tags.map(t => `<span style="font-size:0.65rem;background:#f0fdf4;color:#15803d;border:1px solid #bbf7d0;border-radius:100px;padding:2px 8px;font-weight:700;">${DIET_ICONS[t]||''} ${t}</span>`).join('')
                    : '';

                const allergenHtml = (item.allergen_info && item.allergen_info.length > 0)
                    ? `<span style="font-size:0.65rem;background:#fff7ed;color:#c2410c;border:1px solid #fed7aa;border-radius:100px;padding:2px 8px;font-weight:700;">⚠️ Contains: ${item.allergen_info.join(', ')}</span>`
                    : '';

                const servingHtml = item.serving_size
                    ? `<span style="font-size:0.65rem;color:var(--hub-slate-400);font-weight:600;">${item.serving_size}</span>`
                    : '';

                const descHtml = item.description
                    ? `<div style="font-size:0.72rem;color:var(--hub-slate-400);line-height:1.5;margin-top:2px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;">${item.description}</div>`
                    : '';

                const tagsHtml = (dietHtml || allergenHtml || servingHtml)
                    ? `<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:4px;">${servingHtml}${dietHtml}${allergenHtml}</div>`
                    : '';

                return `
                <div class="dish-row" id="dish-row-${item.id}">
                    <img src="${img}" class="dish-row-img" alt="${item.name}" loading="lazy"
                         onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=200'">
                    <div class="dish-row-info">
                        <div class="dish-row-name">${item.name}</div>
                        <div class="dish-row-price">${priceDisplay}</div>
                        ${descHtml}
                        ${tagsHtml}
                    </div>
                    <div class="dish-row-action">
                        ${optionsHtml}
                        <input type="number" class="dish-row-qty" id="mq-${item.id}" value="1" min="1"
                               ${isSelected ? 'disabled' : ''}>
                        <button type="button"
                            class="dish-row-btn ${isSelected ? 'selected' : ''}"
                            id="mbtn-${item.id}"
                            onclick="window.toggleModalItem(${item.id})">
                            ${isSelected ? (cat === 'Rentals' ? 'Rented ✓' : 'Added ✓') : (cat === 'Rentals' ? 'Rent' : 'Add')}
                        </button>
                    </div>
                </div>`;
            }).join('');"""
            
    content = content.replace(block, new_block)
    with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed dish modal options")
else:
    print("Could not find start_marker")
