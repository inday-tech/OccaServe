import re

def rewrite_packages_js():
    js_path = r"c:\OccaServe\OccaShare\app\static\js\caterer\packages.js"

    new_js = """// Professional Package Management Logic (Wizard Optimized v16.0)
console.log("[Packages] v16.0 Loading...");

// Constants
const DISH_PLACEHOLDER = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100%25' height='100%25' fill='%23f8fafc'/%3E%3Cpath d='M30 40 L70 40 L50 70 Z' fill='%23e2e8f0'/%3E%3Ctext x='50%25' y='85%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='8' font-weight='800' fill='%23cbd5e1'%3ENO DISH IMAGE%3C/text%3E%3C/svg%3E";

const STEPS_ORDER = ['basic', 'inclusions', 'menu', 'addons', 'pricing', 'booking', 'review'];
let currentPackageId = null;

// Global Modal Helpers (Fallback if layout.js is missing or different)
const safeOpenModal = (id) => {
    if (window.openModal) {
        window.openModal(id);
    } else {
        const el = document.getElementById(id);
        if (el) {
            el.style.display = 'flex';
            requestAnimationFrame(() => el.classList.add('active'));
        }
    }
};

const safeCloseModal = (id) => {
    if (window.closeModal) {
        window.closeModal(id);
    } else {
        const el = document.getElementById(id);
        if (el) {
            el.classList.remove('active');
            setTimeout(() => {
                if (!el.classList.contains('active')) el.style.display = 'none';
            }, 400);
        }
    }
};

window.closePackageModal = () => safeCloseModal('packageModal');

function getActivePackageId() {
    const form = document.getElementById('packageForm');
    if (!form) return null;
    const action = form.action || form.getAttribute('action') || '';
    if (action.includes('/update')) {
        const parts = action.split('/');
        return parts[parts.length - 2];
    }
    return null;
}

window.togglePricingMode = function(mode) {
    const isFixed = mode === 'fixed';
    
    document.querySelectorAll('.capacity-per-pax').forEach(el => el.style.display = isFixed ? 'none' : 'block');
    document.querySelectorAll('.capacity-fixed').forEach(el => el.style.display = isFixed ? 'block' : 'none');
    
    const priceLabel = document.getElementById('lblPricingMain');
    const estContainer = document.getElementById('estStartingPriceContainer');
    
    if (priceLabel) {
        priceLabel.innerText = isFixed ? 'Package Price (₱) *' : 'Price Per Guest (₱) *';
    }
    
    if (estContainer) {
        estContainer.style.display = isFixed ? 'none' : 'block';
    }
    
    calculatePricing();
};

window.openAddPackageModal = async function() {
    try {
        const form = document.getElementById('packageForm');
        if (!form) return;
        
        const title = document.getElementById('packageModalTitle');
        if (title) title.innerText = 'Create New Package';

        form.action = '/caterer/packages/add';
        form.reset();

        // Reset new fields to defaults
        if (form.pricing_mode) form.pricing_mode.value = 'per_pax';
        if (form.status) form.status.value = 'active';
        
        window.togglePricingMode('per_pax');

        // Reset Image Preview
        const preview = document.getElementById('pkgImagePreview');
        const placeholder = document.getElementById('previewPlaceholder');
        if (preview) {
            preview.src = '';
            preview.style.display = 'none';
        }
        if (placeholder) placeholder.style.display = 'flex';

        // Clear checked inclusions
        document.querySelectorAll('input[name="linked_menu_ids"]').forEach(cb => cb.checked = false);

        await loadPkgMenuLibrary();
        
        // Reset wizard to Step 1
        switchPackageTab(document.getElementById('step-btn-basic'), 'basic');
        
        safeOpenModal('packageModal');
    } catch (e) {
        console.error('[Packages] Error opening package modal:', e);
    }
};

window.editPackage = async function(pkgId) {
    if (!pkgId) return;

    try {
        const response = await fetch(`/caterer/packages/${pkgId}/details`);
        if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);

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
        if (form.pricing_mode) form.pricing_mode.value = pkg.pricing_mode || 'per_pax';
        if (form.price_per_head) form.price_per_head.value = pkg.price_per_head || pkg.price || '';
        if (form.min_guests) form.min_guests.value = pkg.min_guests || 50;
        if (form.max_guests) form.max_guests.value = pkg.max_guests || '';
        if (form.base_pax) form.base_pax.value = pkg.base_pax || '';
        if (form.status) form.status.value = pkg.status || 'active';
        if (form.booking_lead_time) form.booking_lead_time.value = pkg.booking_lead_time || 7;
        
        if (pkg.policies) {
            if (form.policies_cancellation) form.policies_cancellation.value = pkg.policies.cancellation || '';
            if (form.policies_internal) form.policies_internal.value = pkg.policies.internal || '';
        }

        window.togglePricingMode(form.pricing_mode ? form.pricing_mode.value : 'per_pax');

        if (form.selection_rules) {
            form.selection_rules.value = pkg.selection_rules ? JSON.stringify(pkg.selection_rules) : '';
        }

        // Image Preview Handling
        const preview = document.getElementById('pkgImagePreview');
        const placeholder = document.getElementById('previewPlaceholder');
        if (preview && pkg.image_url) {
            preview.src = pkg.image_url;
            preview.style.display = 'block';
            if (placeholder) placeholder.style.display = 'none';
        } else if (preview) {
            preview.style.display = 'none';
            if (placeholder) placeholder.style.display = 'flex';
        }

        await loadPkgMenuLibrary();

        // Reset wizard to Step 1
        switchPackageTab(document.getElementById('step-btn-basic'), 'basic');
        
        safeOpenModal('packageModal');
    } catch (e) {
        console.error('[Packages] Error loading package details:', e);
        if (window.showError) window.showError("Could not load package details.");
        else alert("Oops! Could not load package details.");
    }
};

window.previewPackageImage = function(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const preview = document.getElementById('pkgImagePreview');
            const placeholder = document.getElementById('previewPlaceholder');
            if (preview) {
                preview.src = e.target.result;
                preview.style.display = 'block';
            }
            if (placeholder) {
                placeholder.style.display = 'none';
            }
        }
        reader.readAsDataURL(input.files[0]);
    }
};

function calculatePricing() {
    const form = document.getElementById('packageForm');
    if (!form) return;
    
    const mode = form.pricing_mode ? form.pricing_mode.value : 'per_pax';
    const rawPrice = (form.price_per_head.value || '').replace(/,/g, '');
    const price = parseFloat(rawPrice) || 0;
    
    if (mode === 'per_pax') {
        const minGuests = parseInt(form.min_guests.value) || 0;
        const estTotal = price * minGuests;
        const valEl = document.getElementById('estStartingPriceValue');
        if (valEl) valEl.innerText = '₱' + estTotal.toLocaleString('en-PH', {minimumFractionDigits: 2});
    }
}

// Attach event listeners for price calculation
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('packageForm');
    if (form) {
        if (form.price_per_head) form.price_per_head.addEventListener('input', calculatePricing);
        if (form.min_guests) form.min_guests.addEventListener('input', calculatePricing);
    }
});

// Dynamic Wizard Navigation
window.switchPackageTab = function(el, tabName) {
    if (!el) return;
    
    const targetIdx = STEPS_ORDER.indexOf(tabName);
    const activeStepEl = document.querySelector('.pkg-step-side.active');
    const currentTabName = activeStepEl ? activeStepEl.id.replace('step-btn-', '') : 'basic';
    const currentIdx = STEPS_ORDER.indexOf(currentTabName);
    
    // Validate forward movement
    if (targetIdx > currentIdx) {
        for (let i = currentIdx; i < targetIdx; i++) {
            if (!validateTab(STEPS_ORDER[i])) {
                const failEl = document.getElementById('step-btn-' + STEPS_ORDER[i]);
                if (failEl) {
                    document.querySelectorAll('.pkg-step-side').forEach(s => s.classList.remove('active'));
                    failEl.classList.add('active');
                }
                return;
            }
        }
    }

    document.querySelectorAll('.pkg-step-side').forEach(s => s.classList.remove('active'));
    el.classList.add('active');

    document.querySelectorAll('#packageModal .tab-pane-pro').forEach(p => p.classList.remove('active'));
    const target = document.getElementById('tab-' + tabName);
    if (target) {
        target.classList.add('active');
        const body = document.querySelector('#packageModal .occ-modal-body');
        if (body) body.scrollTop = 0;
    }

    // Update Progress
    const progressEl = document.getElementById('pkgWizardProgress');
    if (progressEl) {
        const pct = ((targetIdx + 1) / STEPS_ORDER.length) * 100;
        progressEl.style.width = pct + '%';
    }

    // Navigation Buttons
    const btnBack = document.getElementById('btnWizardBack');
    const btnNext = document.getElementById('btnWizardNext');
    const btnSave = document.getElementById('pkgSaveBtn');
    
    if (btnBack) btnBack.style.display = targetIdx > 0 ? 'inline-flex' : 'none';
    
    if (targetIdx === STEPS_ORDER.length - 1) {
        if (btnNext) btnNext.style.display = 'none';
        if (btnSave) btnSave.style.display = 'inline-flex';
        updateReviewTab();
    } else {
        if (btnNext) btnNext.style.display = 'inline-flex';
        if (btnSave) btnSave.style.display = 'none';
    }
};

window.goToWizardNextStep = function() {
    const activeStepEl = document.querySelector('.pkg-step-side.active');
    if (!activeStepEl) return;
    const currentTabName = activeStepEl.id.replace('step-btn-', '');
    const currentIdx = STEPS_ORDER.indexOf(currentTabName);
    if (currentIdx < STEPS_ORDER.length - 1) {
        const nextTab = STEPS_ORDER[currentIdx + 1];
        switchPackageTab(document.getElementById('step-btn-' + nextTab), nextTab);
    }
};

window.goToWizardBackStep = function() {
    const activeStepEl = document.querySelector('.pkg-step-side.active');
    if (!activeStepEl) return;
    const currentTabName = activeStepEl.id.replace('step-btn-', '');
    const currentIdx = STEPS_ORDER.indexOf(currentTabName);
    if (currentIdx > 0) {
        const prevTab = STEPS_ORDER[currentIdx - 1];
        switchPackageTab(document.getElementById('step-btn-' + prevTab), prevTab);
    }
};

function validateTab(tabName) {
    const form = document.getElementById('packageForm');
    if (!form) return true;
    
    let isValid = true;
    
    // Clear old errors
    document.querySelectorAll('.inline-error-badge').forEach(b => b.remove());
    document.querySelectorAll('.control-pro').forEach(c => c.style.borderColor = '');

    const addError = (input, msg) => {
        isValid = false;
        if (!input) return;
        input.style.borderColor = '#ef4444';
        const badge = document.createElement('small');
        badge.className = 'inline-error-badge';
        badge.style = 'color: #ef4444; font-size: 11px; font-weight: 700; margin-top: 4px; display: block;';
        badge.innerText = msg;
        input.parentNode.appendChild(badge);
    };

    if (tabName === 'basic') {
        const nameVal = form.name.value.trim();
        if (!nameVal) addError(form.name, "Package Name is required.");
        
        const mode = form.pricing_mode.value;
        if (mode === 'per_pax') {
            const minG = parseInt(form.min_guests.value);
            if (isNaN(minG) || minG < 1) addError(form.min_guests, "Minimum guests must be at least 1.");
        }
    }
    
    if (tabName === 'pricing') {
        const rawPrice = form.price_per_head.value.replace(/,/g, '');
        const price = parseFloat(rawPrice);
        if (isNaN(price) || price <= 0) {
            addError(form.price_per_head, "Selling price must be greater than 0.");
        }
    }
    
    if (tabName === 'booking') {
        const lead = parseInt(form.booking_lead_time.value);
        if (isNaN(lead) || lead < 0) {
            addError(form.booking_lead_time, "Lead time cannot be negative.");
        }
    }
    
    return isValid;
}

function updateReviewTab() {
    const form = document.getElementById('packageForm');
    if (!form) return;
    
    const dName = document.getElementById('reviewName');
    const dType = document.getElementById('reviewType');
    const dMode = document.getElementById('reviewPricingMode');
    const dCap = document.getElementById('reviewCapacity');
    const dPrice = document.getElementById('reviewPrice');
    
    if (dName) dName.innerText = form.name.value || 'Untitled Package';
    
    let catText = 'General';
    if (form.service_type) {
        const opt = form.service_type.options[form.service_type.selectedIndex];
        catText = opt ? opt.text : form.service_type.value;
    }
    if (dType) dType.innerText = catText;
    
    const mode = form.pricing_mode ? form.pricing_mode.value : 'per_pax';
    if (dMode) dMode.innerText = mode === 'per_pax' ? 'Per Pax' : 'Fixed Package';
    
    if (dCap) {
        if (mode === 'per_pax') {
            const max = form.max_guests.value ? ` to ${form.max_guests.value}` : '+';
            dCap.innerText = `${form.min_guests.value || 0}${max} Guests`;
        } else {
            dCap.innerText = form.base_pax.value ? `Good for ${form.base_pax.value} Guests` : 'N/A';
        }
    }
    
    if (dPrice) {
        const val = form.price_per_head.value || '0';
        dPrice.innerText = `₱${val} ${mode === 'per_pax' ? '/ pax' : 'total'}`;
    }
    
    // Counts
    let dishCount = 0;
    let svcCount = 0;
    let addonCount = 0;
    
    document.querySelectorAll('input[name="linked_menu_ids"]:checked').forEach(cb => {
        const card = cb.closest('.menu-select-card');
        if (card) {
            const isAddon = card.closest('#tab-addons') !== null;
            const isInclusion = card.closest('#tab-inclusions') !== null;
            if (isAddon) addonCount++;
            else if (isInclusion) svcCount++;
            else dishCount++;
        }
    });
    
    const rd = document.getElementById('reviewDishesCount');
    const rs = document.getElementById('reviewServicesCount');
    const ra = document.getElementById('reviewAddonsCount');
    if (rd) rd.innerText = dishCount;
    if (rs) rs.innerText = svcCount;
    if (ra) ra.innerText = addonCount;
}

// Menu Library Loading
async function loadPkgMenuLibrary() {
    const pkgId = getActivePackageId();

    try {
        const [libRes, linkedRes] = await Promise.all([
            fetch('/caterer/api/menu'),
            pkgId ? fetch(`/caterer/packages/${pkgId}/menu`) : Promise.resolve({ json: () => [] })
        ]);

        const library = await libRes.json();
        const linkedItems = pkgId ? await linkedRes.json() : [];
        const linkedIds = Array.isArray(linkedItems) ? linkedItems.map(i => i.id) : [];

        const menuContainer = document.getElementById('pkgMenuLibraryContainer');
        const eqContainer = document.getElementById('inc-equipment-grid');
        const svcContainer = document.getElementById('inc-services-grid');
        const addonsGrid = document.getElementById('addonsGrid');

        if (menuContainer) menuContainer.innerHTML = '';
        if (eqContainer) eqContainer.innerHTML = '';
        if (svcContainer) svcContainer.innerHTML = '';
        if (addonsGrid) addonsGrid.innerHTML = '';

        // Categories mapping
        const foodCats = [];
        const eqCats = [];
        const svcCats = [];
        const addonCats = [];

        library.forEach(item => {
            const cat = item.category ? item.category.toLowerCase() : '';
            if (item.is_addon) {
                addonCats.push(item);
            } else if (cat === 'equipment' || cat === 'rentals' || cat.includes('chair') || cat.includes('table')) {
                eqCats.push(item);
            } else if (cat === 'services' || cat === 'service' || cat.includes('staff')) {
                svcCats.push(item);
            } else {
                foodCats.push(item);
            }
        });

        // Helper to render card
        const renderCard = (item, isAddon = false) => {
            const isSelected = linkedIds.includes(item.id);
            return `
                <div class="menu-select-card ${isSelected ? 'selected' : ''}" 
                     data-id="${item.id}"
                     data-category="${item.category}"
                     onclick="window.toggleLibItemSelectCard(this, ${item.id})"
                     style="position: relative; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 0.5rem; padding: 1.25rem 0.75rem; border: 1px solid ${isSelected ? 'var(--primary-color)' : '#e2e8f0'}; border-radius: 0.75rem; cursor: pointer; transition: all 0.2s; background: ${isSelected ? '#f0fdf4' : 'white'};">
                    
                    <div style="position: absolute; top: 10px; right: 10px; font-size: 1.2rem; color: ${isSelected ? 'var(--primary-color)' : '#cbd5e1'};">
                        ${isSelected ? '<i class="fas fa-check-circle"></i>' : '<i class="far fa-circle"></i>'}
                    </div>

                    <img src="${item.image_url || DISH_PLACEHOLDER}" alt="${item.name}" onerror="this.src='${DISH_PLACEHOLDER}'" style="width: 56px; height: 56px; border-radius: 50%; object-fit: cover; border: 2px solid #f8fafc;">
                    
                    <div style="flex: 1; width: 100%;">
                        <h6 style="margin: 0; font-size: 0.85rem; font-weight: 800; color: #1e293b; line-height: 1.2;">${item.name}</h6>
                        <div style="font-size: 0.65rem; font-weight: 800; color: var(--primary-color); text-transform: uppercase; margin-top: 4px;">${item.category}</div>
                        ${isAddon ? `<div style="font-size: 0.75rem; color: #64748b; font-weight: 700; margin-top: 4px;">Charge: ₱${(item.addon_price || item.price || 0).toLocaleString()}</div>` : ''}
                    </div>
                    <input type="checkbox" name="linked_menu_ids" value="${item.id}" ${isSelected ? 'checked' : ''} style="display:none;">
                </div>
            `;
        };

        // Render Inclusions
        if (eqContainer && eqCats.length > 0) eqContainer.innerHTML = eqCats.map(i => renderCard(i)).join('');
        else if (eqContainer) eqContainer.innerHTML = '<div style="grid-column: 1/-1; color: #94a3b8; font-size: 0.85rem; padding: 1rem 0;">No equipment found in your library.</div>';

        if (svcContainer && svcCats.length > 0) svcContainer.innerHTML = svcCats.map(i => renderCard(i)).join('');
        else if (svcContainer) svcContainer.innerHTML = '<div style="grid-column: 1/-1; color: #94a3b8; font-size: 0.85rem; padding: 1rem 0;">No services found in your library.</div>';

        // Render Menu
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

        // Render Addons
        if (addonsGrid && addonCats.length > 0) {
            addonsGrid.innerHTML = addonCats.map(i => renderCard(i, true)).join('');
        }

        updateSelectionRulesBuilder();
    } catch (e) {
        console.error('[Packages] Menu library fetch error:', e);
    }
}

window.toggleLibItemSelectCard = function(card, id) {
    const cb = card.querySelector('input[type="checkbox"]');
    if (!cb) return;
    cb.checked = !cb.checked;
    
    if (cb.checked) {
        card.classList.add('selected');
        card.style.background = '#f0fdf4';
        card.style.borderColor = '#22c55e';
        const i = card.querySelector('i');
        if (i) i.className = 'fas fa-check-circle text-green-500';
    } else {
        card.classList.remove('selected');
        card.style.background = 'white';
        card.style.borderColor = '#e2e8f0';
        const i = card.querySelector('i');
        if (i) i.className = 'far fa-circle text-slate-200';
    }
    
    // Only update rules if in menu tab
    if (card.closest('#tab-menu')) {
        updateSelectionRulesBuilder();
    }
};

window.clampSelectionRule = function(input, max) {
    let val = parseInt(input.value);
    const parent = input.closest('.form-group-pro');
    const err = parent.querySelector('.error-msg');
    
    if (val > max) {
        input.value = max;
        input.style.borderColor = '#ef4444';
        if (err) {
            err.innerText = `Limit cannot exceed the ${max} selected dishes.`;
            err.style.display = 'block';
        }
    } else {
        input.style.borderColor = '';
        if (err) err.style.display = 'none';
    }
    compileSelectionRules();
};

function updateSelectionRulesBuilder() {
    const container = document.getElementById('selectionRulesContainer');
    if (!container) return;

    // Get selected dish count per category
    const catCounts = {};
    const selectedCats = new Set();
    document.querySelectorAll('#pkgMenuLibraryContainer .menu-select-card.selected').forEach(card => {
        const cat = card.dataset.category;
        if (cat) {
            selectedCats.add(cat);
            catCounts[cat] = (catCounts[cat] || 0) + 1;
        }
    });

    if (selectedCats.size === 0) {
        container.innerHTML = '<div style="grid-column: 1 / -1; color: #94a3b8; font-size: 0.8rem;">Select menu items first to configure rules.</div>';
        return;
    }

    // Try to load existing rules
    let existingRules = {};
    const hiddenInput = document.getElementById('selectionRulesHidden');
    if (hiddenInput && hiddenInput.value) {
        try {
            existingRules = JSON.parse(hiddenInput.value);
        } catch (e) {
            existingRules = {};
        }
    }

    container.innerHTML = '';
    selectedCats.forEach(cat => {
        const currentLimit = existingRules[cat] || '';
        const maxLimit = catCounts[cat] || 1;
        container.innerHTML += `
            <div class="form-group-pro" style="margin-bottom: 0; display: flex; flex-direction: column; justify-content: flex-end; height: 100%;">
                <label style="font-size: 0.7rem; font-weight:800; color: #475569; text-transform: uppercase; letter-spacing: 0.02em; margin-bottom: 0.5rem; display: block; line-height: 1.2;">Limit for ${cat} (Max: ${maxLimit})</label>
                <input type="number" class="control-pro selection-rule-input" data-category="${cat}" value="${currentLimit}" placeholder="Unlimited" min="1" max="${maxLimit}" oninput="window.clampSelectionRule(this, ${maxLimit})">
                <small class="error-msg text-red-500" style="font-size: 10px; display: none; margin-top: 4px; font-weight:600;"></small>
            </div>
        `;
    });
}

function compileSelectionRules() {
    const rules = {};
    document.querySelectorAll('.selection-rule-input').forEach(input => {
        const val = parseInt(input.value);
        if (val > 0) {
            rules[input.dataset.category] = val;
        }
    });
    const hiddenInput = document.getElementById('selectionRulesHidden');
    if (hiddenInput) {
        hiddenInput.value = Object.keys(rules).length > 0 ? JSON.stringify(rules) : '';
    }
}

window.filterPkgMenuLibrary = function() {
    const query = document.getElementById('pkgMenuLibrarySearch')?.value.toLowerCase() || '';
    document.querySelectorAll('#pkgMenuLibraryContainer .menu-select-card').forEach(card => {
        const name = card.querySelector('h6')?.innerText.toLowerCase() || '';
        card.style.display = name.includes(query) ? 'flex' : 'none';
    });
};

window.toggleAllInContainer = function(checkbox, containerSelector) {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    container.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        if (cb.checked !== checkbox.checked) {
            const card = cb.closest('.menu-select-card');
            if (card) window.toggleLibItemSelectCard(card, cb.value);
        }
    });
};

window.archivePackage = async function(id) {
    if (!confirm("Are you sure you want to hide this package? It will no longer be visible to customers.")) return;
    try {
        const res = await fetch(`/caterer/packages/${id}/toggle`, {
            method: 'POST',
            headers: {'X-Requested-With': 'XMLHttpRequest'}
        });
        if (res.ok) window.location.reload();
    } catch (e) {
        console.error(e);
    }
};

document.getElementById('packageForm')?.addEventListener('submit', function(e) {
    // Compile rules before submit
    compileSelectionRules();
});
"""

    with open(js_path, "w", encoding="utf-8") as f:
        f.write(new_js)
    
    print("JS successfully replaced.")

rewrite_packages_js()
