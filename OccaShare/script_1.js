
/* =====================================================================
   HUB CART ENGINE
   Manages the live order drawer, modal add/remove, and checkout flow.
   ===================================================================== */

// ---- Package data (server-side rendered) ----
window.catererAvailable = {{ 'false' if caterer_unavailable else 'true' }};
window.hubPkgs = {
    {% for pkg in packages %}
    "{{ pkg.id }}": {
        id: {{ pkg.id }},
        name: {{ pkg.name|tojson }},
        desc: {{ (pkg.description or '')|tojson }},
        price: "₱{{ '{:,.2f}'.format(pkg.price if pkg.price else (pkg.price_per_head if pkg.price_per_head else 0)) if pkg.price_unit == 'total' else '{:,.2f}'.format(pkg.price_per_head if pkg.price_per_head else (pkg.price if pkg.price else 0)) }}{{ ' total' if pkg.price_unit == 'total' else '/pax' }}",
        price_raw: {{ (pkg.price_per_head if pkg.price_per_head else (pkg.price or 0))|tojson }},
        price_unit: {{ (pkg.price_unit or 'per_guest')|tojson }},
        min_guests: {{ (pkg.min_guests or 0)|tojson }},
        max_guests: {{ (pkg.max_guests or 0)|tojson }},
        duration: "{{ pkg.service_duration or 4 }} hours",
        additional_guest_price: {{ (pkg.additional_guest_price or 0)|tojson }},
        overtime_fee: {{ (pkg.overtime_fee or 0)|tojson }},
        inclusions: {{ (pkg.inclusions)|tojson if pkg.inclusions else '[]' }},
        linked_inventory: [
            {% for item in pkg.menu_items %}{% if item.category in ['Rentals', 'Services'] %}{{ item.name|tojson }},{% endif %}{% endfor %}
            {% if pkg.equipment_links %}{% for el in pkg.equipment_links %}{{ el.equipment.name|tojson }},{% endfor %}{% endif %}
            {% if pkg.service_links %}{% for sl in pkg.service_links %}{{ sl.service.name|tojson }},{% endfor %}{% endif %}
        ].filter(Boolean),
        dishes: [{% for item in pkg.menu_items %}{% if item.category not in ['Rentals', 'Services'] %}{{ item.name|tojson }},{% endif %}{% endfor %}].filter(Boolean)
    }{{ ',' if not loop.last }}
    {% endfor %}
};

// ---- Cart State ----
window.selectedItems = [];
window.hubCatererId = {{ caterer.id }};

// ---- Update the Live Order Drawer UI ----
window.updateCartUI = function() {
    const list    = document.getElementById('order-items-list');
    const total   = document.getElementById('order-total-price');
    const btn     = document.getElementById('btn-checkout-master');
    const drawer  = document.querySelector('.order-drawer');
    const title   = document.querySelector('.drawer-title');

    if (!list) return;

    const items = window.selectedItems;

    // Show/hide drawer with !important to beat CSS display:none
    if (drawer) {
        drawer.style.setProperty('display', items.length > 0 ? 'block' : 'none', 'important');
    }

    // Update title with count
    if (title) {
        title.innerHTML = `<i class="fas fa-shopping-basket" style="color:var(--hub-primary);"></i>
            Your Selection <span style="background:var(--hub-primary);color:#fff;font-size:0.65rem;padding:2px 8px;border-radius:100px;margin-left:6px;font-weight:800;">${items.length}</span>`;
    }

    // Render items with name, qty, price, subtotal, remove
    list.innerHTML = items.length === 0
        ? `<p style="color:var(--hub-slate-400);font-size:0.82rem;text-align:center;padding:1rem 0;">No items added yet.</p>`
        : items.map(item => {
            const subtotal = (item.qty * item.price).toLocaleString('en-PH', {minimumFractionDigits:2});
            const unitPrice = parseFloat(item.price).toLocaleString('en-PH', {minimumFractionDigits:2});
            return `
            <div class="drawer-item" id="di-${item.id}" style="display:flex;justify-content:space-between;align-items:flex-start;padding:0.75rem 0;border-bottom:1px solid var(--hub-slate-100);gap:0.5rem;">
                <div style="flex:1;min-width:0;">
                    <div style="font-size:0.82rem;font-weight:800;color:var(--hub-text-dark);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${item.name}</div>
                    <div style="font-size:0.72rem;color:var(--hub-slate-400);margin-top:2px;">₱${unitPrice} × ${item.qty}</div>
                </div>
                <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
                    <span style="font-size:0.85rem;font-weight:900;color:var(--hub-primary);">₱${subtotal}</span>
                    <i class="fas fa-times-circle" onclick="window.removeCartItem('${item.id}', '${item.type}')"
                       style="cursor:pointer;color:var(--hub-slate-400);font-size:0.9rem;transition:color 0.2s;"
                       onmouseover="this.style.color='#ef4444'" onmouseout="this.style.color='var(--hub-slate-400)'"
                       title="Remove"></i>
                </div>
            </div>`;
        }).join('');

    // Grand total
    const sum = items.reduce((acc, i) => acc + (i.qty * i.price), 0);
    if (total) total.textContent = '₱' + sum.toLocaleString('en-PH', {minimumFractionDigits:2});

    // Checkout button state
    if (btn) btn.disabled = items.length === 0;
};

// ---- Remove item from cart ----
window.removeCartItem = function(id, type) {
    if (!type) type = 'Menu'; // Fallback
    window.selectedItems = window.selectedItems.filter(i => !(String(i.id) === String(id) && i.type === type));
    
    // Reset modal btn if dish modal is open
    const mbtn = document.getElementById(type === 'Menu' ? 'mbtn-' + id : `mbtn-${type}-${id}`);
    const mqty = document.getElementById(type === 'Menu' ? 'mq-' + id : `mq-${type}-${id}`);
    
    if (mbtn) { mbtn.classList.remove('selected'); mbtn.textContent = (type === 'Equipment') ? 'Rent' : 'Add'; }
    if (mqty) mqty.disabled = false;
    window.updateCartUI();
};

// ---- Toggle item from the ORIGINAL dish grid (legacy) ----
window.toggleMenuItem = function(id, name, price) {
    const idx = window.selectedItems.findIndex(i => String(i.id) === String(id));
    const btn = document.getElementById('btn-add-' + id);
    const qty = document.getElementById('qty-' + id);
    const qtyVal = qty ? (parseInt(qty.value) || 1) : 1;

    if (idx === -1) {
        window.selectedItems.push({ id: String(id), name, price: parseFloat(price), qty: qtyVal });
        if (btn) {
            btn.classList.add('selected');
            btn.innerHTML = '<i class="fas fa-check"></i> <span class="btn-text">Added</span>';
        }
        if (qty) qty.disabled = true;
    } else {
        window.selectedItems.splice(idx, 1);
        if (btn) {
            btn.classList.remove('selected');
            btn.innerHTML = '<i class="fas fa-plus"></i> <span class="btn-text">Add to Order</span>';
        }
        if (qty) qty.disabled = false;
    }
    window.updateCartUI();
};

// ---- Checkout: redirect to alacarte checkout ----
window.checkoutOrder = function() {
    if (window.selectedItems.length === 0) return;
    const menuIds = window.selectedItems.map(i => {
        if (i.type === 'Equipment') return 'e_' + i.id;
        if (i.type === 'Service') return 's_' + i.id;
        return 'm_' + i.id;
    }).join(',');
    const catererId = {{ caterer.id }};
    sessionStorage.setItem('alacarte_cart_' + catererId, JSON.stringify(window.selectedItems));
    window.location.href = `/bookings/alacarte/checkout/${catererId}?menu_id=${menuIds}`;
};

// ---- Init on load ----
document.addEventListener('DOMContentLoaded', function() {
    window.updateCartUI();
});
