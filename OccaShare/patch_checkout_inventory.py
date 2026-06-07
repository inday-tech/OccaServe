import re

path = 'app/static/js/customer/alacarte_checkout.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

js_addition = """
    // Real-Time Inventory Validation
    const dateInputInv = document.getElementById('delivery_date');
    const timeInputInv = document.getElementById('delivery_time');
    
    async function checkInventoryAvailability() {
        if (!dateInputInv || !timeInputInv) return;
        const dateVal = dateInputInv.value;
        const timeVal = timeInputInv.value;
        
        if (!dateVal || !timeVal || window.cart.length === 0) return;
        
        try {
            const res = await fetch('/customer/api/check-inventory', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    caterer_id: window.catererId,
                    date: dateVal,
                    time: timeVal,
                    items: window.cart.map(i => ({ id: i.id, qty: i.qty }))
                })
            });
            const data = await res.json();
            
            const invErrId = 'err-inventory';
            let errEl = document.getElementById(invErrId);
            if (!errEl) {
                errEl = document.createElement('div');
                errEl.id = invErrId;
                errEl.className = 'invalid-feedback';
                // Append under time
                timeInputInv.parentNode.appendChild(errEl);
            }
            
            if (data.status === 'error') {
                errEl.innerText = data.error_text;
                errEl.style.display = 'block';
                dateInputInv.classList.add('is-invalid');
                timeInputInv.classList.add('is-invalid');
                // Block next step if inventory conflict
                window.inventoryConflict = true;
            } else {
                errEl.style.display = 'none';
                dateInputInv.classList.remove('is-invalid');
                timeInputInv.classList.remove('is-invalid');
                window.inventoryConflict = false;
            }
        } catch (e) {
            console.error("Inventory check failed", e);
        }
    }
    
    if (dateInputInv) dateInputInv.addEventListener('change', checkInventoryAvailability);
    if (timeInputInv) timeInputInv.addEventListener('change', checkInventoryAvailability);
"""

target = """    // --- NAVIGATION LOGIC ---"""
replacement = js_addition + "\n    // --- NAVIGATION LOGIC ---"
content = content.replace(target, replacement)

# Block step 3 navigation if inventory conflict
target2 = """            if (!validateScreen(window.currentScreen)) return;"""
replacement2 = """            if (!validateScreen(window.currentScreen)) return;
            if (window.currentScreen === 2 && window.inventoryConflict) {
                if (typeof Swal !== 'undefined') {
                    Swal.fire('Inventory Conflict', 'Some items requested are out of stock for this date. Please adjust quantities or choose another date.', 'error');
                } else {
                    alert('Inventory Conflict: Some items requested are out of stock for this date.');
                }
                return;
            }"""
content = content.replace(target2, replacement2)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched alacarte_checkout.js for inventory validation!")
