// Professional Package Management Logic (Wizard Optimized v17.0 - Unlimited Inclusions)
console.log("[Packages] v17.0 Loading...");

// Constants
const DISH_PLACEHOLDER = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100%25' height='100%25' fill='%23f8fafc'/%3E%3Cpath d='M30 40 L70 40 L50 70 Z' fill='%23e2e8f0'/%3E%3Ctext x='50%25' y='85%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='8' font-weight='800' fill='%23cbd5e1'%3ENO DISH IMAGE%3C/text%3E%3C/svg%3E";

let STEPS_ORDER = ['basic', 'inclusions', 'review'];
const ALL_STEPS = ['basic', 'inclusions', 'review'];
let currentPackageId = null;

// ==========================================
// UNLIMITED INCLUSIONS STATE (v17)
// ==========================================
// Each item: { category: 'Menu / Food'|'Service'|'Equipment'|'Other', name, quantity, description, notes }
let packageInclusions = [];


window.scrollToInclusionSection = function (sectionId, btn) {
    const el = document.getElementById(sectionId);
    if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    if (btn) {
        document.querySelectorAll('.inclusion-section-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }
};

window.toggleFoodMode = function (mode) {
    let rulesContainer = document.getElementById('selectionRulesWrapper');
    if (rulesContainer) {
        rulesContainer.style.display = mode === 'customer' ? 'block' : 'none';
    }
};


// Global Modal Helpers
const safeOpenModal = (id, float = false) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.display = 'flex';
    requestAnimationFrame(() => {
        el.classList.add('active');
    });
    document.body.style.overflow = 'hidden';
};

const safeCloseModal = (id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('active');
    el.style.display = 'none';
    const anyActive = document.querySelectorAll('.occ-modal-overlay.active');
    if (anyActive.length === 0) {
        document.body.style.overflow = '';
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

window.togglePricingMode = function (mode) {
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

window.openAddPackageModal = function () {
    const form = document.getElementById('packageForm');
    if (!form) { console.error('[Packages] packageForm not found'); return; }

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
    if (preview) { preview.src = ''; preview.style.display = 'none'; }
    if (placeholder) placeholder.style.display = 'flex';

    // Reset gallery preview
    const galleryContainer = document.getElementById('pkgGalleryPreviewContainer');
    if (galleryContainer) galleryContainer.innerHTML = '';

    // Reset unlimited inclusions state
    packageInclusions = [];
    renderInclusionsList();
    syncInclusionsHidden();

    // Fetch catalog in background
    if (window.fetchInclusionsCatalog) window.fetchInclusionsCatalog();

    // Reset wizard to Step 1 and open modal immediately
    switchPackageTab(document.getElementById('step-btn-basic'), 'basic');
    safeOpenModal('packageModal');

    // Load addon library in background (non-blocking)
    loadPkgMenuLibrary().catch(e => console.warn('[Packages] Library load error (non-critical):', e));
};

window.editPackage = async function (pkgId) {
    if (!pkgId) return;

    try {
        if (window.fetchInclusionsCatalog) window.fetchInclusionsCatalog();

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
        if (form.additional_guest_price) form.additional_guest_price.value = pkg.additional_guest_price || '';
        if (form.status) form.status.value = pkg.status || 'active';
        if (form.booking_lead_time) form.booking_lead_time.value = pkg.booking_lead_time || 7;

        if (pkg.policies) {
            if (form.policies_cancellation) form.policies_cancellation.value = pkg.policies.cancellation || '';
            if (form.policies_internal) form.policies_internal.value = pkg.policies.internal || '';
        }

        window.togglePricingMode(form.pricing_mode ? form.pricing_mode.value : 'per_pax');

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

        // Load existing custom inclusions from pkg.inclusions (relational format)
        packageInclusions = [];
        if (pkg.inclusions) {
            if (Array.isArray(pkg.inclusions)) {
                // Relational format: array of objects
                packageInclusions = pkg.inclusions.filter(i => i && (i.name || typeof i === 'string'));
                // Normalize items to standard objects with type and item_id
                packageInclusions = packageInclusions.map(i => {
                    if (typeof i === 'string') return { type: 'Menu', category: 'Menu / Food', item_id: null, name: i, quantity: '', quantity_num: null, unit: '', description: '' };
                    let cat = i.category || 'Menu / Food';
                    let itemType = i.item_type || i.type || (cat === 'Equipment' ? 'Equipment' : (cat === 'Service' ? 'Service' : 'Menu'));
                    if (cat !== 'Menu / Food' && cat !== 'Service' && cat !== 'Equipment' && cat !== 'Menu') {
                        cat = 'Menu / Food';
                    }
                    return {
                        type: itemType,
                        category: cat,
                        item_id: i.item_id || null,
                        name: i.name || '',
                        quantity: i.quantity || '',
                        quantity_num: i.quantity_num || null,
                        unit: i.unit || '',
                        description: i.description || ''
                    };
                });
            } else if (typeof pkg.inclusions === 'object') {
                // Legacy format: { 'item name': true }
                packageInclusions = Object.entries(pkg.inclusions)
                    .filter(([k, v]) => v)
                    .map(([k]) => ({ type: 'Menu', category: 'Menu / Food', item_id: null, name: k, quantity: '', quantity_num: null, unit: '', description: '' }));
            }
        }
        renderInclusionsList();
        syncInclusionsHidden();

        // Open modal immediately, load addon library in background
        switchPackageTab(document.getElementById('step-btn-basic'), 'basic');
        safeOpenModal('packageModal');

        loadPkgMenuLibrary().catch(e => console.warn('[Packages] Library load error (non-critical):', e));
    } catch (e) {
        console.error('[Packages] Error loading package details:', e);
        if (window.showError) window.showError("Could not load package details.");
        else alert("Oops! Could not load package details.");
    }
};

window.previewPackageImage = function (input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function (e) {
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

window.previewPackageGallery = function (input) {
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
        reader.onload = function (e) {
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
    const sellingPrice = parseFloat(rawPrice) || 0;

    // Sum cost of all checked inclusion items
    let totalCost = 0;
    const checkedItems = document.querySelectorAll('input[name="linked_menu_ids"]:checked');
    checkedItems.forEach(cb => {
        const itemId = String(cb.value);
        // Find in globalPkgLibrary
        const libraryItem = globalPkgLibrary.find(i => String(i.id) === itemId);
        if (libraryItem && libraryItem.cost_price) {
            totalCost += parseFloat(libraryItem.cost_price);
        }
    });

    const valEl = document.getElementById('estStartingPriceValue');
    if (valEl && mode === 'per_pax') {
        const minGuests = parseInt(form.min_guests.value) || 0;
        const estTotal = sellingPrice * minGuests;
        valEl.innerText = '₱' + estTotal.toLocaleString('en-PH', { minimumFractionDigits: 2 });
    }

    // Update Profit Widget
    const costEl = document.getElementById('pkgEstCostValue');
    const profitEl = document.getElementById('pkgEstProfitValue');
    const marginEl = document.getElementById('pkgEstMarginValue');

    if (costEl && profitEl && marginEl) {
        costEl.innerText = '₱' + totalCost.toLocaleString('en-PH', { minimumFractionDigits: 2 });

        const profit = sellingPrice - totalCost;
        profitEl.innerText = '₱' + profit.toLocaleString('en-PH', { minimumFractionDigits: 2 });

        if (profit <= 0) {
            profitEl.style.color = '#dc2626';
            profitEl.parentElement.style.background = '#fef2f2';
            profitEl.parentElement.style.borderColor = '#fecaca';
        } else {
            profitEl.style.color = '#15803d';
            profitEl.parentElement.style.background = '#f0fdf4';
            profitEl.parentElement.style.borderColor = '#bbf7d0';
        }

        let margin = 0;
        if (sellingPrice > 0) {
            margin = (profit / sellingPrice) * 100;
        }
        marginEl.innerText = margin.toFixed(1) + '%';

        if (margin < 20) {
            marginEl.style.color = '#dc2626';
            marginEl.parentElement.style.background = '#fef2f2';
            marginEl.parentElement.style.borderColor = '#fecaca';
        } else {
            marginEl.style.color = '#1d4ed8';
            marginEl.parentElement.style.background = '#eff6ff';
            marginEl.parentElement.style.borderColor = '#bfdbfe';
        }
    }
}

// Attach event listeners for price calculation and form submission
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('packageForm');
    if (form) {
        if (form.price_per_head) form.price_per_head.addEventListener('input', calculatePricing);
        if (form.min_guests) form.min_guests.addEventListener('input', calculatePricing);

        // Guarantee inclusions are serialized right before form submit
        form.addEventListener('submit', () => {
            syncInclusionsHidden();
        });
    }
});

// Dynamic Wizard Navigation
window.switchPackageTab = function (el, tabName) {
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
        const content = document.querySelector('#packageModal .modal-content, #packageModal .pkg-wizard-content');
        if (content) content.scrollTop = 0;
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

window.goToWizardNextStep = function () {
    const activeStepEl = document.querySelector('.pkg-step-side.active');
    if (!activeStepEl) return;
    const currentTabName = activeStepEl.id.replace('step-btn-', '');
    const currentIdx = STEPS_ORDER.indexOf(currentTabName);
    if (currentIdx < STEPS_ORDER.length - 1) {
        const nextTab = STEPS_ORDER[currentIdx + 1];
        switchPackageTab(document.getElementById('step-btn-' + nextTab), nextTab);
    }
};

window.goToWizardBackStep = function () {
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

        if (form.price_per_head) {
            const rawPrice = form.price_per_head.value.replace(/,/g, '');
            const price = parseFloat(rawPrice);
            if (isNaN(price) || price <= 0) {
                addError(form.price_per_head, "Selling price must be greater than 0.");
            }
        }

        if (form.reservation_fee && form.reservation_fee.value) {
            const resFee = parseFloat(form.reservation_fee.value);
            const price = parseFloat((form.price_per_head.value || '0').replace(/,/g, ''));
            if (resFee > price) {
                addError(form.reservation_fee, "Reservation fee cannot exceed selling price.");
            }
        }
    }

    if (tabName === 'inclusions') {
        // Inclusions are optional in the new unlimited freeform system
        // No mandatory validation
    }

    return isValid;
}

function updateInclusionCounters() {
    // Kept for backward compatibility but not required in new system
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
        const excessRow = document.getElementById('reviewExcessRow');
        const excessRate = document.getElementById('reviewExcessRate');

        if (mode === 'per_pax') {
            const max = form.max_guests.value ? ` to ${form.max_guests.value}` : '+';
            dCap.innerText = `${form.min_guests.value || 0}${max} Guests`;
            if (excessRow) excessRow.style.display = 'none';
        } else {
            dCap.innerText = form.base_pax.value ? `Good for ${form.base_pax.value} Guests` : 'N/A';
            if (excessRow && form.additional_guest_price && form.additional_guest_price.value) {
                excessRow.style.display = 'block';
                excessRate.innerText = `₱${form.additional_guest_price.value} / head`;
            } else if (excessRow) {
                excessRow.style.display = 'none';
            }
        }
    }

    if (dPrice) {
        const val = form.price_per_head.value || '0';
        dPrice.innerText = `₱${val} ${mode === 'per_pax' ? '/ pax' : 'total'}`;
    }

    // Counts from inclusions state
    const dishCount = packageInclusions.filter(i => i.category === 'Menu / Food' || i.category === 'Menu' || i.type === 'Menu').length;
    const svcCount = packageInclusions.filter(i => i.category === 'Service' || i.type === 'Service').length;
    const eqCount = packageInclusions.filter(i => i.category === 'Equipment' || i.type === 'Equipment').length;

    const rd = document.getElementById('reviewDishesCount');
    const rs = document.getElementById('reviewServicesCount');
    const re = document.getElementById('reviewEquipmentCount');
    if (rd) rd.innerText = dishCount;
    if (rs) rs.innerText = svcCount;
    if (re) re.innerText = eqCount;

    // Show review inclusions detail list
    const reviewInclusionsDetail = document.getElementById('reviewInclusionsDetail');
    if (reviewInclusionsDetail) {
        if (packageInclusions.length === 0) {
            reviewInclusionsDetail.innerHTML = '<div style="color:#94a3b8; font-size:0.85rem; font-style:italic;">No inclusions added yet.</div>';
        } else {
            const grouped = {};
            packageInclusions.forEach(inc => {
                const cat = inc.category || 'Other';
                if (!grouped[cat]) grouped[cat] = [];
                grouped[cat].push(inc);
            });
            const catIcons = { 'Menu / Food': '🍽️', 'Service': '🛎️', 'Equipment': '🪑', 'Other': '📦' };
            let html = '';
            for (const [cat, items] of Object.entries(grouped)) {
                html += `<div style="margin-bottom:0.75rem;"><div style="font-size:0.75rem;font-weight:800;color:#64748b;text-transform:uppercase;margin-bottom:0.35rem;">${catIcons[cat] || '•'} ${cat}</div>`;
                html += items.map(i => `<div style="font-size:0.85rem;color:#1e293b;display:flex;gap:6px;align-items:flex-start;margin-bottom:4px;"><i class="fas fa-check-circle" style="color:#16a34a;margin-top:3px;flex-shrink:0;"></i><span><strong>${i.name}</strong>${i.quantity ? ' — ' + i.quantity : ''}${i.description ? '<br><span style="color:#64748b;font-size:0.78rem;">' + i.description + '</span>' : ''}</span></div>`).join('');
                html += '</div>';
            }
            reviewInclusionsDetail.innerHTML = html;
        }
    }
}



// ==========================================
// OPTIONAL ADD-ONS WIZARD LOGIC (v17)
// ==========================================
let currentAddonType = null;
let configuredAddons = { menu: [], service: [], equipment: [] };
let globalPkgLibrary = [];

// Overwrite loadPkgMenuLibrary to store library globally and fetch existing addons
const originalLoad = window.loadPkgMenuLibrary;
window.loadPkgMenuLibrary = async function () {
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
        updateInclusionCounters();

        // Update the Pricing Guide based on pre-selected items
        if (typeof calculatePricing === 'function') {
            calculatePricing();
        }
    } catch (e) {
        console.error('[Packages] Menu library fetch error:', e);
    }
};

window.openAddonPicker = function (type) {
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

    let selectedComponentIds = Array.from(document.querySelectorAll('input[name="linked_menu_ids"]:checked')).map(cb => String(cb.value));
    let existingAddonIds = configuredAddons[type] ? configuredAddons[type].map(a => String(a.id)) : [];

    items = items.filter(item => {
        let isPackageOnly = item.usage_type === 'package_only';
        let isAlreadyInPackage = selectedComponentIds.includes(String(item.id));
        let isAlreadyAnAddon = existingAddonIds.includes(String(item.id));
        return !isPackageOnly && !isAlreadyInPackage && !isAlreadyAnAddon;
    });

    if (items.length === 0) {
        grid.innerHTML = `<div style="grid-column: 1/-1; padding: 2rem; text-align: center; color: #94a3b8; font-size: 0.9rem;">No available items to add. (Items might be set to 'Package Only', or are already included in this package/add-ons).</div>`;
    } else {
        grid.innerHTML = items.map(item => `
            <div class="addon-picker-card" 
                 data-id="${item.id}"
                 data-name="${item.name.replace(/"/g, '&quot;')}"
                 data-price="${item.price || 0}"
                 data-pricing-type="${item.pricing_type || 'fixed'}"
                 onclick="window.toggleAddonPickerCard(this)"
                 style="position: relative; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; gap: 0.5rem; padding: 1rem 0.5rem; border: 1px solid #e2e8f0; border-radius: 0.5rem; cursor: pointer; transition: all 0.2s; background: white; min-height: 80px;">
                
                <div style="position: absolute; top: 8px; right: 8px; font-size: 1rem; color: #cbd5e1;">
                    <i class="far fa-square"></i>
                </div>
                
                <h6 style="margin: 0; font-size: 0.8rem; font-weight: 800; color: #1e293b; line-height: 1.2;">${item.name}</h6>
                <div style="font-size: 0.65rem; font-weight: 700; color: #64748b;">₱${(item.price || 0).toLocaleString()}</div>
            </div>
        `).join('');
    }

    safeOpenModal('addonPickerModal', true);
};

window.closeAddonPicker = () => safeCloseModal('addonPickerModal');
window.closeAddonConfig = () => safeCloseModal('addonConfigModal');

window.toggleAddonPickerCard = function (card) {
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

window.filterAddonPicker = function () {
    const query = document.getElementById('addonPickerSearch')?.value.toLowerCase() || '';
    document.querySelectorAll('#addonPickerGrid .addon-picker-card').forEach(card => {
        const name = card.dataset.name.toLowerCase();
        card.style.display = name.includes(query) ? 'flex' : 'none';
    });
};


window.proceedToAddonConfig = function () {
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
        const pricingType = card.dataset.pricingType || 'fixed';
        const basePrice = card.dataset.price || 0;

        const existing = configuredAddons[currentAddonType].find(a => String(a.id) === String(id));
        if (existing) {
            container.innerHTML += `<div style="padding: 1rem; background: #fffbeb; border: 1px solid #fde68a; border-radius: 0.5rem; margin-bottom: 1rem; font-size: 0.85rem; color: #92400e;"><strong>${name}</strong> is already configured as an add-on.</div>`;
            return;
        }

        let fieldsHtml = '';

        if (currentAddonType === 'menu') {
            if (pricingType === 'variants') {
                fieldsHtml = `
                    <div style="padding: 0.75rem; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 0.5rem; margin-bottom: 1rem; font-size: 0.85rem; color: #475569;">
                        <i class="fas fa-info-circle text-brand mr-2"></i> This item uses variant pricing. Customers will select their preferred variant during booking, and its price will be added automatically.
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                        <div class="form-group-pro" style="display: none;">
                            <input type="number" class="control-pro cfg-price" value="0" min="0">
                        </div>
                        <div class="form-group-pro" style="grid-column: 1 / -1;">
                            <label>Selection Type</label>
                            <select class="control-pro cfg-selection-type" onchange="window.toggleAddonQtyFields(this)">
                                <option value="single">Single Selection (No Quantity)</option>
                                <option value="multiple">Multiple Selection</option>
                            </select>
                        </div>
                    </div>
                `;
            } else {
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
                `;
            }

            fieldsHtml += `
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

window.toggleAddonQtyFields = function (selectEl) {
    const container = selectEl.closest('.addon-config-item');
    const qtyFields = container.querySelector('.addon-qty-fields');
    if (selectEl.value === 'multiple' || selectEl.value === 'manpower') {
        qtyFields.style.display = 'grid';
    } else {
        qtyFields.style.display = 'none';
    }
};

window.saveAddonConfig = function () {
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
                if (maxInput) maxInput.style.borderColor = 'red';
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

window.removeAddon = function (type, index) {
    if (confirm("Remove this add-on from the package?")) {
        configuredAddons[type].splice(index, 1);
        renderAddonLists();
    }
};

// End Addons Logic

window.toggleLibItemSelectCard = function (card, id) {
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

    // Update inclusion counters
    if (typeof updateInclusionCounters === 'function') {
        updateInclusionCounters();
    }

    // Update selection rules if food item was toggled
    if (card.closest('#food-section') || card.closest('#tab-food')) {
        if (typeof updateSelectionRulesBuilder === 'function') {
            updateSelectionRulesBuilder();
        }
    }

    if (typeof calculatePricing === 'function') {
        calculatePricing();
    }
};

window.toggleAllInContainer = function (checkbox, containerSelector) {
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

window.filterPkgMenuLibrary = function () {
    const searchVal = document.getElementById('pkgMenuLibrarySearch').value.toLowerCase();
    const container = document.getElementById('pkgMenuLibraryContainer');
    if (!container) return;
    const cards = container.querySelectorAll('.menu-select-card');
    cards.forEach(card => {
        const text = card.textContent.toLowerCase();
        if (text.includes(searchVal)) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });
};

window.filterPkgInclusions = function () {
    const searchVal = document.getElementById('pkgInclusionsSearch').value.toLowerCase();
    const container = document.getElementById('tab-inclusions');
    if (!container) return;
    const cards = container.querySelectorAll('.menu-select-card');
    cards.forEach(card => {
        const text = card.textContent.toLowerCase();
        if (text.includes(searchVal)) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });
};


window.filterServices = function () {
    const searchVal = document.getElementById('pkgServicesSearch');
    if (!searchVal) return;
    const container = document.getElementById('inc-services-grid');
    if (!container) return;
    const cards = container.querySelectorAll('.menu-select-card');
    cards.forEach(card => {
        card.style.display = card.textContent.toLowerCase().includes(searchVal.value.toLowerCase()) ? 'flex' : 'none';
    });
};

window.filterEquipment = function () {
    const searchVal = document.getElementById('pkgEquipmentSearch');
    if (!searchVal) return;
    const container = document.getElementById('inc-equipment-grid');
    if (!container) return;
    const cards = container.querySelectorAll('.menu-select-card');
    cards.forEach(card => {
        card.style.display = card.textContent.toLowerCase().includes(searchVal.value.toLowerCase()) ? 'flex' : 'none';
    });
};

// ==========================================
// UNIFIED PACKAGE INCLUSIONS WORKFLOW
// ==========================================

// Helper to safely escape HTML entities
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ==========================================
// ==========================================
// RELATIONAL PACKAGE INCLUSIONS WORKFLOW
// ==========================================

// Centralized Inclusions Catalog State
window.inclusionsCatalog = {
    equipment: [],
    menu: [],
    service: []
};

// Fetch all catalog items (Equipment, Menu, Service) from backend
window.fetchInclusionsCatalog = async function () {
    try {
        const res = await fetch('/caterer/api/catalogs/inclusions');
        if (res.ok) {
            window.inclusionsCatalog = await res.json();
            return window.inclusionsCatalog;
        }
    } catch (e) {
        console.warn('[Packages] Could not load inclusions catalog:', e);
    }
    return window.inclusionsCatalog;
};

// Open Add Inclusion Modal
window.openAddInclusionModal = async function () {
    const editIndexEl = document.getElementById('customInclusionEditIndex');
    const title = document.getElementById('inclusionModalTitle');
    const subtitle = document.getElementById('inclusionModalSubtitle');
    const btnAddAnother = document.getElementById('btnInclusionSaveAddAnother');
    const btnDoneText = document.getElementById('btnInclusionSaveDoneText');
    const alertBox = document.getElementById('addInclusionSuccessAlert');
    const desc = document.getElementById('customInclusionDescription');

    if (editIndexEl) editIndexEl.value = '-1';
    if (title) title.innerText = 'Add Package Inclusion';
    if (subtitle) subtitle.innerText = 'Link existing items from your catalog into this package.';
    if (btnAddAnother) btnAddAnother.style.display = 'inline-flex';
    if (btnDoneText) btnDoneText.innerText = 'Add Inclusion';
    if (alertBox) { alertBox.style.display = 'none'; alertBox.innerText = ''; }
    if (desc) desc.value = '';

    // Ensure catalog is populated
    if (!window.inclusionsCatalog.equipment || window.inclusionsCatalog.equipment.length === 0) {
        await window.fetchInclusionsCatalog();
    }

    // Default to Equipment
    const catSelect = document.getElementById('customInclusionCategory');
    const defaultType = (catSelect && catSelect.value) ? catSelect.value : 'Equipment';
    if (catSelect) catSelect.value = defaultType;

    window.handleInclusionTypeChange(defaultType);

    safeOpenModal('addInclusionModal', true);
    setTimeout(() => {
        const searchInput = document.getElementById('inclusionItemSearch');
        if (searchInput) searchInput.focus();
    }, 120);
};

// Handle Inclusion Type change (Equipment | Menu | Service)
window.handleInclusionTypeChange = function (type, preselectId = null) {
    const normType = (type === 'Menu / Food' || type === 'Menu') ? 'Menu' : (type === 'Service' ? 'Service' : 'Equipment');
    
    const catSelect = document.getElementById('customInclusionCategory');
    if (catSelect && catSelect.value !== normType) {
        catSelect.value = normType;
    }

    const lblItem = document.getElementById('lblInclusionItem');
    const btnCreateText = document.getElementById('btnCreateNewCatalogItemText');
    const searchInput = document.getElementById('inclusionItemSearch');
    const unitInput = document.getElementById('customInclusionQtyUnit');
    const qtyInput = document.getElementById('customInclusionQtyNum');
    const banner = document.getElementById('selectedItemInfoBanner');

    // Update UI text and placeholders
    if (lblItem) lblItem.innerHTML = `${normType} <span style="color: #ef4444;">*</span>`;
    if (btnCreateText) btnCreateText.innerText = `+ Create New ${normType === 'Menu' ? 'Menu Item' : normType}`;
    if (searchInput) {
        searchInput.placeholder = `Type to filter ${normType.toLowerCase()} catalog...`;
        searchInput.value = '';
    }

    if (banner) banner.style.display = 'none';
    const itemIdEl = document.getElementById('customInclusionItemId');
    const nameEl = document.getElementById('customInclusionName');
    if (itemIdEl) itemIdEl.value = '';
    if (nameEl) nameEl.value = '';

    // Suggest default units based on type
    if (unitInput && !unitInput.value) {
        if (normType === 'Equipment') unitInput.placeholder = 'e.g. chairs, pcs';
        else if (normType === 'Menu') unitInput.placeholder = 'e.g. pax, servings';
        else unitInput.placeholder = 'e.g. staff, hours';
    }

    // Populate the dropdown
    window.populateCatalogSelect(normType, '', preselectId);
};

// Populate the Catalog Select dropdown
window.populateCatalogSelect = function (type, filterQuery = '', preselectId = null) {
    const select = document.getElementById('inclusionItemSelect');
    if (!select) return;

    const catalogKey = type.toLowerCase();
    const items = window.inclusionsCatalog[catalogKey] || [];
    const query = (filterQuery || '').toLowerCase().trim();

    const filtered = query ? items.filter(i => {
        const n = (i.name || '').toLowerCase();
        const c = (i.category || '').toLowerCase();
        return n.includes(query) || c.includes(query);
    }) : items;

    let html = `<option value="">-- Select ${type} ▼ --</option>`;
    if (filtered.length === 0) {
        html += `<option value="" disabled>No ${type.toLowerCase()} matching search</option>`;
    } else {
        filtered.forEach(item => {
            const isSelected = preselectId && String(item.id) === String(preselectId);
            const unit = item.unit_type || '';
            const qty = item.available_qty !== undefined ? item.available_qty : (item.max_available !== undefined ? item.max_available : '');
            const cat = item.category || type;
            html += `<option value="${item.id}" 
                        data-name="${escapeHtml(item.name)}" 
                        data-unit="${escapeHtml(unit)}" 
                        data-qty="${qty}" 
                        data-cat="${escapeHtml(cat)}"
                        ${isSelected ? 'selected' : ''}>
                        ${escapeHtml(item.name)} (${escapeHtml(cat)})${qty !== '' ? ' — ' + qty + ' avail' : ''}
                     </option>`;
        });
    }

    select.innerHTML = html;

    if (preselectId) {
        select.value = String(preselectId);
        window.handleCatalogItemSelected(String(preselectId));
    }
};

// Filter items in catalog select on typing in search box
window.filterInclusionCatalogItems = function (query) {
    const catSelect = document.getElementById('customInclusionCategory');
    const type = catSelect ? catSelect.value : 'Equipment';
    window.populateCatalogSelect(type, query);
};

// Handle selection of a catalog item
window.handleCatalogItemSelected = function (selectedId) {
    const select = document.getElementById('inclusionItemSelect');
    const itemIdEl = document.getElementById('customInclusionItemId');
    const nameEl = document.getElementById('customInclusionName');
    const banner = document.getElementById('selectedItemInfoBanner');
    const badge = document.getElementById('selectedItemCategoryBadge');
    const title = document.getElementById('selectedItemTitle');
    const meta = document.getElementById('selectedItemMeta');
    const qtyNum = document.getElementById('customInclusionQtyNum');
    const qtyUnit = document.getElementById('customInclusionQtyUnit');

    if (!selectedId || !select) {
        if (banner) banner.style.display = 'none';
        if (itemIdEl) itemIdEl.value = '';
        if (nameEl) nameEl.value = '';
        window.updateQuantityPreview();
        return;
    }

    const opt = select.options[select.selectedIndex];
    if (!opt || !opt.dataset.name) return;

    const itemName = opt.dataset.name;
    const itemUnit = opt.dataset.unit || '';
    const itemQty = opt.dataset.qty || '';
    const itemCat = opt.dataset.cat || '';

    if (itemIdEl) itemIdEl.value = selectedId;
    if (nameEl) {
        nameEl.value = itemName;
        nameEl.style.borderColor = '';
    }

    // Display banner overview
    if (banner) {
        banner.style.display = 'block';
        if (title) title.innerText = itemName;
        if (badge) badge.innerText = itemCat;
        if (meta) meta.innerText = itemQty ? `Available: ${itemQty}` : `Category: ${itemCat}`;
    }

    // Set intelligent default quantity and unit if empty
    const catSelect = document.getElementById('customInclusionCategory');
    const currentType = catSelect ? catSelect.value : 'Equipment';

    if (qtyNum && (!qtyNum.value || qtyNum.value === '0')) {
        if (currentType === 'Equipment') {
            const avail = parseInt(itemQty, 10);
            qtyNum.value = avail && avail < 50 ? String(avail) : '50';
        } else if (currentType === 'Menu') {
            qtyNum.value = '100';
        } else {
            qtyNum.value = '1';
        }
    }

    if (qtyUnit && !qtyUnit.value) {
        if (itemUnit) {
            qtyUnit.value = itemUnit;
        } else if (currentType === 'Equipment') {
            const nLower = itemName.toLowerCase();
            if (nLower.includes('chair')) qtyUnit.value = 'chairs';
            else if (nLower.includes('table')) qtyUnit.value = 'tables';
            else qtyUnit.value = 'units';
        } else if (currentType === 'Menu') {
            qtyUnit.value = 'pax';
        } else {
            qtyUnit.value = 'staff';
        }
    }

    select.style.borderColor = '';
    window.updateQuantityPreview();
};

// Update dynamic quantity preview text
window.updateQuantityPreview = function () {
    const qtyNumEl = document.getElementById('customInclusionQtyNum');
    const qtyUnitEl = document.getElementById('customInclusionQtyUnit');
    const qtyPreview = document.getElementById('qtyPreviewDisplay');
    const hiddenQty = document.getElementById('customInclusionQuantity');

    const num = qtyNumEl ? qtyNumEl.value.trim() : '';
    const unit = qtyUnitEl ? qtyUnitEl.value.trim() : '';

    let formatted = '';
    if (num && unit) {
        formatted = `${num} ${unit}`;
    } else if (num) {
        formatted = `${num}`;
    } else if (unit) {
        formatted = `${unit}`;
    }

    if (hiddenQty) hiddenQty.value = formatted;
    if (qtyPreview) qtyPreview.innerText = formatted || 'None specified';
};

// Edit Existing Inclusion
window.editInclusion = async function (index) {
    if (typeof index !== 'number' || index < 0 || index >= packageInclusions.length) return;
    const item = packageInclusions[index];

    const editIndexEl = document.getElementById('customInclusionEditIndex');
    const title = document.getElementById('inclusionModalTitle');
    const subtitle = document.getElementById('inclusionModalSubtitle');
    const btnAddAnother = document.getElementById('btnInclusionSaveAddAnother');
    const btnDoneText = document.getElementById('btnInclusionSaveDoneText');
    const alertBox = document.getElementById('addInclusionSuccessAlert');
    const desc = document.getElementById('customInclusionDescription');
    const qtyNumEl = document.getElementById('customInclusionQtyNum');
    const qtyUnitEl = document.getElementById('customInclusionQtyUnit');

    if (editIndexEl) editIndexEl.value = String(index);
    if (title) title.innerText = 'Edit Package Inclusion';
    if (subtitle) subtitle.innerText = 'Update the details of this package inclusion.';
    if (btnAddAnother) btnAddAnother.style.display = 'none';
    if (btnDoneText) btnDoneText.innerText = 'Save Changes';
    if (alertBox) { alertBox.style.display = 'none'; alertBox.innerText = ''; }
    if (desc) desc.value = item.description || '';

    // Determine type
    let itemType = item.type;
    if (!itemType) {
        const cat = (item.category || '').toLowerCase();
        if (cat.includes('equipment')) itemType = 'Equipment';
        else if (cat.includes('service')) itemType = 'Service';
        else itemType = 'Menu';
    }

    // Ensure catalog is populated
    if (!window.inclusionsCatalog.equipment || window.inclusionsCatalog.equipment.length === 0) {
        await window.fetchInclusionsCatalog();
    }

    // Pre-populate fields
    if (item.quantity_num) {
        if (qtyNumEl) qtyNumEl.value = item.quantity_num;
        if (qtyUnitEl) qtyUnitEl.value = item.unit || '';
    } else if (item.quantity) {
        const m = String(item.quantity).match(/^(\d+)\s*(.*)$/);
        if (m) {
            if (qtyNumEl) qtyNumEl.value = m[1];
            if (qtyUnitEl) qtyUnitEl.value = m[2] || '';
        } else {
            if (qtyNumEl) qtyNumEl.value = '';
            if (qtyUnitEl) qtyUnitEl.value = item.quantity;
        }
    }

    window.handleInclusionTypeChange(itemType, item.item_id);

    // If item_id wasn't in catalog yet, set name manually
    const nameEl = document.getElementById('customInclusionName');
    if (nameEl) nameEl.value = item.name || '';

    window.updateQuantityPreview();
    safeOpenModal('addInclusionModal', true);
};

// Close Modal
window.closeAddInclusionModal = function () {
    safeCloseModal('addInclusionModal');
};

// Save Inclusion (Add or Edit)
window.saveInclusion = function (addAnother = false) {
    const editIndexEl = document.getElementById('customInclusionEditIndex');
    const catSelect = document.getElementById('customInclusionCategory');
    const select = document.getElementById('inclusionItemSelect');
    const itemIdEl = document.getElementById('customInclusionItemId');
    const nameEl = document.getElementById('customInclusionName');
    const qtyNumEl = document.getElementById('customInclusionQtyNum');
    const qtyUnitEl = document.getElementById('customInclusionQtyUnit');
    const descEl = document.getElementById('customInclusionDescription');
    const alertBox = document.getElementById('addInclusionSuccessAlert');

    const selectedType = catSelect ? catSelect.value : 'Equipment';
    const itemId = itemIdEl ? itemIdEl.value : '';
    let nameVal = (nameEl ? nameEl.value : '').trim();

    // If name is empty, attempt to read from select
    if (!nameVal && select && select.selectedIndex > 0) {
        const opt = select.options[select.selectedIndex];
        if (opt && opt.dataset.name) nameVal = opt.dataset.name;
    }

    // Validation: Item must be chosen
    if (!nameVal) {
        if (select) {
            select.style.borderColor = '#ef4444';
            select.focus();
        }
        return;
    }
    if (select) select.style.borderColor = '';

    // Formatted Quantity
    window.updateQuantityPreview();
    const qtyVal = (document.getElementById('customInclusionQuantity') || {}).value || '';
    const qtyNum = qtyNumEl && qtyNumEl.value ? parseInt(qtyNumEl.value, 10) : null;
    const qtyUnit = qtyUnitEl ? qtyUnitEl.value.trim() : '';
    const descVal = descEl ? descEl.value.trim() : '';

    const categoryVal = selectedType === 'Menu' ? 'Menu / Food' : selectedType;

    const itemObj = {
        type: selectedType,
        category: categoryVal,
        item_id: itemId ? parseInt(itemId, 10) : null,
        name: nameVal,
        quantity: qtyVal,
        quantity_num: qtyNum,
        unit: qtyUnit,
        description: descVal
    };

    const editIndex = editIndexEl ? parseInt(editIndexEl.value, 10) : -1;

    if (editIndex >= 0 && editIndex < packageInclusions.length) {
        // Edit Mode
        packageInclusions[editIndex] = itemObj;
        syncInclusionsHidden();
        renderInclusionsList();
        safeCloseModal('addInclusionModal');
    } else {
        // Add Mode
        packageInclusions.push(itemObj);
        syncInclusionsHidden();
        renderInclusionsList();

        if (addAnother) {
            if (alertBox) {
                alertBox.style.display = 'block';
                alertBox.innerHTML = `<i class="fas fa-check-circle" style="margin-right:6px;"></i> Saved <strong>${escapeHtml(nameVal)}</strong>! You can add another inclusion below.`;
                setTimeout(() => {
                    if (alertBox) alertBox.style.display = 'none';
                }, 3500);
            }
            // Reset for next inclusion
            if (select) select.value = '';
            if (itemIdEl) itemIdEl.value = '';
            if (nameEl) nameEl.value = '';
            if (qtyNumEl) qtyNumEl.value = '';
            if (qtyUnitEl) qtyUnitEl.value = '';
            if (descEl) descEl.value = '';
            const banner = document.getElementById('selectedItemInfoBanner');
            if (banner) banner.style.display = 'none';
            window.updateQuantityPreview();
            const searchInput = document.getElementById('inclusionItemSearch');
            if (searchInput) {
                searchInput.value = '';
                searchInput.focus();
            }
        } else {
            safeCloseModal('addInclusionModal');
        }
    }
};

// Remove Inclusion
window.removeInclusion = function (index) {
    if (typeof index !== 'number' || index < 0 || index >= packageInclusions.length) return;
    packageInclusions.splice(index, 1);
    syncInclusionsHidden();
    renderInclusionsList();
};

// Sync packageInclusions array to the hidden form field
function syncInclusionsHidden() {
    const hiddenInput = document.getElementById('package_inclusions_json');
    if (hiddenInput) {
        hiddenInput.value = JSON.stringify(packageInclusions);
    }
}

// Handle "+ Create New Equipment / Service / Menu" from the inclusion form
window.handleCreateNewCatalogItem = function () {
    const catSelect = document.getElementById('customInclusionCategory');
    const type = catSelect ? catSelect.value : 'Equipment';
    const editIndexEl = document.getElementById('customInclusionEditIndex');
    const editIdx = editIndexEl ? editIndexEl.value : '-1';

    // Store return state
    window._pkgInclusionReturnState = {
        active: true,
        type: type,
        editIndex: editIdx
    };

    // Close inclusion modal temporarily
    safeCloseModal('addInclusionModal');

    if (type === 'Equipment') {
        if (typeof openWizard === 'function') {
            openWizard('rentalWizardModal');
        } else {
            alert("Opening Add New Rental wizard...");
        }
    } else if (type === 'Service') {
        if (typeof openWizard === 'function') {
            openWizard('serviceWizardModal');
        } else {
            alert("Opening Add New Service wizard...");
        }
    } else if (type === 'Menu') {
        safeOpenModal('quickAddMenuModal', true);
    }
};

window.closeQuickAddMenuModal = function () {
    safeCloseModal('quickAddMenuModal');
    safeOpenModal('addInclusionModal', true);
};

window.submitQuickAddMenu = async function (e) {
    e.preventDefault();
    const form = document.getElementById('quickAddMenuForm');
    const btn = document.getElementById('btnQuickMenuSubmit');
    if (!form) return;
    const data = new FormData(form);
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Saving...</span>';
    }
    try {
        const res = await fetch('/caterer/menu/add', {
            method: 'POST',
            body: data,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const json = await res.json();
        if (json && (json.status === 'success' || json.item_id || json.id)) {
            safeCloseModal('quickAddMenuModal');
            form.reset();
            await window.handleCatalogItemCreated('Menu', json);
        } else {
            alert((json && json.message) || 'Error adding menu item');
        }
    } catch (err) {
        console.error(err);
        alert('Failed to save menu item.');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check"></i> <span>Save &amp; Select</span>';
        }
    }
};

// Callback when a new item is created from rental/service wizard to return to package inclusions
window.handleCatalogItemCreated = async function (type, resData) {
    window._pkgInclusionReturnState = null;

    // Refresh the inclusions catalog
    await window.fetchInclusionsCatalog();

    const createdId = resData.item_id || (resData.item ? resData.item.id : null) || resData.id;
    const createdName = resData.item_name || (resData.item ? resData.item.name : null) || resData.name;

    // Re-open inclusion modal
    window.openAddInclusionModal();

    // Switch to type and auto-select the newly created item
    setTimeout(() => {
        window.handleInclusionTypeChange(type, createdId);

        const alertBox = document.getElementById('addInclusionSuccessAlert');
        if (alertBox && createdName) {
            alertBox.style.display = 'block';
            alertBox.innerHTML = `<i class="fas fa-check-circle" style="margin-right:6px;"></i> Newly created <strong>${escapeHtml(createdName)}</strong> has been automatically selected!`;
            setTimeout(() => { if (alertBox) alertBox.style.display = 'none'; }, 4500);
        }
    }, 150);
};

// Render clean, professional list / card layout for inclusions
function renderInclusionsList() {
    const container = document.getElementById('inclusionsListGrouped');
    const chipsContainer = document.getElementById('inclusionsSummaryChips');
    const totalBadge = document.getElementById('inclusionsTotalBadge');
    const bottomAdd = document.getElementById('inclusionsBottomAddContainer');
    if (!container) return;

    const totalCount = packageInclusions.length;
    const dishCount = packageInclusions.filter(i => (i.category === 'Menu / Food' || i.type === 'Menu')).length;
    const svcCount = packageInclusions.filter(i => (i.category === 'Service' || i.type === 'Service')).length;
    const eqCount = packageInclusions.filter(i => (i.category === 'Equipment' || i.type === 'Equipment')).length;

    // Update Header Badge
    if (totalBadge) {
        totalBadge.innerText = `${totalCount} Total Inclusion${totalCount === 1 ? '' : 's'}`;
        totalBadge.style.background = totalCount > 0 ? '#e2e8f0' : '#f1f5f9';
        totalBadge.style.color = totalCount > 0 ? '#0f172a' : '#475569';
    }

    // Update Summary Filter Chips & Bottom Add Button
    if (totalCount === 0) {
        if (chipsContainer) chipsContainer.style.display = 'none';
        if (bottomAdd) bottomAdd.style.display = 'none';

        container.innerHTML = `
            <div style="text-align: center; padding: 3.5rem 2rem; background: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 16px; margin: 0.5rem 0;">
                <div style="width: 56px; height: 56px; border-radius: 50%; background: #e2e8f0; color: #64748b; display: inline-flex; align-items: center; justify-content: center; font-size: 1.5rem; margin-bottom: 1rem;">
                    <i class="fas fa-layer-group"></i>
                </div>
                <h4 style="font-size: 1.1rem; font-weight: 800; color: #1e293b; margin: 0 0 0.4rem 0;">No inclusions added yet</h4>
                <p style="font-size: 0.85rem; color: #64748b; max-width: 420px; margin: 0 auto 1.5rem auto; line-height: 1.5;">Add the menu, services, and equipment included in this package.</p>
                <button type="button" class="btn-primary-pro" onclick="window.openAddInclusionModal()"
                    style="display: inline-flex; align-items: center; gap: 8px; padding: 0.65rem 1.25rem; font-size: 0.875rem; font-weight: 800; border-radius: 10px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
                    <i class="fas fa-plus"></i>
                    <span>+ Add Inclusion</span>
                </button>
            </div>
        `;
        return;
    }

    if (chipsContainer) {
        chipsContainer.style.display = 'flex';
        chipsContainer.innerHTML = `
            <span style="font-size: 0.78rem; font-weight: 800; color: #0f172a; background: #e2e8f0; padding: 4px 12px; border-radius: 20px;">
                Total: ${totalCount}
            </span>
            ${dishCount > 0 ? `<span style="font-size: 0.78rem; font-weight: 700; color: #15803d; background: #f0fdf4; border: 1px solid #bbf7d0; padding: 4px 10px; border-radius: 20px;">🍽️ ${dishCount} Menu / Food</span>` : ''}
            ${svcCount > 0 ? `<span style="font-size: 0.78rem; font-weight: 700; color: #1d4ed8; background: #eff6ff; border: 1px solid #bfdbfe; padding: 4px 10px; border-radius: 20px;">🛎️ ${svcCount} Service</span>` : ''}
            ${eqCount > 0 ? `<span style="font-size: 0.78rem; font-weight: 700; color: #c2410c; background: #fff7ed; border: 1px solid #fed7aa; padding: 4px 10px; border-radius: 20px;">🪑 ${eqCount} Equipment</span>` : ''}
        `;
    }

    if (bottomAdd) {
        bottomAdd.style.display = 'block';
    }

    // Category styling theme configuration
    const catConfig = {
        'Menu / Food': {
            badgeBg: '#f0fdf4',
            badgeColor: '#15803d',
            badgeBorder: '#bbf7d0',
            icon: 'fas fa-utensils',
            iconBg: '#dcfce7',
            iconColor: '#16a34a'
        },
        'Menu': {
            badgeBg: '#f0fdf4',
            badgeColor: '#15803d',
            badgeBorder: '#bbf7d0',
            icon: 'fas fa-utensils',
            iconBg: '#dcfce7',
            iconColor: '#16a34a'
        },
        'Service': {
            badgeBg: '#eff6ff',
            badgeColor: '#1d4ed8',
            badgeBorder: '#bfdbfe',
            icon: 'fas fa-concierge-bell',
            iconBg: '#dbeafe',
            iconColor: '#2563eb'
        },
        'Equipment': {
            badgeBg: '#fff7ed',
            badgeColor: '#c2410c',
            badgeBorder: '#fed7aa',
            icon: 'fas fa-chair',
            iconBg: '#ffedd5',
            iconColor: '#ea580c'
        }
    };

    let html = '';
    packageInclusions.forEach((item, index) => {
        let cat = item.category || 'Menu / Food';
        if (cat === 'Menu') cat = 'Menu / Food';
        const cfg = catConfig[cat] || catConfig['Menu / Food'];

        html += `
        <div class="inclusion-item-card" style="display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; padding: 1rem 1.25rem; background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.02); transition: all 0.2s ease;">
            <div style="display: flex; align-items: flex-start; gap: 1rem; flex: 1; min-width: 0;">
                <div style="width: 40px; height: 40px; border-radius: 10px; background: ${cfg.iconBg}; color: ${cfg.iconColor}; display: flex; align-items: center; justify-content: center; font-size: 1rem; flex-shrink: 0; margin-top: 2px;">
                    <i class="${cfg.icon}"></i>
                </div>
                <div style="flex: 1; min-width: 0;">
                    <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 4px;">
                        <span style="font-size: 0.72rem; font-weight: 800; color: ${cfg.badgeColor}; background: ${cfg.badgeBg}; border: 1px solid ${cfg.badgeBorder}; padding: 2px 8px; border-radius: 6px; text-transform: uppercase; letter-spacing: 0.4px;">
                            ${cat}
                        </span>
                        ${item.quantity ? `
                            <span style="font-size: 0.78rem; font-weight: 700; color: #475569; background: #f1f5f9; padding: 2px 8px; border-radius: 6px; display: inline-flex; align-items: center; gap: 4px;">
                                <i class="fas fa-tag" style="font-size: 0.65rem; color: #94a3b8;"></i> ${escapeHtml(item.quantity)}
                            </span>
                        ` : ''}
                    </div>
                    <div style="font-size: 0.98rem; font-weight: 800; color: #0f172a; line-height: 1.3; margin-bottom: 3px;">
                        ${escapeHtml(item.name)}
                    </div>
                    ${item.description ? `
                        <div style="font-size: 0.84rem; color: #64748b; line-height: 1.45; margin-top: 4px;">
                            ${escapeHtml(item.description)}
                        </div>
                    ` : ''}
                </div>
            </div>

            <!-- Actions -->
            <div style="display: flex; align-items: center; gap: 6px; flex-shrink: 0; margin-left: auto;">
                <button type="button" onclick="window.editInclusion(${index})" title="Edit inclusion"
                    style="display: inline-flex; align-items: center; gap: 5px; padding: 0.45rem 0.75rem; font-size: 0.8rem; font-weight: 700; color: #334155; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; cursor: pointer; transition: all 0.15s;"
                    onmouseover="this.style.background='#e2e8f0'; this.style.color='#0f172a';"
                    onmouseout="this.style.background='#f8fafc'; this.style.color='#334155';">
                    <i class="fas fa-edit" style="color: #64748b;"></i>
                    <span>Edit</span>
                </button>
                <button type="button" onclick="window.removeInclusion(${index})" title="Delete inclusion"
                    style="display: inline-flex; align-items: center; gap: 5px; padding: 0.45rem 0.75rem; font-size: 0.8rem; font-weight: 700; color: #dc2626; background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; cursor: pointer; transition: all 0.15s;"
                    onmouseover="this.style.background='#fee2e2'; this.style.color='#b91c1c';"
                    onmouseout="this.style.background='#fef2f2'; this.style.color='#dc2626';">
                    <i class="fas fa-trash-alt"></i>
                    <span>Delete</span>
                </button>
            </div>
        </div>
        `;
    });

    container.innerHTML = html;
}

window.archivePackage = function (id) {
    if (!id) return;
    const confirmBtn = document.getElementById('confirmArchivePackageBtn');
    if (confirmBtn) {
        confirmBtn.onclick = async function () {
            try {
                confirmBtn.disabled = true;
                confirmBtn.innerText = 'Archiving...';
                const res = await fetch(`/caterer/packages/${id}/archive`, {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                });
                if (res.ok) {
                    window.location.reload();
                } else {
                    alert('Failed to archive package.');
                    confirmBtn.disabled = false;
                    confirmBtn.innerText = 'Archive Now';
                }
            } catch (err) {
                console.error('Error archiving package:', err);
                alert('An error occurred while archiving.');
                confirmBtn.disabled = false;
                confirmBtn.innerText = 'Archive Now';
            }
        };
    }
    safeOpenModal('archivePackageModal', true);
};

window.filterPackages = function () {
    const input = document.getElementById('packageSearchInput');
    const query = input ? input.value.toLowerCase().trim() : '';
    const cards = document.querySelectorAll('.package-card-pro');
    let visibleCount = 0;
    cards.forEach(card => {
        const text = card.textContent.toLowerCase();
        if (text.includes(query)) {
            card.style.display = 'flex';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });
    const emptyState = document.getElementById('searchEmptyState');
    if (emptyState) {
        emptyState.style.display = (visibleCount === 0 && query.length > 0) ? 'flex' : 'none';
    }
};


