// Professional Package Management Logic (Wizard Optimized v16.0)
console.log("[Packages] v16.0 Loading...");

// Constants
const DISH_PLACEHOLDER = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100%25' height='100%25' fill='%23f8fafc'/%3E%3Cpath d='M30 40 L70 40 L50 70 Z' fill='%23e2e8f0'/%3E%3Ctext x='50%25' y='85%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='8' font-weight='800' fill='%23cbd5e1'%3ENO DISH IMAGE%3C/text%3E%3C/svg%3E";

const STEPS_ORDER = ['basic', 'inclusions', 'menu', 'addons', 'pricing', 'booking', 'review'];
let currentPackageId = null;

// Global Modal Helpers (Fallback if layout.js is missing or different)
const safeOpenModal = (id, float = false) => {
    if (window.openModal && !float) {
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

window.previewPackageGallery = function(input) {
    const container = document.getElementById('pkgGalleryPreviewContainer');
    if (!container) return;
    
    // Check if total files exceed 4
    if (input.files.length > 4) {
        alert("You can only select up to 4 images for the gallery.");
        input.value = ""; // clear
        container.innerHTML = "";
        return;
    }

    container.innerHTML = "";
    
    Array.from(input.files).forEach((file, index) => {
        if (index >= 4) return;
        const reader = new FileReader();
        reader.onload = function(e) {
            const imgEl = document.createElement('img');
            imgEl.src = e.target.result;
            imgEl.style.width = '80px';
            imgEl.style.height = '80px';
            imgEl.style.objectFit = 'cover';
            imgEl.style.borderRadius = 'var(--border-radius)';
            imgEl.style.border = '1px solid #e2e8f0';
            container.appendChild(imgEl);
        }
        reader.readAsDataURL(file);
    });
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
    
    safeOpenModal('addonPickerModal', true);
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
        safeOpenModal('addonConfigModal', true);
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
    if (window.showToast) {
        window.showToast("Add-ons successfully added to package!", "success");
    }
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
}

window.removeAddon = function(type, index) {
    if (confirm("Remove this add-on from the package?")) {
        configuredAddons[type].splice(index, 1);
        renderAddonLists();
    }
};

// End Addons Logic

window.toggleLibItemSelectCard = function(card, id) {
    const cb = card.querySelector('input[type="checkbox"]');
    if (!cb) return;
    cb.checked = !cb.checked;

    if (cb.checked) {
        card.classList.add('selected');
        card.style.background = '#f0fdf4';
        card.style.borderColor = 'var(--primary-color)';
        const i = card.querySelector('div[style*="absolute"] i');
        if (i) {
            i.className = 'fas fa-check-circle';
            i.parentElement.style.color = 'var(--primary-color)';
        }
    } else {
        card.classList.remove('selected');
        card.style.background = 'white';
        card.style.borderColor = '#e2e8f0';
        const i = card.querySelector('div[style*="absolute"] i');
        if (i) {
            i.className = 'far fa-circle';
            i.parentElement.style.color = '#cbd5e1';
        }
    }

    // Only update rules if in menu tab
    if (card.closest('#tab-menu')) {
        if (typeof updateSelectionRulesBuilder === 'function') {
            updateSelectionRulesBuilder();
        }
    }
};

window.toggleAllInContainer = function(checkbox, containerSelector) {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    
    const cards = container.querySelectorAll('.menu-select-card');
    cards.forEach(card => {
        const cb = card.querySelector('input[type="checkbox"]');
        if (!cb) return;
        
        // If the card's state doesn't match the master checkbox state, toggle it
        if (cb.checked !== checkbox.checked) {
            // Trigger the card click programmatically so it updates the UI too
            card.click();
        }
    });
};
