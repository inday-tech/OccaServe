import re
with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "window.toggleModalItem = function(id) {"
end_marker = "if (qty) qty.disabled = true;"

idx_start = content.find(start_marker)
idx_end = content.find(end_marker, idx_start)

if idx_start != -1 and idx_end != -1:
    block = content[idx_start:idx_end + len(end_marker)]
    
    new_block = """window.toggleModalItem = function(id) {
            const sid = String(id);
            // Look up the full item object
            const menuItem = window.hubMenuItems
                ? window.hubMenuItems.find(i => String(i.id) === sid)
                : null;

            const idx = window.selectedItems.findIndex(i => String(i.id) === sid);
            const btn = document.getElementById('mbtn-' + sid);
            const qty = document.getElementById('mq-' + sid);
            const opt = document.getElementById('opt-' + sid);
            const qtyVal = qty ? (Math.max(1, parseInt(qty.value) || 1)) : 1;

            if (idx === -1) {
                // Validate: max qty
                if (qtyVal < 1 || qtyVal > 999) {
                    alert('Please enter a valid quantity (1\u2013999).');
                    return;
                }
                
                let finalPrice = menuItem ? (parseFloat(menuItem.price) || 0) : 0;
                let finalName = menuItem ? menuItem.name : 'Item #' + sid;
                
                if (opt && opt.value) {
                    const [optName, optPrice] = opt.value.split('|');
                    finalPrice = parseFloat(optPrice) || finalPrice;
                    finalName = finalName + ' (' + optName + ')';
                }
                
                window.selectedItems.push({
                    id: sid,
                    type: 'Menu',
                    name: finalName,
                    price: finalPrice,
                    qty: qtyVal
                });
                if (btn) { btn.classList.add('selected'); btn.textContent = (menuItem && menuItem.category === 'Rentals') ? 'Rented \u2713' : 'Added \u2713'; }
                if (qty) qty.disabled = true;
                if (opt) opt.disabled = true;"""
                
    content = content.replace(block, new_block)
    
    # Also update the toggle off logic to enable `opt`
    off_old = """                if (btn) { btn.classList.remove('selected'); btn.textContent = (menuItem && menuItem.category === 'Rentals') ? 'Rent' : 'Add'; }
                if (qty) { qty.disabled = false; qty.value = 1; }"""
    off_new = """                if (btn) { btn.classList.remove('selected'); btn.textContent = (menuItem && menuItem.category === 'Rentals') ? 'Rent' : 'Add'; }
                if (qty) { qty.disabled = false; qty.value = 1; }
                const opt = document.getElementById('opt-' + sid);
                if (opt) opt.disabled = false;"""
    content = content.replace(off_old, off_new)

    with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed toggleModalItem")
else:
    print("Could not find start_marker")
