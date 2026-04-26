// Professional Package Management Logic (Wizard Optimized v13.0)

// Constants
const DISH_PLACEHOLDER = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100%25' height='100%25' fill='%23f8fafc'/%3E%3Cpath d='M30 40 L70 40 L50 70 Z' fill='%23e2e8f0'/%3E%3Ctext x='50%25' y='85%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='8' font-weight='800' fill='%23cbd5e1'%3ENO DISH IMAGE%3C/text%3E%3C/svg%3E";

let currentPackageId = null;

// Global Modal Helpers (Fallback if layout.js is missing)
window.openModal = window.openModal || function(id) {
    const el = document.getElementById(id);
    if (el) {
        el.style.display = 'flex';
        requestAnimationFrame(() => el.classList.add('active'));
    }
};

window.closeModal = window.closeModal || function(id) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.remove('active');
        setTimeout(() => {
            if (!el.classList.contains('active')) el.style.display = 'none';
        }, 400);
    }
};

function getActivePackageId() {
    const form = document.getElementById('packageForm');
    if (!form) return null;
    const action = form.action;
    if (action.includes('/update')) {
        const parts = action.split('/');
        return parts[parts.length - 2];
    }
    return null;
}

function openAddPackageModal() {
    try {
        const form = document.getElementById('packageForm');
        if (!form) return;
        
        const title = document.getElementById('packageModalTitle');
        if (title) title.innerText = 'Create New Package';

        form.action = '/caterer/packages/add';
        form.reset();

        // Reset wizard to Step 1
        const firstStep = document.getElementById('step-btn-basic');
        if (firstStep) switchPackageTab(firstStep, 'basic');

        // Render default standard inclusions
        if (typeof renderInclusions === 'function') renderInclusions({});

        // Clear dynamic costs
        if (window.calculateCosts) window.calculateCosts();

        // Initialize Menu Library Tab
        loadPkgMenuLibrary();
        
        if (window.openModal) window.openModal('packageModal');
    } catch (e) {
        console.error('Error opening package modal:', e);
    }
}

async function editPackage(pkgId) {
    try {
        const response = await fetch(`/caterer/packages/${pkgId}/details`);
        if (!response.ok) throw new Error('Failed to fetch');

        const pkg = await response.json();

        const title = document.getElementById('packageModalTitle');
        if (title) title.innerText = 'Edit Package';

        const form = document.getElementById('packageForm');
        if (!form) return;
        form.action = `/caterer/packages/${pkgId}/update`;

        // Populate fields
        if (form.name) form.name.value = pkg.name || '';
        if (form.description) form.description.value = pkg.description || '';
        if (form.service_type) form.service_type.value = pkg.service_type || 'General';
        if (form.price_per_head) form.price_per_head.value = pkg.price_per_head || '';
        if (form.min_guests) form.min_guests.value = pkg.min_guests || 50;
        if (form.service_duration) form.service_duration.value = pkg.service_duration || 8;

        // ROI fields
        const mtInput = document.getElementById('pkgEditorMarkupType');
        const mvInput = document.getElementById('pkgEditorMarkupValue');
        if (mtInput) mtInput.value = pkg.markup_type || 'percentage';
        if (mvInput) mvInput.value = pkg.markup_value || 0;
        if (typeof setEditorMarkupType === 'function') {
            setEditorMarkupType(pkg.markup_type || 'percentage', false);
        }

        // Cost Breakdown (Explicit Fields)
        if (form.base_pax) form.base_pax.value = pkg.base_pax || 50;
        if (form.labor_cost) form.labor_cost.value = pkg.labor_cost || 0;
        if (form.utility_cost) form.utility_cost.value = pkg.utility_cost || 0;
        if (form.equipment_cost) form.equipment_cost.value = pkg.equipment_cost || 0;
        
        const ingDisplay = document.getElementById('pkgIngredientCostDisplay');
        if (ingDisplay) {
            ingDisplay.innerText = '₱' + (pkg.ingredient_total_cost || 0).toFixed(2) + ' / pax';
            ingDisplay.dataset.cost = pkg.ingredient_total_cost || 0;
        }

        if (typeof calculateCosts === 'function') calculateCosts();

        // Inclusions
        if (typeof renderInclusions === 'function') {
            renderInclusions(pkg.inclusions || {});
        }

        // Reset wizard to Step 1
        const firstStep = document.getElementById('step-btn-basic');
        if (firstStep) switchPackageTab(firstStep, 'basic');

        if (window.openModal) window.openModal('packageModal');
    } catch (e) {
        console.error('Error loading package:', e);
        if (window.showError) window.showError("Could not load package details.");
    }
}

const STANDARD_INCLUSIONS = [
    "Tables and Chairs",
    "Table Linens & Centerpieces",
    "Complete Silverware & Glassware",
    "Uniformed Waitstaff",
    "Basic Sound System",
    "Purified Drinking Water",
    "Setup and Teardown",
    "Food Warmers & Buffet Setup"
];

function renderInclusions(activeInclusions = {}) {
    const matrix = document.getElementById('inclusionMatrix');
    if (!matrix) return;
    matrix.innerHTML = '';

    const allInclusions = new Set(STANDARD_INCLUSIONS);
    Object.keys(activeInclusions).forEach(inc => {
        if (activeInclusions[inc]) allInclusions.add(inc);
    });

    allInclusions.forEach(val => {
        const isChecked = activeInclusions[val] === true;
        const isCustom = !STANDARD_INCLUSIONS.includes(val);
        appendInclusionRow(val, isChecked, isCustom);
    });
}

function appendInclusionRow(val, checked = true, isCustom = true) {
    const matrix = document.getElementById('inclusionMatrix');
    if (!matrix) return;
    const newLabel = document.createElement('label');
    newLabel.className = 'matrix-item checklist-item-pro';
    newLabel.style = "position: relative; display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; background: white; border: 1px solid #e2e8f0; border-radius: 0.5rem; cursor: pointer; transition: all 0.2s;";
    
    const checkedAttr = checked ? 'checked' : '';
    
    let actionsHtml = '';
    if (isCustom) {
        actionsHtml = `
        <div style="margin-left: auto; display: flex; gap: 0.4rem;">
            <button type="button" onclick="editCustomInclusion(this, event)" style="color:var(--primary-color); border:none; background:none; cursor:pointer; font-size:11px;"><i class="fas fa-edit"></i></button>
            <button type="button" onclick="this.closest('.matrix-item').remove(); event.preventDefault(); event.stopPropagation();" style="color:#ef4444; border:none; background:none; cursor:pointer; font-size:11px;"><i class="fas fa-trash-alt"></i></button>
        </div>
        `;
    }

    newLabel.innerHTML = `
        <input type="checkbox" name="inclusions" value="${val}" ${checkedAttr} style="width: 1.1rem; height: 1.1rem; accent-color: var(--primary-color); cursor: pointer;" onclick="event.stopPropagation()">
        <span class="inc-text" style="font-size: 0.9rem; font-weight: 600; color: #334155;">${val}</span>
        ${actionsHtml}
    `;
    
    matrix.appendChild(newLabel);
}

function addCustomInclusion() {
    const input = document.getElementById('customInclusionInput');
    if (!input) return;
    const val = input.value.trim();
    if (val) {
        const matrix = document.getElementById('inclusionMatrix');
        if (matrix && !matrix.querySelector(`input[value="${val}"]`)) {
            appendInclusionRow(val, true, true);
        }
        input.value = '';
    }
}

function editCustomInclusion(btn, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const row = btn.closest('.matrix-item');
    const span = row.querySelector('.inc-text');
    const input = row.querySelector('input[type="checkbox"]');
    const newVal = prompt("Edit Inclusion:", span.innerText);
    if (newVal && newVal.trim()) {
        span.innerText = newVal.trim();
        input.value = newVal.trim();
    }
}

function switchPackageTab(el, tabName) {
    if (!el) return;
    document.querySelectorAll('.pkg-step').forEach(s => s.classList.remove('active'));
    el.classList.add('active');

    document.querySelectorAll('#packageModal .tab-pane-pro').forEach(p => p.classList.remove('active'));
    const target = document.getElementById('tab-' + tabName);
    if (target) {
        target.classList.add('active');
        document.querySelector('#packageModal .modal-body-pro').scrollTop = 0;
    }

    if (tabName === 'menu') loadPkgMenuLibrary();
}

async function loadPkgMenuLibrary() {
    const container = document.getElementById('pkgMenuLibraryContainer');
    if (!container) return;

    const pkgId = getActivePackageId();

    try {
        const [libRes, linkedRes] = await Promise.all([
            fetch('/caterer/api/menu'),
            pkgId ? fetch(`/caterer/packages/${pkgId}/menu`) : Promise.resolve({ json: () => [] })
        ]);

        const library = await libRes.json();
        const linkedItems = pkgId ? await linkedRes.json() : [];
        const linkedIds = Array.isArray(linkedItems) ? linkedItems.map(i => i.id) : [];

        container.innerHTML = '';
        if (library.length === 0) {
            container.innerHTML = '<div class="text-center py-5 text-slate-400 text-xs">Your library is currently empty.</div>';
            return;
        }

        container.innerHTML = library.map(item => {
            const isSelected = linkedIds.includes(item.id);
            return `
                <div class="menu-select-card ${isSelected ? 'selected' : ''}" 
                     onclick="toggleLibItemSelectCard(this, ${item.id})"
                     style="display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem; border: 1px solid #e2e8f0; border-radius: 0.75rem; cursor: pointer; transition: all 0.2s; margin-bottom: 0.5rem; background: ${isSelected ? '#f0fdf4' : 'white'}; border-color: ${isSelected ? '#22c55e' : '#e2e8f0'};">
                    <img src="${item.image_url || DISH_PLACEHOLDER}" alt="${item.name}" onerror="this.src=DISH_PLACEHOLDER}" style="width: 40px; height: 40px; border-radius: 0.5rem; object-fit: cover;">
                    <div style="flex: 1;">
                        <h6 style="margin: 0; font-size: 0.85rem; font-weight: 700;">${item.name}</h6>
                        <div style="font-size: 0.7rem; color: #94a3b8;">${item.category}</div>
                    </div>
                    <input type="checkbox" name="linked_menu_ids" value="${item.id}" ${isSelected ? 'checked' : ''} style="display:none;">
                    ${isSelected ? '<i class="fas fa-check-circle text-green-500"></i>' : '<i class="far fa-circle text-slate-200"></i>'}
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Menu library fetch error:', e);
        container.innerHTML = '<div class="text-center py-5 text-red-400 text-xs">Error loading library.</div>';
    }
}

function toggleLibItemSelectCard(card, id) {
    const cb = card.querySelector('input[type="checkbox"]');
    if (!cb) return;
    cb.checked = !cb.checked;
    if (cb.checked) {
        card.classList.add('selected');
        card.style.background = '#f0fdf4';
        card.style.borderColor = '#22c55e';
        card.querySelector('i').className = 'fas fa-check-circle text-green-500';
    } else {
        card.classList.remove('selected');
        card.style.background = 'white';
        card.style.borderColor = '#e2e8f0';
        card.querySelector('i').className = 'far fa-circle text-slate-200';
    }
}

function filterPkgMenuLibrary() {
    const query = document.getElementById('pkgMenuLibrarySearch').value.toLowerCase();
    document.querySelectorAll('.menu-select-card').forEach(card => {
        const name = card.querySelector('h6').innerText.toLowerCase();
        card.style.display = name.includes(query) ? 'flex' : 'none';
    });
}

// Pricing Tools
window.toggleSmartPricing = function() {
    const sec = document.getElementById('smartPricingSection');
    const icon = document.getElementById('smartToolsIcon');
    if (!sec) return;
    const isHidden = sec.style.display === 'none';
    sec.style.display = isHidden ? 'block' : 'none';
    if (icon) icon.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
}

function setEditorMarkupType(type, focus = true) {
    const hb = document.getElementById('pkgEditorMarkupType');
    if (hb) hb.value = type;

    const bPct = document.getElementById('p-markup-percentage');
    const bFix = document.getElementById('p-markup-fixed');
    const sym = document.getElementById('pMarkupSymbol');
    const input = document.getElementById('pkgEditorMarkupValue');

    const activeStyle = "flex:1; height:32px; font-size:9px; font-weight:900; border-radius:6px; border:1px solid var(--color-neutral-900); background:var(--color-neutral-900); color:white;";
    const inactiveStyle = "flex:1; height:32px; font-size:9px; font-weight:900; border-radius:6px; border:1px solid var(--color-neutral-200); background:white; color:var(--color-neutral-500);";

    if (type === 'percentage') {
        bPct.style = activeStyle;
        bFix.style = inactiveStyle;
        if (sym) sym.innerText = '%';
    } else {
        bFix.style = activeStyle;
        bPct.style = inactiveStyle;
        if (sym) sym.innerText = '₱';
    }
    if (focus && input) input.focus();
    updateProjRevenue();
}

window.updateProjRevenue = function() {
    const cost = parseFloat(document.getElementById('cost_price_input').value) || 0;
    const mt = document.getElementById('pkgEditorMarkupType');
    const type = mt ? mt.value : 'percentage';
    const mv = document.getElementById('pkgEditorMarkupValue');
    const val = mv ? parseFloat(mv.value) || 0 : 0;
    const display = document.getElementById('projRevenueDisplay');
    const manualInput = document.getElementById('pkgManualPriceInput');

    let rev = 0;
    if (type === 'percentage') rev = cost * (1 + (val / 100));
    else rev = cost + val;

    if (display) display.innerText = rev.toLocaleString(undefined, { minimumFractionDigits: 2 });
    
    // Auto-sync to manual if smart tools section is visible
    const sp = document.getElementById('smartPricingSection');
    if (manualInput && rev > 0 && sp && sp.style.display !== 'none') {
        manualInput.value = rev.toFixed(0);
    }
}

function calculateCosts() {
    const labor = parseFloat(document.getElementById('pkgLaborCost')?.value) || 0;
    const utility = parseFloat(document.getElementById('pkgUtilityCost')?.value) || 0;
    const equip = parseFloat(document.getElementById('pkgEquipmentCost')?.value) || 0;
    const basePax = parseInt(document.getElementById('pkgBasePax')?.value) || 50;
    
    const ingDisplay = document.getElementById('pkgIngredientCostDisplay');
    const ingCostPerPax = parseFloat(ingDisplay?.dataset?.cost) || 0;

    let overheadTotal = labor + utility + equip;
    let overheadPerPax = basePax > 0 ? overheadTotal / basePax : 0;
    let totalCostPerPax = overheadPerPax + ingCostPerPax;

    const display = document.getElementById('totalCostDisplay');
    if (display) display.innerText = '₱' + totalCostPerPax.toLocaleString(undefined, { minimumFractionDigits: 2 });

    const internalInput = document.getElementById('pkgInternalCostPerPax');
    if (internalInput) internalInput.value = totalCostPerPax;

    const input = document.getElementById('cost_price_input');
    if (input) input.value = totalCostPerPax;

    if (typeof updateProjRevenue === 'function') updateProjRevenue();

    const manualPriceInput = document.getElementById('pkgManualPriceInput');
    const manualPrice = manualPriceInput ? parseFloat(manualPriceInput.value.replace(/,/g, '')) || 0 : 0;
    const badge = document.getElementById('roiMarginBadge');
    
    if (badge) {
        if (manualPrice > 0) {
            const profit = manualPrice - totalCostPerPax;
            const margin = (profit / manualPrice) * 100;
            
            badge.innerText = `${margin.toFixed(1)}% Margin`;
            
            const oldAlert = badge.parentElement.querySelector('.loss-text-alert');
            if (oldAlert) oldAlert.remove();

            if (margin < 0) {
                badge.className = 'roi-badge-smart bad margin-pulse-warning';
                badge.innerText = `LOSS: ${margin.toFixed(1)}%`;
                const alert = document.createElement('span');
                alert.className = 'loss-text-alert';
                alert.style = "color:#ef4444; font-size:10px; font-weight:800; margin-left:8px;";
                alert.innerText = '⚠️ Negative ROI';
                badge.parentElement.appendChild(alert);
            } else if (margin < 20) {
                badge.className = 'roi-badge-smart warning';
                badge.style.background = '#fff7ed';
                badge.style.color = '#f97316';
            } else {
                badge.className = 'roi-badge-smart good';
                badge.style.background = '#f0fdf4';
                badge.style.color = '#22c55e';
            }
        } else {
            badge.innerText = '--% Margin';
            badge.className = 'roi-badge-smart';
            badge.style.background = '#f1f5f9';
            badge.style.color = '#64748b';
        }
    }
}

// Menu Management Modal Logic
function showMenuModal(pkgId, pkgName) {
    currentPackageId = pkgId;
    const title = document.getElementById('targetPkgDisplay');
    if (title) title.innerText = `Package: ${pkgName}`;
    
    document.getElementById('modalMenuPackageId').value = pkgId;
    switchMenuMode('current');
    
    if (window.openModal) window.openModal('menuModal');
}

function hideMenuModal() {
    if (window.closeModal) window.closeModal('menuModal');
}

async function switchMenuMode(mode) {
    document.querySelectorAll('.mtab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('#menuModal .tab-pane-pro').forEach(p => p.style.display = 'none');
    
    const activeBtn = document.querySelector(`.mtab-btn[onclick="switchMenuMode('${mode}')"]`);
    if (activeBtn) activeBtn.classList.add('active');
    
    const pane = document.getElementById(`menu-mode-${mode}`);
    if (pane) pane.style.display = 'block';

    if (mode === 'current') loadPackageMenu();
    if (mode === 'library') loadLibraryItems();
}

async function loadPackageMenu() {
    const container = document.getElementById('menuItemsContainer');
    if (!container) return;
    container.innerHTML = '<div class="text-center py-5"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';

    try {
        const res = await fetch(`/caterer/packages/${currentPackageId}/menu`);
        const items = await res.json();
        
        if (items.length === 0) {
            container.innerHTML = '<div class="text-center py-10 text-slate-400">No items curated for this package yet.</div>';
            return;
        }

        container.innerHTML = items.map(item => `
            <div class="menu-item-pro-row" style="display: flex; align-items: center; gap: 1rem; background: #f8fafc; padding: 1rem; border-radius: 1rem; border-left: 4px solid #ef4444;">
                <img src="${item.image_url || DISH_PLACEHOLDER}" class="dish-thumb" style="width: 50px; height: 50px; border-radius: 0.75rem; object-fit: cover;">
                <div class="dish-info-pro" style="flex: 1;">
                    <h6 style="margin: 0; font-weight: 800;">${item.name}</h6>
                    <span style="font-size: 0.75rem; color: #94a3b8;">${item.category}</span>
                </div>
                <button type="button" onclick="unlinkDish(${item.id})" class="text-red-400" style="border:none; background:none; cursor:pointer;"><i class="fas fa-unlink"></i></button>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = '<div class="text-center py-5 text-red-500">Error loading menu.</div>';
    }
}

async function loadLibraryItems() {
    const container = document.getElementById('libraryItemsContainer');
    if (!container) return;
    container.innerHTML = '<div class="text-center py-5"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';

    try {
        const [libRes, linkedRes] = await Promise.all([
            fetch('/caterer/api/menu'),
            fetch(`/caterer/packages/${currentPackageId}/menu`)
        ]);
        const library = await libRes.json();
        const linkedItems = await linkedRes.json();
        const linkedIds = linkedItems.map(i => i.id);

        container.innerHTML = library.map(item => {
            const isLinked = linkedIds.includes(item.id);
            return `
                <div class="library-item-row" data-name="${item.name.toLowerCase()}" style="display: flex; align-items: center; gap: 1rem; background: #fff; padding: 0.75rem; border-radius: 0.75rem; border: 1px solid #e2e8f0; margin-bottom: 0.5rem;">
                    <img src="${item.image_url || DISH_PLACEHOLDER}" style="width: 40px; height: 40px; border-radius: 0.5rem; object-fit: cover;">
                    <div style="flex: 1;">
                        <h6 style="margin: 0; font-size: 0.85rem; font-weight: 700;">${item.name}</h6>
                        <div style="font-size: 0.7rem; color: #94a3b8;">${item.category}</div>
                    </div>
                    ${isLinked ? 
                        '<span class="text-green-500 font-bold text-xs"><i class="fas fa-check"></i> Linked</span>' : 
                        `<button type="button" onclick="linkDish(${item.id})" class="btn-sm-outline" style="font-size: 10px; padding: 0.25rem 0.5rem;">Link Dish</button>`
                    }
                </div>
            `;
        }).join('');
    } catch (e) {
        container.innerHTML = '<div class="text-center py-5 text-red-500">Error loading library.</div>';
    }
}

function filterLibraryItems() {
    const query = document.getElementById('librarySearchInput').value.toLowerCase();
    document.querySelectorAll('.library-item-row').forEach(row => {
        row.style.display = row.dataset.name.includes(query) ? 'flex' : 'none';
    });
}

async function linkDish(dishId) {
    if (!window.apiAction) return;
    
    const formData = new FormData();
    formData.append('item_id', dishId);
    
    const res = await window.apiAction(`/caterer/packages/${currentPackageId}/menu/link`, {
        method: 'POST',
        body: formData
    });
    if (res) loadLibraryItems();
}

async function unlinkDish(dishId) {
    if (!window.apiAction) return;
    const res = await window.apiAction(`/caterer/packages/${currentPackageId}/menu/${dishId}/unlink`, {
        method: 'POST'
    });
    if (res) loadPackageMenu();
}

async function archivePackage(id) {
    const doArchive = async () => {
        try {
            const res = await fetch(`/caterer/packages/${id}/archive`, { method: 'POST' });
            if (res.ok) window.location.reload();
            else alert('Archive failed.');
        } catch (e) { console.error(e); }
    };

    if (window.showConfirm) {
        window.showConfirm('Are you sure you want to archive this package? It will be hidden from your offerings.', doArchive, 'Archive Package?');
    } else {
        if (confirm('Archive this package?')) doArchive();
    }
}

// Global Exports
window.openAddPackageModal = openAddPackageModal;
window.editPackage = editPackage;
window.switchPackageTab = switchPackageTab;
window.addCustomInclusion = addCustomInclusion;
window.editCustomInclusion = editCustomInclusion;
window.calculateCosts = calculateCosts;
window.setEditorMarkupType = setEditorMarkupType;
window.filterPkgMenuLibrary = filterPkgMenuLibrary;
window.showMenuModal = showMenuModal;
window.hideMenuModal = hideMenuModal;
window.switchMenuMode = switchMenuMode;
window.filterLibraryItems = filterLibraryItems;
window.linkDish = linkDish;
window.unlinkDish = unlinkDish;
window.archivePackage = archivePackage;

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    const pkgForm = document.getElementById('packageForm');
    if (pkgForm) {
        pkgForm.addEventListener('input', () => {
            if (window.calculateCosts) window.calculateCosts();
        });
        
        pkgForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = pkgForm.querySelector('button[type="submit"]');
            const data = new FormData(pkgForm);
            
            if (window.apiAction) {
                const res = await window.apiAction(pkgForm.action, {
                    method: 'POST',
                    body: data
                }, btn);

                if (res) {
                    if (window.closeModal) window.closeModal('packageModal');
                    
                    // If update, refresh the card in-place
                    const action = pkgForm.action;
                    if (action.includes('/update')) {
                        const parts = action.split('/');
                        const pkgId = parts[parts.length - 2];
                        updatePackageCardUI(pkgId, data);
                    } else {
                        // For new packages, reload after a short delay for smooth feel
                        setTimeout(() => window.location.reload(), 1000);
                    }
                }
            }
        });
    }

    function updatePackageCardUI(id, formData) {
        const card = document.getElementById(`package-${id}`);
        if (!card) return;

        const name = formData.get('name');
        const desc = formData.get('description');
        const price = formData.get('price_per_head');
        const minGuests = formData.get('min_guests');
        const imageFile = formData.get('image');

        if (name) {
            const nameEl = card.querySelector('.package-name-pro');
            if (nameEl) nameEl.innerText = name;
        }
        if (desc) {
            const descEl = card.querySelector('.package-desc-pro');
            if (descEl) descEl.innerText = desc.length > 120 ? desc.substring(0, 117) + '...' : desc;
        }
        if (price) {
            const priceEl = card.querySelector('.price-val');
            if (priceEl) priceEl.innerText = '₱' + parseFloat(price.replace(/,/g, '')).toLocaleString();
        }
        if (minGuests) {
            const guestEl = card.querySelector('.spec-item-min span');
            if (guestEl) guestEl.innerText = `${minGuests}+ guests`;
        }
        
        // Handle image preview update if a new image was uploaded
        if (imageFile && imageFile.size > 0) {
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = card.querySelector('.package-media-pro img');
                if (img) img.src = e.target.result;
                else {
                    // If there was no image, we might need to replace the placeholder
                    const media = card.querySelector('.package-media-pro');
                    if (media) media.innerHTML = `<img src="${e.target.result}" alt="${name || 'Package'}" loading="lazy">`;
                }
            };
            reader.readAsDataURL(imageFile);
        }
    }

    const manualPriceInput = document.getElementById('pkgManualPriceInput');
    if (manualPriceInput) {
        manualPriceInput.addEventListener('input', () => {
            if (window.calculateCosts) window.calculateCosts();
        });
    }
});

// Close modal-pro on backdrop click for consistency with layout.js
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-pro')) {
        if (window.closeModal) window.closeModal(e.target.id);
    }
});

window.togglePackageStatus = async function(id, el) {
    try {
        const response = await fetch(`/caterer/packages/${id}/toggle-status`, { method: 'POST' });
        if (response.ok) {
            const result = await response.json();
            if (el) {
                el.innerText = result.is_active ? 'active' : 'hidden';
                el.className = `status-pill-small ${result.is_active ? 'active' : ''}`;
            }
        }
    } catch (e) { console.error('Status toggle error:', e); }
};

window.previewPackageImage = function(event) {
    const preview = document.getElementById('packageImagePreview');
    const area = document.getElementById('photoUploadArea');
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            preview.src = e.target.result;
            preview.style.display = 'block';
            area.style.display = 'none';
        };
        reader.readAsDataURL(file);
    }
};

window.filterPackages = function() {
    const input = document.getElementById('packageSearchInput');
    const filter = input.value.toLowerCase();
    const cards = document.querySelectorAll('.package-card-pro');

    cards.forEach(card => {
        const textContent = card.textContent || card.innerText;
        card.style.display = textContent.toLowerCase().indexOf(filter) > -1 ? "" : "none";
    });
};

// ROI Management
let currentRoiPackageId = null;
let currentMarkupType = 'percentage';

window.openRoiModal = function(pkgId, pkgName, markupType, markupValue) {
    currentRoiPackageId = pkgId;
    currentMarkupType = markupType || 'percentage';
    document.getElementById('roiModalSubtitle').innerText = `Package: ${pkgName}`;
    document.getElementById('roiMarkupValue').value = markupValue || 0;
    setMarkupType(currentMarkupType);
    if (window.openModal) window.openModal('roiModal');
};

window.hideRoiModal = function() {
    if (window.closeModal) window.closeModal('roiModal');
};

window.setMarkupType = function(type) {
    currentMarkupType = type;
    const btnPct = document.getElementById('btn-markup-percentage');
    const btnFix = document.getElementById('btn-markup-fixed');
    const symbol = document.getElementById('markupSymbol');
    const label = document.getElementById('markupValueLabel');

    if (type === 'percentage') {
        if (btnPct) btnPct.style.background = 'white', btnPct.style.color = 'var(--primary-color)', btnPct.style.boxShadow = '0 2px 4px rgba(0,0,0,0.05)';
        if (btnFix) btnFix.style.background = 'transparent', btnFix.style.color = 'var(--color-neutral-500)', btnFix.style.boxShadow = 'none';
        if (symbol) symbol.innerText = '%';
        if (label) label.innerText = 'Markup Value (%)';
    } else {
        if (btnFix) btnFix.style.background = 'white', btnFix.style.color = 'var(--primary-color)', btnFix.style.boxShadow = '0 2px 4px rgba(0,0,0,0.05)';
        if (btnPct) btnPct.style.background = 'transparent', btnPct.style.color = 'var(--color-neutral-500)', btnPct.style.boxShadow = 'none';
        if (symbol) symbol.innerText = '₱';
        if (label) label.innerText = 'Markup Amount (₱)';
    }
};

window.saveRoi = async function() {
    const val = parseFloat(document.getElementById('roiMarkupValue').value) || 0;
    const resp = await fetch(`/caterer/api/packages/${currentRoiPackageId}/roi`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            markup_type: currentMarkupType, 
            markup_value: val 
        })
    });
    if (resp.ok) location.reload();
};

window.onclick = function(event) {
    const pModal = document.getElementById('packageModal');
    const mModal = document.getElementById('menuModal');
    const rModal = document.getElementById('roiModal');
    if (event.target == pModal) window.closeModal('packageModal');
    if (event.target == mModal) window.closeModal('menuModal');
    if (event.target == rModal) window.closeModal('roiModal');
};
