// Professional Package Management Logic (Wizard Optimized v17.0 - Unlimited Inclusions)
console.log("[Packages] v17.0 Loading...");

// Constants
var DISH_PLACEHOLDER = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100%25' height='100%25' fill='%23f8fafc'/%3E%3Cpath d='M30 40 L70 40 L50 70 Z' fill='%23e2e8f0'/%3E%3Ctext x='50%25' y='85%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='8' font-weight='800' fill='%23cbd5e1'%3ENO DISH IMAGE%3C/text%3E%3C/svg%3E";

var STEPS_ORDER = ['basic', 'inclusions', 'review'];
var ALL_STEPS = ['basic', 'inclusions', 'review'];
var currentPackageId = null;
let packageNameValidationStatus = 'idle';
let packageNameValidationSequence = 0;
let packageNameValidationTimer = null;

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


// Converts an API error payload into a readable message.
// FastAPI validation errors arrive as `detail: [{loc, msg, ...}]`, which
// stringify to "[object Object]" when shown directly.
function extractErrorMessage(data, fallback = 'Something went wrong. Please try again.') {
    if (!data) return fallback;

    const detail = data.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length) {
        const msgs = detail
            .map(d => (typeof d === 'string' ? d : (d && d.msg) || ''))
            .filter(Boolean);
        if (msgs.length) return msgs.join('\n');
    }
    if (detail && typeof detail === 'object' && typeof detail.msg === 'string') return detail.msg;

    if (typeof data.message === 'string' && data.message.trim()) return data.message;
    return fallback;
}
window.extractErrorMessage = extractErrorMessage;

// Global Modal Helpers
var safeOpenModal = (id, float = false) => {
    const el = document.getElementById(id);
    if (!el) return;

    if (!float) {
        document.querySelectorAll('.occ-modal-overlay.active').forEach((overlay) => {
            if (overlay.id !== id) {
                overlay.classList.remove('active');
                overlay.style.display = 'none';
            }
        });
    }

    el.style.display = 'flex';
    requestAnimationFrame(() => {
        el.classList.add('active');
    });
    document.body.style.overflow = 'hidden';
};

var safeCloseModal = (id) => {
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

function setPackageNameValidation(status, message = '') {
    packageNameValidationStatus = status;
    const messageEl = document.getElementById('packageNameValidationMessage');
    const nameInput = document.getElementById('pkgNameInput');
    if (messageEl) {
        messageEl.textContent = message;
        messageEl.classList.toggle('is-error', status === 'duplicate' || status === 'error');
        messageEl.classList.toggle('is-success', status === 'valid');
    }
    if (nameInput) {
        nameInput.setAttribute('aria-invalid', status === 'duplicate' || status === 'error' ? 'true' : 'false');
    }
    updatePackageWizardControls();
}

async function validatePackageName(name) {
    const normalizedName = name.trim();
    const sequence = ++packageNameValidationSequence;
    if (!normalizedName) {
        setPackageNameValidation('idle');
        return;
    }

    setPackageNameValidation('checking', 'Checking package name...');
    try {
        const response = await fetch('/caterer/api/validate-package-name', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: normalizedName, exclude_id: getActivePackageId() })
        });
        if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
        const result = await response.json();
        if (sequence !== packageNameValidationSequence) return;
        if (result.exists) {
            setPackageNameValidation('duplicate', 'A package with this name already exists. Choose a different name.');
        } else {
            setPackageNameValidation('valid', 'This package name is available.');
        }
    } catch (error) {
        if (sequence !== packageNameValidationSequence) return;
        console.error('[Packages] Package name validation failed:', error);
        setPackageNameValidation('error', 'Could not verify the package name. Check your connection and try again.');
    }
}

function schedulePackageNameValidation(name) {
    window.clearTimeout(packageNameValidationTimer);
    packageNameValidationSequence++;
    if (!name.trim()) {
        setPackageNameValidation('idle');
        return;
    }
    packageNameValidationStatus = 'checking';
    setPackageNameValidation('checking', 'Checking package name...');
    packageNameValidationTimer = window.setTimeout(() => validatePackageName(name), 350);
}

window.togglePricingMode = function (mode) {
    const isFixed = mode === 'fixed';
    const isCustomizable = mode === 'customizable';
    const pricingModeSelect = document.getElementById('pkgPricingModeSelect');
    const previousMode = pricingModeSelect?.dataset.previousMode;

    // 1. Category Field: Only visible for Fixed packages, hidden for Customizable
    const categoryGroup = document.getElementById('pkgCategoryGroup');
    const serviceTypeSelect = document.getElementById('pkgServiceTypeSelect');
    const pricingModeGroup = document.getElementById('pkgPricingModeGroup');

    if (categoryGroup) {
        categoryGroup.style.display = isCustomizable ? 'none' : 'block';
    }
    const otherCategoryGroup = document.getElementById('pkgOtherCategoryGroup');
    const otherCategoryInput = document.getElementById('pkgOtherCategoryInput');
    if (otherCategoryGroup) {
        const showOtherCategory = !isCustomizable && serviceTypeSelect?.value === 'Other';
        otherCategoryGroup.style.display = showOtherCategory ? 'block' : 'none';
        if (otherCategoryInput) otherCategoryInput.required = showOtherCategory;
    }
    if (serviceTypeSelect) {
        serviceTypeSelect.required = !isCustomizable;
        if (isCustomizable && (!serviceTypeSelect.value || serviceTypeSelect.value === '')) {
            serviceTypeSelect.value = 'General';
        }
    }
    if (pricingModeGroup) {
        if (isCustomizable) {
            pricingModeGroup.classList.add('form-grid-full');
        } else {
            pricingModeGroup.classList.remove('form-grid-full');
        }
    }

    // 2. Package Pricing Details (Fixed package price, Per-pax rate, or Customizable starting price)
    const pricingCard = document.getElementById('pkgPricingCard');
    const priceInput = document.getElementById('pkgManualPriceInput');
    const minGuestsInput = document.querySelector('#packageForm [name="min_guests"]');
    const basePaxInput = document.querySelector('#packageForm [name="base_pax"]');
    const pricingLabelText = document.getElementById('pkgPricingLabelText');
    const pricingUnitHint = document.getElementById('pkgPriceUnitHint');
    const extraGuestRateInput = document.getElementById('pkgExtraGuestRate');
    const startingPriceFloor = Math.max(0, Number(window.CATERER_STARTING_PRICE) || 0);

    if (extraGuestRateInput) {
        extraGuestRateInput.min = String(startingPriceFloor);
        const currentExtraRate = Number(extraGuestRateInput.value) || 0;
        if (isFixed && currentExtraRate < startingPriceFloor) {
            extraGuestRateInput.value = String(startingPriceFloor);
        }
    }

    if (pricingCard) {
        pricingCard.style.display = 'block';
    }

    if (isCustomizable) {
        if (pricingLabelText) pricingLabelText.textContent = 'Starting price per guest (₱) *';
        if (pricingUnitHint) pricingUnitHint.textContent = 'Customers can choose options at this rate per guest.';
        if (priceInput) {
            priceInput.readOnly = false;
            priceInput.placeholder = 'e.g. 350.00';
            priceInput.required = true;
            if (previousMode === 'fixed' || !priceInput.value.trim() || priceInput.value === '0.00' || priceInput.value === '0') {
                const defaultStartingPrice = Number(window.CATERER_STARTING_PRICE) || 0;
                priceInput.value = defaultStartingPrice ? String(defaultStartingPrice) : '';
            }
        }
    } else if (mode === 'fixed') {
        if (pricingLabelText) pricingLabelText.textContent = 'Package price (base total) *';
        if (pricingUnitHint) pricingUnitHint.textContent = 'Included guests × Business Settings rate per guest.';
        if (priceInput) {
            priceInput.readOnly = true;
            priceInput.placeholder = '0.00';
            priceInput.required = true;
        }
    } else {
        if (pricingLabelText) pricingLabelText.textContent = 'Price per guest (₱) *';
        if (pricingUnitHint) pricingUnitHint.textContent = 'Charged for each guest included in this package.';
        if (priceInput) {
            priceInput.readOnly = false;
            priceInput.placeholder = '0.00';
            priceInput.required = true;
            if (priceInput.value === '0.00' || priceInput.value === '0') {
                priceInput.value = '';
            }
        }
    }

    // 3. Show/hide capacity sections
    document.querySelectorAll('.capacity-per-pax').forEach(el => el.style.display = isFixed ? 'none' : 'block');
    document.querySelectorAll('.capacity-fixed').forEach(el => el.style.display = isFixed ? 'block' : 'none');
    document.querySelectorAll('.capacity-additional').forEach(el => el.style.display = isFixed ? 'block' : 'none');
    const globalMinPax = Math.max(1, Number(window.CATERER_MIN_PAX) || 20);
    if (minGuestsInput) {
        minGuestsInput.min = String(globalMinPax);
        minGuestsInput.required = !isFixed;
    }
    if (basePaxInput) {
        basePaxInput.min = String(globalMinPax);
        basePaxInput.required = isFixed;
        basePaxInput.disabled = !isFixed;
        if (isFixed && !basePaxInput.value) basePaxInput.value = String(globalMinPax);
    }
    if (pricingModeSelect) pricingModeSelect.dataset.previousMode = mode;

    // 4. Step 2 sidebar title
    const sidebarTitle = document.getElementById('step2SidebarTitle');
    if (sidebarTitle) {
        sidebarTitle.innerText = isCustomizable ? '2. Customer Options' : '2. Package Inclusions';
    }
    const sidebarMobileTitle = document.getElementById('step2SidebarMobileTitle');
    if (sidebarMobileTitle) {
        sidebarMobileTitle.innerText = isCustomizable ? '2. Options' : '2. Inclusions';
    }

    // 5. Step 2 containers
    const fixedCont = document.getElementById('step2FixedContainer');
    const custCont = document.getElementById('step2CustomizableContainer');
    if (fixedCont) fixedCont.style.display = isCustomizable ? 'none' : 'block';
    if (custCont) custCont.style.display = isCustomizable ? 'flex' : 'none';

    const estContainer = document.getElementById('estStartingPriceContainer');
    if (estContainer) {
        estContainer.style.display = (isFixed || isCustomizable) ? 'none' : 'block';
    }

    if (isCustomizable) {
        if (window.fetchInclusionsCatalog) {
            window.fetchInclusionsCatalog().then(() => {
                if (typeof window.renderCustomizableCatalogs === 'function') {
                    window.renderCustomizableCatalogs();
                }
            });
        }
    }

    calculatePricing();
    updatePackageWizardControls();
};

window.openAddPackageModal = async function () {
    const form = document.getElementById('packageForm');
    if (!form) { console.error('[Packages] packageForm not found'); return; }

    const title = document.getElementById('packageModalTitle');
    if (title) title.innerText = 'Create a Package';

    form.action = '/caterer/packages/add';
    form.reset();

    const globalMinPax = Math.max(1, Number(window.CATERER_MIN_PAX) || 20);
    const startingPrice = Math.max(0, Number(window.CATERER_STARTING_PRICE) || 0);
    const serviceDuration = Math.min(24, Math.max(1, Number(window.CATERER_SERVICE_DURATION) || 4));
    if (form.min_guests) {
        form.min_guests.value = String(globalMinPax);
        form.min_guests.min = String(globalMinPax);
    }
    if (form.base_pax) {
        form.base_pax.value = String(globalMinPax);
        form.base_pax.min = String(globalMinPax);
    }
    if (form.service_duration) form.service_duration.value = String(serviceDuration);
    const defaultExcessGuestPrice = Math.max(startingPrice, Number(window.CATERER_DEFAULT_EXCESS_GUEST_PRICE) || 0);
    if (form.additional_guest_price) form.additional_guest_price.value = String(defaultExcessGuestPrice);
    if (form.additional_guest_price) form.additional_guest_price.min = String(startingPrice);
    if (form.price_per_head) form.price_per_head.value = '';
    const otherCategoryInput = document.getElementById('pkgOtherCategoryInput');
    const otherCategoryGroup = document.getElementById('pkgOtherCategoryGroup');
    if (otherCategoryInput) otherCategoryInput.value = '';
    if (otherCategoryGroup) otherCategoryGroup.style.display = 'none';
    window.clearTimeout(packageNameValidationTimer);
    packageNameValidationSequence++;
    setPackageNameValidation('idle');

    // Reset new fields to defaults
    if (form.pricing_mode) form.pricing_mode.value = 'fixed';
    const pricingModeSelect = document.getElementById('pkgPricingModeSelect');
    if (pricingModeSelect) pricingModeSelect.dataset.previousMode = 'fixed';
    if (form.status) form.status.value = 'active';

    window.togglePricingMode('fixed');

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

    // Reset customizable package state
    customizableMenuIds = new Set();
    customizableServiceIds = new Set();
    customizableEquipmentIds = new Set();
    customizableCategoryQuotas = {};
    lastMenuQuery = '';
    lastServiceQuery = '';
    const mSearch = document.getElementById('custMenuSearchInput');
    const sSearch = document.getElementById('custServiceSearchInput');
    if (mSearch) mSearch.value = '';
    if (sSearch) sSearch.value = '';

    // Reset wizard to Step 1 and open modal immediately
    const basicStepBtn = document.getElementById('step-btn-basic');
    if (typeof window.switchPackageTab === 'function') {
        window.switchPackageTab(basicStepBtn, 'basic');
    }
    safeOpenModal('packageModal');
    updatePackageWizardControls();

    // Fetch catalog upfront so menus, equipment, services are all immediately available
    if (window.fetchInclusionsCatalog) {
        window.fetchInclusionsCatalog().then(() => {
            if (typeof renderCustomizableCatalogs === 'function') renderCustomizableCatalogs();
            if (typeof syncCustomizableSelectionRules === 'function') syncCustomizableSelectionRules();
        }).catch(e => console.warn('[Packages] Catalog load error:', e));
    }

    // Load addon library in background (non-blocking)
    if (typeof loadPkgMenuLibrary === 'function') {
        loadPkgMenuLibrary().catch(e => console.warn('[Packages] Library load error (non-critical):', e));
    }
};

window.editPackage = async function (pkgId) {
    if (!pkgId) return;

    const title = document.getElementById('packageModalTitle');
    if (title) title.innerText = 'Edit Package';

    const form = document.getElementById('packageForm');
    if (form) form.action = `/caterer/packages/${pkgId}/update`;

    const basicStepBtn = document.getElementById('step-btn-basic');
    if (typeof window.switchPackageTab === 'function') {
        window.switchPackageTab(basicStepBtn, 'basic');
    }
    safeOpenModal('packageModal');

    try {
        if (window.fetchInclusionsCatalog) await window.fetchInclusionsCatalog();

        const response = await fetch(`/caterer/packages/${pkgId}/details`);
        if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);

        const pkg = await response.json();

        // Populate fields
        const nameInput = form.elements.namedItem('name');
        if (nameInput) nameInput.value = pkg.name || '';
        if (form.description) form.description.value = pkg.description || '';
        if (form.service_type) form.service_type.value = pkg.service_type || 'General';
        if (form.pricing_mode) form.pricing_mode.value = pkg.pricing_mode || 'fixed';
        const pricingModeSelect = document.getElementById('pkgPricingModeSelect');
        if (pricingModeSelect) pricingModeSelect.dataset.previousMode = form.pricing_mode.value;
        if (form.price_per_head) form.price_per_head.value = pkg.price_per_head ?? pkg.price ?? '';
        const globalMinPax = Math.max(1, Number(window.CATERER_MIN_PAX) || 20);
        if (form.min_guests) {
            form.min_guests.value = pkg.min_guests || globalMinPax;
            form.min_guests.min = String(globalMinPax);
        }
        if (form.base_pax) {
            form.base_pax.value = pkg.base_pax || globalMinPax;
            form.base_pax.min = String(globalMinPax);
        }
        if (form.service_duration) form.service_duration.value = pkg.service_duration || window.CATERER_SERVICE_DURATION || 4;
        if (form.additional_guest_price) {
            const rateFloor = Math.max(0, Number(window.CATERER_STARTING_PRICE) || 0);
            const savedExtraRate = Number(pkg.additional_guest_price ?? window.CATERER_DEFAULT_EXCESS_GUEST_PRICE) || 0;
            form.additional_guest_price.min = String(rateFloor);
            form.additional_guest_price.value = String(Math.max(savedExtraRate, rateFloor));
        }
        if (form.status) form.status.value = pkg.status || 'active';
        if (form.booking_lead_time) form.booking_lead_time.value = pkg.booking_lead_time || 7;

        if (pkg.policies) {
            if (form.policies_cancellation) form.policies_cancellation.value = pkg.policies.cancellation || '';
            if (form.policies_internal) form.policies_internal.value = pkg.policies.internal || '';
        }

        window.togglePricingMode(form.pricing_mode ? form.pricing_mode.value : 'fixed');
        schedulePackageNameValidation(pkg.name || '');
        const otherCategoryGroup = document.getElementById('pkgOtherCategoryGroup');
        if (otherCategoryGroup) otherCategoryGroup.style.display = 'none';

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
                        description: i.description || '',
                        image_url: i.image_url || ''
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

        // Load Customizable Package State
        customizableMenuIds = new Set();
        customizableServiceIds = new Set();
        customizableEquipmentIds = new Set();
        lastMenuQuery = '';
        lastServiceQuery = '';
        const mSearchEdit = document.getElementById('custMenuSearchInput');
        const sSearchEdit = document.getElementById('custServiceSearchInput');
        if (mSearchEdit) mSearchEdit.value = '';
        if (sSearchEdit) sSearchEdit.value = '';

        if (pkg.selection_rules) {
            let rules = pkg.selection_rules;
            if (typeof rules === 'string') {
                try { rules = JSON.parse(rules); } catch(e) { rules = {}; }
            }
            if (rules && typeof rules === 'object') {
                if (Array.isArray(rules.available_menu_ids)) {
                    rules.available_menu_ids.forEach(id => customizableMenuIds.add(Number(id)));
                }
                if (Array.isArray(rules.available_service_ids)) {
                    rules.available_service_ids.forEach(id => customizableServiceIds.add(Number(id)));
                }
                if (Array.isArray(rules.available_equipment_ids)) {
                    rules.available_equipment_ids.forEach(id => customizableEquipmentIds.add(Number(id)));
                }
                if (rules.category_quotas && typeof rules.category_quotas === 'object') {
                    customizableCategoryQuotas = Object.assign({}, rules.category_quotas);
                } else {
                    customizableCategoryQuotas = {};
                }
            }
        } else {
            customizableCategoryQuotas = {};
        }
        if (typeof renderCustomizableCatalogs === 'function') renderCustomizableCatalogs();
        if (typeof syncCustomizableSelectionRules === 'function') syncCustomizableSelectionRules();

        // Open modal immediately, load addon library in background
        const basicStepBtn = document.getElementById('step-btn-basic');
        if (typeof window.switchPackageTab === 'function') {
            window.switchPackageTab(basicStepBtn, 'basic');
        }
        safeOpenModal('packageModal');
        updatePackageWizardControls();

        if (typeof loadPkgMenuLibrary === 'function') {
            loadPkgMenuLibrary().catch(e => console.warn('[Packages] Library load error (non-critical):', e));
        }
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

    const modeInput = form.elements.namedItem('pricing_mode');
    const priceInput = form.elements.namedItem('price_per_head');
    const basePaxInput = form.elements.namedItem('base_pax');
    const minGuestsInput = form.elements.namedItem('min_guests');
    const mode = modeInput ? modeInput.value : 'per_pax';
    if (mode === 'fixed' && priceInput && basePaxInput) {
        const basePax = Number(basePaxInput.value);
        const startingPrice = Number(window.CATERER_STARTING_PRICE);
        const hasValidInputs = Number.isSafeInteger(basePax) && basePax > 0
            && Number.isFinite(startingPrice) && startingPrice > 0;
        const total = hasValidInputs
            ? Math.round((basePax * startingPrice + Number.EPSILON) * 100) / 100
            : 0;
        priceInput.value = total > 0
            ? total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
            : '';
        if (minGuestsInput) minGuestsInput.value = hasValidInputs ? String(basePax) : '';
        const priceHelp = document.getElementById('pkgPriceHelp');
        if (priceHelp) {
            const formattedRate = Number.isFinite(startingPrice) && startingPrice > 0
                ? startingPrice.toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                : 'not set';
            const formattedTotal = total > 0
                ? total.toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                : 'not available';
            priceHelp.textContent = `Base total = ${hasValidInputs ? basePax : 'valid included guests'} × ₱${formattedRate} per guest = ₱${formattedTotal}. Extra guest rate is charged separately for guests above the included count.`;
        }
    }
    const rawPrice = String(priceInput?.value || '').replace(/,/g, '');
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
        const minGuests = parseInt(minGuestsInput?.value || '', 10) || 0;
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
    updatePackageWizardControls();
}

// Attach event listeners for price calculation and form submission
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('packageForm');
    if (form) {
        const nameInput = document.getElementById('pkgNameInput');
        const categorySelect = document.getElementById('pkgServiceTypeSelect');
        const otherCategoryInput = document.getElementById('pkgOtherCategoryInput');
        const otherCategoryGroup = document.getElementById('pkgOtherCategoryGroup');
        document.querySelectorAll('#packageModal .pkg-step-side').forEach(stepButton => {
            stepButton.addEventListener('keydown', event => {
                if ((event.key === 'Enter' || event.key === ' ') && stepButton.getAttribute('aria-disabled') !== 'true') {
                    event.preventDefault();
                    const stepName = stepButton.id.replace('step-btn-', '');
                    window.switchPackageTab(stepButton, stepName);
                }
            });
        });
        if (nameInput) {
            nameInput.addEventListener('input', () => schedulePackageNameValidation(nameInput.value));
        }
        if (categorySelect) {
            categorySelect.addEventListener('change', () => {
                const showOther = categorySelect.value === 'Other';
                if (otherCategoryGroup) otherCategoryGroup.style.display = showOther ? 'block' : 'none';
                if (otherCategoryInput) otherCategoryInput.required = showOther;
                updatePackageWizardControls();
            });
        }
        if (otherCategoryInput) {
            otherCategoryInput.addEventListener('input', updatePackageWizardControls);
        }
        form.querySelectorAll('input, select, textarea').forEach(field => {
            field.addEventListener('input', updatePackageWizardControls);
            field.addEventListener('change', updatePackageWizardControls);
        });
        if (form.price_per_head) form.price_per_head.addEventListener('input', calculatePricing);
        const basePaxInput = form.elements.namedItem('base_pax');
        const extraGuestRateInput = form.elements.namedItem('additional_guest_price');
        if (basePaxInput) {
            ['input', 'change'].forEach(eventName => basePaxInput.addEventListener(eventName, calculatePricing));
        }
        if (extraGuestRateInput) {
            ['input', 'change'].forEach(eventName => extraGuestRateInput.addEventListener(eventName, () => {
                updatePackageWizardControls();
                if (document.querySelector('.pkg-step-side.active')?.id === 'step-btn-review') updateReviewTab();
            }));
        }
        if (form.elements.namedItem('min_guests')) form.elements.namedItem('min_guests').addEventListener('input', calculatePricing);
        const helpTriggers = document.querySelectorAll('#packageModal .pkg-help-trigger');
        helpTriggers.forEach(trigger => {
            trigger.addEventListener('click', event => {
                event.preventDefault();
                event.stopPropagation();
                const help = document.getElementById(trigger.getAttribute('aria-controls'));
                const shouldOpen = trigger.getAttribute('aria-expanded') !== 'true';
                helpTriggers.forEach(other => {
                    other.setAttribute('aria-expanded', 'false');
                    const otherHelp = document.getElementById(other.getAttribute('aria-controls'));
                    if (otherHelp) otherHelp.hidden = true;
                });
                if (help) help.hidden = !shouldOpen;
                trigger.setAttribute('aria-expanded', String(shouldOpen));
            });
        });
        document.addEventListener('click', event => {
            if (event.target.closest('#packageModal .pkg-help-trigger, #packageModal .pkg-field-help')) return;
            helpTriggers.forEach(trigger => {
                trigger.setAttribute('aria-expanded', 'false');
                const help = document.getElementById(trigger.getAttribute('aria-controls'));
                if (help) help.hidden = true;
            });
        });
        document.addEventListener('keydown', event => {
            if (event.key !== 'Escape') return;
            helpTriggers.forEach(trigger => {
                trigger.setAttribute('aria-expanded', 'false');
                const help = document.getElementById(trigger.getAttribute('aria-controls'));
                if (help) help.hidden = true;
            });
        });

        // Guarantee inclusions and customizable selection rules are serialized right before form submit
        form.addEventListener('submit', (event) => {
            if (!packageStepIsReady('review')) {
                event.preventDefault();
                const activeStep = document.querySelector('.pkg-step-side.active');
                const step = activeStep ? activeStep.id.replace('step-btn-', '') : 'basic';
                validateTab(step);
                updatePackageWizardControls();
                return;
            }
            if (categorySelect && categorySelect.value === 'Other' && otherCategoryInput) {
                const category = otherCategoryInput.value.trim();
                let option = Array.from(categorySelect.options).find(item => item.value.toLowerCase() === category.toLowerCase());
                if (!option) {
                    option = new Option(category, category);
                    categorySelect.add(option);
                }
                categorySelect.value = option.value;
            }
            syncInclusionsHidden();
            if (typeof syncCustomizableSelectionRules === 'function') {
                syncCustomizableSelectionRules();
            }
        });
    }
});

// Dynamic Wizard Navigation
window.STEPS_ORDER = STEPS_ORDER;

window.switchPackageTab = function (el, tabName) {
    if (!tabName) tabName = 'basic';

    const steps = window.STEPS_ORDER || ['basic', 'inclusions', 'review'];
    const targetIdx = steps.indexOf(tabName);
    const activeStepEl = document.querySelector('.pkg-step-side.active');
    const currentTabName = activeStepEl ? activeStepEl.id.replace('step-btn-', '') : 'basic';
    const currentIdx = steps.indexOf(currentTabName);

    // Validate forward movement
    if (targetIdx > currentIdx && currentIdx >= 0) {
        for (let i = currentIdx; i < targetIdx; i++) {
            if (typeof validateTab === 'function' && !validateTab(steps[i])) {
                const failEl = document.getElementById('step-btn-' + steps[i]);
                if (failEl) {
                    document.querySelectorAll('.pkg-step-side').forEach(s => s.classList.remove('active'));
                    failEl.classList.add('active');
                }
                return;
            }
        }
    }

    document.querySelectorAll('.pkg-step-side').forEach(s => s.classList.remove('active'));
    if (el) {
        el.classList.add('active');
    } else {
        const targetBtn = document.getElementById('step-btn-' + tabName);
        if (targetBtn) targetBtn.classList.add('active');
    }

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
        const safeIdx = targetIdx >= 0 ? targetIdx : 0;
        const pct = ((safeIdx + 1) / steps.length) * 100;
        progressEl.style.width = pct + '%';
    }

    // Navigation Buttons
    const btnBack = document.getElementById('btnWizardBack');
    const btnNext = document.getElementById('btnWizardNext');
    const btnSave = document.getElementById('pkgSaveBtn');

    if (btnBack) {
        if (targetIdx > 0) {
            btnBack.style.setProperty('display', 'inline-flex', 'important');
        } else {
            btnBack.style.setProperty('display', 'none', 'important');
        }
    }

    if (targetIdx === steps.length - 1) {
        if (btnNext) btnNext.style.setProperty('display', 'none', 'important');
        if (btnSave) btnSave.style.setProperty('display', 'inline-flex', 'important');
        if (typeof updateReviewTab === 'function') updateReviewTab();
    } else {
        if (btnNext) btnNext.style.setProperty('display', 'inline-flex', 'important');
        if (btnSave) btnSave.style.setProperty('display', 'none', 'important');
    }
    updatePackageWizardControls();
};

window.goToWizardNextStep = function () {
    const steps = window.STEPS_ORDER || ['basic', 'inclusions', 'review'];
    const activeStepEl = document.querySelector('.pkg-step-side.active');
    if (!activeStepEl) {
        window.switchPackageTab(document.getElementById('step-btn-inclusions'), 'inclusions');
        return;
    }
    const currentTabName = activeStepEl.id.replace('step-btn-', '');
    const currentIdx = steps.indexOf(currentTabName);
    if (currentIdx < steps.length - 1) {
        const nextTab = steps[currentIdx + 1];
        window.switchPackageTab(document.getElementById('step-btn-' + nextTab), nextTab);
    }
};

window.goToWizardBackStep = function () {
    const steps = window.STEPS_ORDER || ['basic', 'inclusions', 'review'];
    const activeStepEl = document.querySelector('.pkg-step-side.active');
    if (!activeStepEl) return;
    const currentTabName = activeStepEl.id.replace('step-btn-', '');
    const currentIdx = steps.indexOf(currentTabName);
    if (currentIdx > 0) {
        const prevTab = steps[currentIdx - 1];
        window.switchPackageTab(document.getElementById('step-btn-' + prevTab), prevTab);
    }
};

function validateTab(tabName) {
    const form = document.getElementById('packageForm');
    if (!form) return true;

    let isValid = true;

    // Clear old errors
    document.querySelectorAll('#packageModal .inline-error-badge').forEach(b => b.remove());
    document.querySelectorAll('#packageModal .control-pro').forEach(c => c.style.borderColor = '');

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
        const nameInput = form.elements.namedItem('name');
        const nameVal = nameInput ? nameInput.value.trim() : '';
        if (!nameVal) addError(nameInput, "Package Name is required.");
        else if (packageNameValidationStatus !== 'valid') {
            const nameMessage = packageNameValidationStatus === 'duplicate'
                ? 'Choose a different package name.'
                : packageNameValidationStatus === 'error'
                    ? 'Package name could not be verified. Please try again.'
                    : 'Wait for package name validation to finish.';
            addError(nameInput, nameMessage);
        }

        const mode = form.pricing_mode ? form.pricing_mode.value : 'fixed';
        if (mode !== 'customizable' && form.service_type?.value === 'Other') {
            const otherCategoryInput = document.getElementById('pkgOtherCategoryInput');
            if (!otherCategoryInput || !otherCategoryInput.value.trim()) {
                addError(otherCategoryInput, 'Enter the specific category name.');
            }
        }
        const globalMinPax = Math.max(1, Number(window.CATERER_MIN_PAX) || 20);
        const durationInput = form.elements.namedItem('service_duration');
        const duration = Number(durationInput?.value);
        if (!Number.isInteger(duration) || duration < 1 || duration > 24) addError(durationInput, 'Enter a service duration from 1 to 24 hours.');
        if (mode === 'per_pax' || mode === 'customizable') {
            const minG = parseInt(form.min_guests.value);
            if (isNaN(minG) || minG < globalMinPax) addError(form.min_guests, `Minimum guests must be at least ${globalMinPax}.`);
        } else if (mode === 'fixed') {
            const basePax = parseInt(form.base_pax?.value, 10);
            if (!Number.isInteger(basePax) || basePax < globalMinPax) addError(form.base_pax, `Package guest count must be at least ${globalMinPax}.`);
        }

        if (mode === 'customizable') {
            if (form.price_per_head) {
                const rawPrice = (form.price_per_head.value || '').replace(/,/g, '');
                const price = parseFloat(rawPrice);
                if (!rawPrice.trim() || !Number.isFinite(price) || price <= 0) {
                    addError(form.price_per_head, "Enter a starting price greater than ₱0.");
                }
            }
        } else {
            if (form.price_per_head) {
                const rawPrice = (form.price_per_head.value || '').replace(/,/g, '');
                const price = parseFloat(rawPrice);
                if (isNaN(price) || price <= 0) {
                    addError(form.price_per_head, Number(window.CATERER_STARTING_PRICE) > 0
                        ? "Enter a valid base guest count to calculate the package total."
                        : "Set a starting price above ₱0 in Business Settings to calculate this package total.");
                }
            }

        }
    }

    if (tabName === 'inclusions') {
        const mode = form.pricing_mode ? form.pricing_mode.value : 'fixed';
        if (mode === 'customizable') {
            const total = customizableMenuIds.size + customizableServiceIds.size + customizableEquipmentIds.size;
            if (total === 0) {
                alert("Please select at least one menu item or service for customers to choose from.");
                return false;
            }
        } else if (packageInclusions.length === 0) {
            alert('Add at least one inclusion to this package before continuing.');
            return false;
        }
    }

    return isValid;
}

function packageStepIsReady(tabName) {
    const form = document.getElementById('packageForm');
    if (!form) return false;
    const value = name => String(form.elements.namedItem(name)?.value || '').trim();
    const mode = value('pricing_mode') || 'fixed';
    const globalMinPax = Math.max(1, Number(window.CATERER_MIN_PAX) || 20);

    if (tabName === 'basic') {
        const rawPrice = value('price_per_head').replace(/,/g, '');
        const price = Number(rawPrice);
        const duration = Number(value('service_duration'));
        const categoryOkay = mode === 'customizable' || (
            Boolean(value('service_type')) &&
            (value('service_type') !== 'Other' || Boolean(document.getElementById('pkgOtherCategoryInput')?.value.trim()))
        );
        const capacity = mode === 'fixed'
            ? Number(value('base_pax')) >= globalMinPax
            : Number(value('min_guests')) >= globalMinPax;
        return Boolean(value('name')) && packageNameValidationStatus === 'valid' && categoryOkay
            && Number.isInteger(duration) && duration >= 1 && duration <= 24
            && Boolean(rawPrice) && Number.isFinite(price) && price > 0
            && capacity;
    }

    if (tabName === 'inclusions') {
        if (mode !== 'customizable') return packageInclusions.length > 0;

        const hasOptions = customizableMenuIds.size + customizableServiceIds.size + customizableEquipmentIds.size > 0;
        const categoryCounts = getCustomizableMenuCategoryCounts();
        const quotasReady = Object.entries(categoryCounts).every(([cat, available]) => {
            const quota = Number(customizableCategoryQuotas[cat]);
            return Number.isInteger(quota) && quota >= 1 && quota <= available;
        });
        return hasOptions && quotasReady;
    }

    return packageStepIsReady('basic') && packageStepIsReady('inclusions');
}

function updatePackageWizardControls() {
    const active = document.querySelector('.pkg-step-side.active');
    const step = active ? active.id.replace('step-btn-', '') : 'basic';
    const next = document.getElementById('btnWizardNext');
    const save = document.getElementById('pkgSaveBtn');
    if (next) next.disabled = !packageStepIsReady(step);
    if (save) save.disabled = !packageStepIsReady('review');

    (window.STEPS_ORDER || ['basic', 'inclusions', 'review']).forEach((name, index, steps) => {
        const stepButton = document.getElementById(`step-btn-${name}`);
        if (!stepButton) return;
        const enabled = index === 0 || steps.slice(0, index).every(packageStepIsReady);
        stepButton.setAttribute('aria-disabled', String(!enabled));
        stepButton.tabIndex = enabled ? 0 : -1;
    });
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
    const dCapLabel = document.getElementById('reviewCapacityLabel');
    const dPrice = document.getElementById('reviewPrice');
    const priceFormula = document.getElementById('reviewPriceFormula');
    const dDuration = document.getElementById('reviewDuration');
    const dStatus = document.getElementById('reviewStatus');
    const descriptionRow = document.getElementById('reviewDescriptionRow');
    const dDescription = document.getElementById('reviewDescription');

    const nameInput = form.elements.namedItem('name');
    if (dName) dName.innerText = (nameInput && nameInput.value) || 'Untitled Package';

    const mode = form.pricing_mode ? form.pricing_mode.value : 'fixed';

    const catRow = document.getElementById('reviewCategoryRow');
    if (catRow) {
        catRow.style.display = (mode === 'customizable') ? 'none' : 'block';
    }

    let catText = 'General';
    if (form.service_type) {
        const opt = form.service_type.options[form.service_type.selectedIndex];
        catText = opt ? opt.text : form.service_type.value;
    }
    if (form.service_type?.value === 'Other') {
        catText = document.getElementById('pkgOtherCategoryInput')?.value.trim() || 'Other';
    }
    if (dType) dType.innerText = catText;

    if (dMode) {
        if (mode === 'customizable') dMode.innerText = 'Customizable Package';
        else if (mode === 'fixed') dMode.innerText = 'Fixed Package';
        else dMode.innerText = 'Per Pax';
    }
    if (dDuration) dDuration.innerText = `${form.service_duration?.value || '—'} hours`;
    if (dStatus && form.status) {
        dStatus.innerText = form.status.options[form.status.selectedIndex]?.text || form.status.value;
    }
    const description = String(form.description?.value || '').trim();
    if (descriptionRow) descriptionRow.style.display = description ? 'block' : 'none';
    if (dDescription) dDescription.innerText = description;

    if (dCap) {
        const excessRow = document.getElementById('reviewExcessRow');
        const excessRate = document.getElementById('reviewExcessRate');

        if (mode === 'customizable' || mode === 'per_pax') {
            const minVal = form.min_guests ? form.min_guests.value : 50;
            const max = form.max_guests && form.max_guests.value ? ` to ${form.max_guests.value}` : '+';
            dCap.innerText = `${minVal || 0}${max} Guests`;
            if (excessRow) excessRow.style.display = 'none';
        } else {
            dCap.innerText = form.base_pax && form.base_pax.value ? `${form.base_pax.value} guests included` : 'N/A';
            if (excessRow && form.additional_guest_price && form.additional_guest_price.value) {
                excessRow.style.display = 'block';
                excessRate.innerText = `₱${Number(form.additional_guest_price.value).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} per extra guest`;
            } else if (excessRow) {
                excessRow.style.display = 'none';
            }
        }
        if (dCapLabel) dCapLabel.innerText = mode === 'fixed' ? 'Included guests:' : 'Minimum guests:';
    }

    if (dPrice) {
        const val = form.price_per_head ? (form.price_per_head.value || '0') : '0';
        if (mode === 'customizable') {
            dPrice.innerHTML = `<span style="color: #0f172a; font-weight: 800; font-size: 1.05rem;">Starting at ₱${val}</span><div style="font-size: 0.72rem; color: #16a34a; font-weight: 600; margin-top: 2px;">+ Customizable choices calculated per customer selection</div>`;
        } else if (mode === 'fixed') {
            dPrice.innerText = `₱${val} base total`;
            if (priceFormula) {
                const basePax = Number(form.base_pax?.value) || 0;
                const rate = Number(window.CATERER_STARTING_PRICE) || 0;
                priceFormula.innerText = `${basePax} included guests × ₱${rate.toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} per guest. Extra guests are charged separately.`;
            }
        } else {
            dPrice.innerText = `₱${val} / pax`;
        }
        if (mode !== 'fixed' && priceFormula) priceFormula.innerText = '';
    }

    // Toggle Review Blocks
    const fixedReview = document.getElementById('reviewFixedPackageBlock');
    const custReview = document.getElementById('reviewCustomizablePackageBlock');

    try {
        if (mode === 'customizable') {
            if (fixedReview) fixedReview.style.display = 'none';
            if (custReview) custReview.style.display = 'flex';
            if (typeof renderReviewCustomizable === 'function') {
                renderReviewCustomizable();
            }
        } else {
            if (fixedReview) fixedReview.style.display = 'block';
            if (custReview) custReview.style.display = 'none';

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
                    html += `<div class="review-inclusion-group" style="margin-bottom:0.75rem;"><div class="review-inclusion-group-title" style="font-size:0.75rem;font-weight:800;color:#64748b;text-transform:uppercase;margin-bottom:0.35rem;">${catIcons[cat] || '•'} ${cat}</div>`;
                    html += items.map(i => `<div class="review-inclusion-summary-item" style="font-size:0.85rem;color:#1e293b;display:flex;gap:6px;align-items:flex-start;margin-bottom:4px;"><i class="fas fa-check-circle" style="color:#16a34a;margin-top:3px;flex-shrink:0;"></i><span><strong>${escapeHtml(i.name)}</strong>${i.description ? '<br><span style="color:#64748b;font-size:0.78rem;">' + escapeHtml(i.description) + '</span>' : ''}</span></div>`).join('');
                    html += '</div>';
                }
                reviewInclusionsDetail.innerHTML = html;
            }
        }
        }
    } catch (err) {
        console.error("updateReviewTab error:", err);
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

        if (typeof updateSelectionRulesBuilder === 'function') {
            updateSelectionRulesBuilder();
        }
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
// ===== Inclusion photo upload state/helpers =====
let inclusionImageFile = null;      // newly picked file, uploaded on save
let inclusionCurrentImage = '';     // image already stored on the inclusion/catalog item

function setInclusionPhotoPreview(src) {
    const box = document.getElementById('inclusionPhotoPreview');
    if (!box) return;
    if (src) {
        box.innerHTML = `<img src="${escapeHtml(src)}" alt="" style="width:100%;height:100%;object-fit:cover;" onerror="this.remove();">`;
        box.style.border = '1.5px solid #e2e8f0';
    } else {
        box.innerHTML = '';
        box.style.border = '1.5px dashed #cbd5e1';
    }
}

function resetInclusionImagePicker(currentImage = '') {
    inclusionImageFile = null;
    inclusionCurrentImage = currentImage || '';
    const input = document.getElementById('inclusionImageInput');
    if (input) input.value = '';
    const clearBtn = document.getElementById('btnInclusionPhotoClear');
    if (clearBtn) clearBtn.style.display = 'none';
    const hint = document.getElementById('inclusionPhotoHint');
    if (hint) hint.textContent = inclusionCurrentImage
        ? 'Current photo shown. Upload a new one to replace it.'
        : `JPG or PNG. Maximum size: ${Number(window.MAX_UPLOAD_SIZE_MB) || 5}MB.`;
    setInclusionPhotoPreview(inclusionCurrentImage);
}
window.resetInclusionImagePicker = resetInclusionImagePicker;

window.triggerInclusionImagePicker = function () {
    const input = document.getElementById('inclusionImageInput');
    if (input) input.click();
};

window.handleInclusionImageChange = function (event) {
    const input = event && event.target ? event.target : document.getElementById('inclusionImageInput');
    const file = input && input.files && input.files[0] ? input.files[0] : null;
    const hint = document.getElementById('inclusionPhotoHint');
    if (!file) return;

    const extension = (file.name.split('.').pop() || '').toLowerCase();
    if (!['jpg', 'jpeg', 'png'].includes(extension) || (file.type && !['image/jpeg', 'image/png'].includes(file.type))) {
        if (hint) { hint.textContent = 'Please choose a JPG, JPEG, or PNG image.'; hint.style.color = '#dc2626'; }
        input.value = '';
        return;
    }
    const maxSizeMb = Number(window.MAX_UPLOAD_SIZE_MB) || 5;
    if (file.size > maxSizeMb * 1024 * 1024) {
        if (hint) { hint.textContent = `Image is too large. Maximum size is ${maxSizeMb}MB.`; hint.style.color = '#dc2626'; }
        input.value = '';
        return;
    }

    inclusionImageFile = file;
    const reader = new FileReader();
    reader.onload = e => setInclusionPhotoPreview(e.target.result);
    reader.readAsDataURL(file);

    if (hint) { hint.textContent = `Selected: ${file.name} — will be saved with this inclusion.`; hint.style.color = '#15803d'; }
    const clearBtn = document.getElementById('btnInclusionPhotoClear');
    if (clearBtn) clearBtn.style.display = 'inline-flex';
};

window.clearInclusionImageSelection = function () {
    const hint = document.getElementById('inclusionPhotoHint');
    if (hint) hint.style.color = '#64748b';
    resetInclusionImagePicker(inclusionCurrentImage);
};

// Find the stored photo of a catalog item
function findCatalogImage(type, itemId, name) {
    const key = (type === 'Service') ? 'service' : ((type === 'Equipment') ? 'equipment' : 'menu');
    const catalog = (window.inclusionsCatalog && window.inclusionsCatalog[key]) || [];
    let found = null;
    if (itemId) found = catalog.find(c => Number(c.id) === Number(itemId));
    if (!found && name) found = catalog.find(c => String(c.name || '').toLowerCase() === String(name).toLowerCase());
    return (found && found.image_url) || '';
}

function setInclusionCategoryChoices(includeEquipment = false) {
    const select = document.getElementById('customInclusionCategory');
    if (!select) return;
    const equipmentOption = Array.from(select.options).find(option => option.value === 'Equipment');
    if (includeEquipment && !equipmentOption) {
        select.add(new Option('Equipment', 'Equipment'));
    } else if (!includeEquipment && equipmentOption) {
        equipmentOption.remove();
    }
}

// Persist the picked photo onto the linked catalog item
async function uploadInclusionImage(type, itemId) {
    const apiType = (type === 'Service') ? 'service' : ((type === 'Equipment') ? 'equipment' : 'menu');
    const formData = new FormData();
    formData.append('image', inclusionImageFile);

    const res = await fetch(`/caterer/api/catalogs/item-image/${apiType}/${itemId}`, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: formData
    });
    let data = {};
    try { data = await res.json(); } catch (e) { data = {}; }
    if (!res.ok) throw new Error(extractErrorMessage(data, 'Failed to upload the photo.'));

    const imageUrl = data.image_url || '';
    // Keep the in-memory catalog in sync so other inclusions show the new photo
    const key = (type === 'Service') ? 'service' : ((type === 'Equipment') ? 'equipment' : 'menu');
    const catalog = (window.inclusionsCatalog && window.inclusionsCatalog[key]) || [];
    const entry = catalog.find(c => Number(c.id) === Number(itemId));
    if (entry) entry.image_url = imageUrl;
    return imageUrl;
}

window.openAddInclusionModal = async function () {
    const editIndexEl = document.getElementById('customInclusionEditIndex');
    const title = document.getElementById('inclusionModalTitle');
    const subtitle = document.getElementById('inclusionModalSubtitle');
    const btnAddAnother = document.getElementById('btnInclusionSaveAddAnother');
    const btnDoneText = document.getElementById('btnInclusionSaveDoneText');
    const alertBox = document.getElementById('addInclusionSuccessAlert');
    const desc = document.getElementById('customInclusionDescription');
    const itemSelect = document.getElementById('inclusionItemSelect');
    const searchInput = document.getElementById('inclusionItemSearch');
    const selectedBanner = document.getElementById('selectedItemInfoBanner');

    if (editIndexEl) editIndexEl.value = '-1';
    if (title) title.innerText = 'Quick Add Inclusion';
    if (subtitle) subtitle.innerText = 'Add a food item or service to your fixed package.';
    if (btnAddAnother) btnAddAnother.hidden = true;
    if (btnDoneText) btnDoneText.innerText = 'Save & Select';
    const doneButton = document.getElementById('btnInclusionSaveDone');
    if (doneButton) {
        doneButton.disabled = true;
        doneButton.hidden = true;
    }
    if (alertBox) { alertBox.style.display = 'none'; alertBox.innerText = ''; }
    if (desc) desc.value = '';
    if (itemSelect) itemSelect.innerHTML = '<option value="" selected disabled>Select a catalog item</option>';
    if (searchInput) searchInput.value = '';
    if (selectedBanner) selectedBanner.style.display = 'none';
    resetInclusionImagePicker('');

    // Ensure catalog is populated across all item types
    if (!window.inclusionsCatalog || !window.inclusionsCatalog.equipment || !window.inclusionsCatalog.menu || !window.inclusionsCatalog.service) {
        await window.fetchInclusionsCatalog();
    }

    // Start with only the requested choices; legacy equipment inclusions remain editable.
    setInclusionCategoryChoices(false);
    const catSelect = document.getElementById('customInclusionCategory');
    if (catSelect) catSelect.value = '';

    window.handleInclusionTypeChange('');

    safeOpenModal('addInclusionModal', true);
    setTimeout(() => {
        const searchInput = document.getElementById('inclusionItemSearch');
        if (searchInput) searchInput.focus();
    }, 120);
};

// Handle Inclusion Type change (Equipment | Menu | Service)
window.handleInclusionTypeChange = function (type, preselectId = null) {
    const normType = (type === 'Menu / Food' || type === 'Menu') ? 'Menu' : (type === 'Service' ? 'Service' : (type === 'Equipment' ? 'Equipment' : ''));
    const select = document.getElementById('inclusionItemSelect');
    const catSelect = document.getElementById('customInclusionCategory');
    if (catSelect && catSelect.value !== normType) {
        catSelect.value = normType;
    }

    const lblItem = document.getElementById('lblInclusionItem');
    const btnCreateText = document.getElementById('btnCreateNewCatalogItemText');
    const btnCreateCatalog = document.getElementById('btnCreateNewCatalogItem');
    const searchInput = document.getElementById('inclusionItemSearch');
    const banner = document.getElementById('selectedItemInfoBanner');
    const catalogSection = document.querySelector('#addInclusionModal .inclusion-catalog-section');
    const descriptionSection = document.querySelector('#addInclusionModal .inclusion-description-section');
    const photoSection = document.querySelector('#addInclusionModal .inclusion-photo-section');
    const infoAlert = document.querySelector('#addInclusionModal .inclusion-info-alert');
    const btnAddAnother = document.getElementById('btnInclusionSaveAddAnother');
    const doneButton = document.getElementById('btnInclusionSaveDone');
    const doneText = document.getElementById('btnInclusionSaveDoneText');

    if (!normType) {
        if (catalogSection) catalogSection.style.display = 'none';
        if (descriptionSection) descriptionSection.style.display = 'none';
        if (photoSection) photoSection.style.display = 'none';
        if (infoAlert) infoAlert.style.display = 'none';
        if (btnAddAnother) btnAddAnother.hidden = true;
        if (doneButton) {
            doneButton.disabled = true;
            doneButton.hidden = true;
        }
        if (doneText) doneText.innerText = 'Save & Select';
        if (banner) banner.style.display = 'none';
        const itemIdEl = document.getElementById('customInclusionItemId');
        const nameEl = document.getElementById('customInclusionName');
        if (itemIdEl) itemIdEl.value = '';
        if (nameEl) nameEl.value = '';
        if (select) select.innerHTML = '<option value="" selected disabled>Select a catalog item</option>';
        if (!inclusionImageFile) resetInclusionImagePicker('');
        return;
    }
    if (catalogSection) catalogSection.style.display = 'block';
    if (catalogSection) catalogSection.style.display = 'block';
    if (descriptionSection) descriptionSection.style.display = 'block';
    if (photoSection) photoSection.style.display = 'block';
    if (infoAlert) infoAlert.style.display = 'flex';
    if (btnAddAnother) btnAddAnother.hidden = false;
    if (doneButton) {
        doneButton.disabled = false;
        doneButton.hidden = false;
    }
    if (doneText) doneText.innerText = 'Add Inclusion';

    // Update UI text and placeholders
    if (lblItem) lblItem.innerHTML = `${normType} <span style="color: #ef4444;">*</span>`;
    if (btnCreateText) btnCreateText.innerText = 'Create new';
    if (btnCreateCatalog) btnCreateCatalog.style.display = normType === 'Equipment' ? 'none' : 'inline-flex';
    if (searchInput) {
        searchInput.placeholder = `Type to filter ${normType.toLowerCase()} catalog...`;
        searchInput.value = '';
    }

    if (banner) banner.style.display = 'none';
    const itemIdEl = document.getElementById('customInclusionItemId');
    const nameEl = document.getElementById('customInclusionName');
    if (itemIdEl) itemIdEl.value = '';
    if (nameEl) nameEl.value = '';
    resetInclusionImagePicker('');

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

    let html = `<option value="" selected disabled>Select a ${type.toLowerCase()} item</option>`;
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
    const type = catSelect ? catSelect.value : '';
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

    if (!selectedId || !select) {
        if (banner) banner.style.display = 'none';
        if (itemIdEl) itemIdEl.value = '';
        if (nameEl) nameEl.value = '';
        if (!inclusionImageFile) resetInclusionImagePicker('');
        return;
    }

    const opt = select.options[select.selectedIndex];
    if (!opt || !opt.dataset.name) return;

    const itemName = opt.dataset.name;
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

    const catSelect = document.getElementById('customInclusionCategory');
    const currentType = catSelect ? catSelect.value : 'Equipment';

    select.style.borderColor = '';
    // Show the catalog item's existing photo unless the user already picked a new one
    if (!inclusionImageFile) {
        resetInclusionImagePicker(findCatalogImage(currentType, selectedId, itemName));
    }
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

    if (editIndexEl) editIndexEl.value = String(index);
    if (title) title.innerText = 'Edit Package Inclusion';
    if (subtitle) subtitle.innerText = 'Update the details of this package inclusion.';
    if (btnAddAnother) btnAddAnother.hidden = true;
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

    window.handleInclusionTypeChange(itemType, item.item_id);
    if (btnAddAnother) btnAddAnother.hidden = true;

    // If item_id wasn't in catalog yet, set name manually
    const nameEl = document.getElementById('customInclusionName');
    if (nameEl) nameEl.value = item.name || '';

    setInclusionCategoryChoices(itemType === 'Equipment');
    resetInclusionImagePicker(item.image_url || findCatalogImage(itemType, item.item_id, item.name));

    safeOpenModal('addInclusionModal', true);
};

// Close Modal
window.closeAddInclusionModal = function () {
    safeCloseModal('addInclusionModal');
};

// Save Inclusion (Add or Edit)
window.saveInclusion = async function (addAnother = false) {
    const editIndexEl = document.getElementById('customInclusionEditIndex');
    const catSelect = document.getElementById('customInclusionCategory');
    const select = document.getElementById('inclusionItemSelect');
    const itemIdEl = document.getElementById('customInclusionItemId');
    const nameEl = document.getElementById('customInclusionName');
    const descEl = document.getElementById('customInclusionDescription');
    const alertBox = document.getElementById('addInclusionSuccessAlert');

    const selectedType = catSelect ? catSelect.value : 'Equipment';
    if (!['Menu', 'Service', 'Equipment'].includes(selectedType)) {
        if (catSelect) catSelect.focus();
        return;
    }
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

    const descVal = descEl ? descEl.value.trim() : '';

    const categoryVal = selectedType === 'Menu' ? 'Menu / Food' : selectedType;

    // Upload the picked photo (stored on the linked catalog item)
    let imageUrl = inclusionCurrentImage || '';
    if (inclusionImageFile) {
        if (!itemId) {
            const hint = document.getElementById('inclusionPhotoHint');
            if (hint) { hint.textContent = 'Select a catalog item first so the photo can be saved.'; hint.style.color = '#dc2626'; }
            return;
        }
        const saveBtns = [document.getElementById('btnInclusionSaveDone'), document.getElementById('btnInclusionSaveAddAnother')].filter(Boolean);
        const hint = document.getElementById('inclusionPhotoHint');
        saveBtns.forEach(b => { b.disabled = true; b.style.opacity = '0.6'; });
        if (hint) { hint.textContent = 'Uploading photo...'; hint.style.color = '#64748b'; }
        try {
            imageUrl = await uploadInclusionImage(selectedType, parseInt(itemId, 10));
            inclusionImageFile = null;
            inclusionCurrentImage = imageUrl;
        } catch (err) {
            if (hint) { hint.textContent = (err && err.message) || 'Failed to upload the photo.'; hint.style.color = '#dc2626'; }
            return;
        } finally {
            saveBtns.forEach(b => { b.disabled = false; b.style.opacity = '1'; });
        }
    }

    const itemObj = {
        type: selectedType,
        category: categoryVal,
        item_id: itemId ? parseInt(itemId, 10) : null,
        name: nameVal,
        description: descVal,
        image_url: imageUrl
    };

    const editIndex = editIndexEl ? parseInt(editIndexEl.value, 10) : -1;

    if (editIndex >= 0 && editIndex < packageInclusions.length) {
        // Edit Mode
        packageInclusions[editIndex] = itemObj;
        syncInclusionsHidden();
        renderInclusionsList();
        if (typeof renderCustInclusionsList === 'function') renderCustInclusionsList();
        safeCloseModal('addInclusionModal');
    } else {
        // Add Mode
        packageInclusions.push(itemObj);
        syncInclusionsHidden();
        renderInclusionsList();
        if (typeof renderCustInclusionsList === 'function') renderCustInclusionsList();

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
            if (descEl) descEl.value = '';
            resetInclusionImagePicker('');
            setInclusionCategoryChoices(false);
            if (catSelect) catSelect.value = '';
            const banner = document.getElementById('selectedItemInfoBanner');
            if (banner) banner.style.display = 'none';
            window.handleInclusionTypeChange('');
            const typeSelect = document.getElementById('customInclusionCategory');
            if (typeSelect) typeSelect.focus();
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
    if (typeof renderCustInclusionsList === 'function') renderCustInclusionsList();
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
    if (type === 'Equipment') {
        if (window.showToast) window.showToast('Equipment cannot be added through Quick Add Inclusion.', 'error');
        return;
    }
    const editIndexEl = document.getElementById('customInclusionEditIndex');
    const editIdx = editIndexEl ? editIndexEl.value : '-1';

    // Store return state so we return seamlessly to addInclusionModal without closing packageModal
    window._pkgInclusionReturnState = {
        active: true,
        type: type,
        editIndex: editIdx
    };

    // Close inclusion modal temporarily (leaves packageModal untouched)
    safeCloseModal('addInclusionModal');

    const quickType = (type === 'Menu' || type === 'Menu / Food') ? 'menu' : 'service';
    if (typeof window.openQuickAddOptionModal === 'function') {
        window.openQuickAddOptionModal(quickType);
    } else {
        alert(`Opening quick add for ${quickType}...`);
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
                <p style="font-size: 0.85rem; color: #64748b; max-width: 420px; margin: 0 auto 0.4rem auto; line-height: 1.5;">Add the menu, services, and equipment included in this package.</p>
                <p style="font-size: 0.8rem; color: #64748b; font-weight: 600; margin: 0 auto 1.5rem auto;"><i class="fas fa-info-circle" style="color: var(--primary-color, #f97316); margin-right: 4px;"></i>These inclusions are fixed and cannot be changed by customers.</p>
                <button type="button" class="btn-primary-pro" onclick="window.openFixedQuickAddOptionModal()"
                    style="display: inline-flex; align-items: center; gap: 8px; padding: 0.65rem 1.25rem; font-size: 0.875rem; font-weight: 800; border-radius: 10px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
                    <i class="fas fa-plus"></i>
                    <span>Add Inclusion</span>
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

        // Resolve image/description from catalog when available
        let resolvedImg = item.image_url || '';
        let resolvedDesc = item.description || '';
        const catalogKey = (cat === 'Service') ? 'service' : ((cat === 'Equipment') ? 'equipment' : 'menu');
        const catalog = (window.inclusionsCatalog && window.inclusionsCatalog[catalogKey]) || [];
        if (item.item_id) {
            const found = catalog.find(c => Number(c.id) === Number(item.item_id));
            if (found) {
                if (!resolvedImg) resolvedImg = found.image_url || '';
                if (!resolvedDesc) resolvedDesc = found.description || '';
            }
        } else if (item.name) {
            const found = catalog.find(c => String(c.name || '').toLowerCase() === String(item.name).toLowerCase());
            if (found) {
                if (!resolvedImg) resolvedImg = found.image_url || '';
                if (!resolvedDesc) resolvedDesc = found.description || '';
            }
        }

        html += `
        <div class="inclusion-item-card" style="display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; padding: 1rem 1.25rem; background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.02); transition: all 0.2s ease;">
            <div class="inclusion-item-card-content" style="display: flex; align-items: flex-start; gap: 1rem; flex: 1; min-width: 0;">
                <div class="inclusion-item-card-thumbnail" style="width: 56px; height: 56px; border-radius: 12px; background: ${cfg.iconBg}; color: ${cfg.iconColor}; display: flex; align-items: center; justify-content: center; font-size: 1rem; flex-shrink: 0; overflow: hidden;">
                    ${resolvedImg
                        ? `<img src="${escapeHtml(resolvedImg)}" alt="" onerror="this.style.display='none';this.parentElement.innerHTML='<i class=\\'${cfg.icon}\\'></i>';" style="width:100%;height:100%;object-fit:cover;">`
                        : `<i class="${cfg.icon}"></i>`}
                </div>
                <div class="inclusion-item-card-details" style="flex: 1; min-width: 0;">
                    <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 4px;">
                        <span style="font-size: 0.72rem; font-weight: 800; color: ${cfg.badgeColor}; background: ${cfg.badgeBg}; border: 1px solid ${cfg.badgeBorder}; padding: 2px 8px; border-radius: 6px; text-transform: uppercase; letter-spacing: 0.4px;">
                            ${cat}
                        </span>
                    </div>
                    <div style="font-size: 0.98rem; font-weight: 800; color: #0f172a; line-height: 1.3; margin-bottom: 3px;">
                        ${escapeHtml(item.name)}
                    </div>
                    ${resolvedDesc && String(resolvedDesc).trim().length > 2 ? `
                        <div style="font-size: 0.84rem; color: #64748b; line-height: 1.45; margin-top: 4px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                            ${escapeHtml(resolvedDesc)}
                        </div>
                    ` : ''}
                </div>
            </div>

            <!-- Actions -->
            <div class="inclusion-item-card-actions" style="display: flex; align-items: center; gap: 6px; flex-shrink: 0; margin-left: auto;">
                <button type="button" onclick="window.editInclusion(${index})" title="Edit inclusion"
                    aria-label="Edit inclusion"
                    style="display: inline-flex; align-items: center; gap: 5px; padding: 0.45rem 0.75rem; font-size: 0.8rem; font-weight: 700; color: #334155; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; cursor: pointer; transition: all 0.15s;"
                    onmouseover="this.style.background='#e2e8f0'; this.style.color='#0f172a';"
                    onmouseout="this.style.background='#f8fafc'; this.style.color='#334155';">
                    <i class="fas fa-edit" style="color: #64748b;"></i>
                    <span>Edit</span>
                </button>
                <button type="button" onclick="window.removeInclusion(${index})" title="Delete inclusion"
                    aria-label="Delete inclusion"
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
                    confirmBtn.innerText = 'Archive package';
                }
            } catch (err) {
                console.error('Error archiving package:', err);
                alert('An error occurred while archiving.');
                confirmBtn.disabled = false;
                confirmBtn.innerText = 'Archive package';
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

// ==========================================
// CUSTOMIZABLE PACKAGE: AVAILABLE OPTIONS
// ==========================================
let customizableMenuIds = new Set();
let customizableServiceIds = new Set();
let customizableEquipmentIds = new Set();
let customizableCategoryQuotas = {};

let lastMenuQuery = '';
let lastServiceQuery = '';

function getCustomizableMenuCategoryCounts() {
    const counts = {};
    (window.inclusionsCatalog.menu || [])
        .filter(item => customizableMenuIds.has(Number(item.id)))
        .forEach(item => {
            const category = String(item.category || '').trim() || 'Others';
            counts[category] = (counts[category] || 0) + 1;
        });
    return counts;
}

window.toggleCustomizableItem = function (type, id, checked) {
    const numId = Number(id);
    if (type === 'menu') {
        if (checked) customizableMenuIds.add(numId);
        else customizableMenuIds.delete(numId);
        updateCustomizableCounters('menu');
        renderCategoryQuotas();
    } else if (type === 'service') {
        if (checked) customizableServiceIds.add(numId);
        else customizableServiceIds.delete(numId);
        updateCustomizableCounters('service');
    }
    syncCustomizableSelectionRules();
    updatePackageWizardControls();
};

window.toggleAllCustomizableCatalog = function (type, selectAll) {
    const catalog = window.inclusionsCatalog[type] || [];
    if (type === 'menu') {
        if (selectAll) catalog.forEach(i => customizableMenuIds.add(Number(i.id)));
        else customizableMenuIds.clear();
        renderCustomizableMenu(lastMenuQuery);
        updateCustomizableCounters('menu');
        renderCategoryQuotas();
    } else if (type === 'service') {
        if (selectAll) catalog.forEach(i => customizableServiceIds.add(Number(i.id)));
        else customizableServiceIds.clear();
        renderCustomizableServices(lastServiceQuery);
        updateCustomizableCounters('service');
    }
    syncCustomizableSelectionRules();
    updatePackageWizardControls();
};

window.filterCustomizableCatalog = function (type, query) {
    if (type === 'menu') {
        lastMenuQuery = query;
        renderCustomizableMenu(query);
    } else if (type === 'service') {
        lastServiceQuery = query;
        renderCustomizableServices(query);
    }
};

function updateCustomizableCounters(type) {
    const menuBadge = document.getElementById('custMenuCountBadge');
    const serviceBadge = document.getElementById('custServiceCountBadge');
    const totalBadge = document.getElementById('custTotalAvailableBadge');

    if (menuBadge) menuBadge.innerText = `${customizableMenuIds.size} Selected`;
    if (serviceBadge) serviceBadge.innerText = `${customizableServiceIds.size} Selected`;

    if (totalBadge) {
        const total = customizableMenuIds.size + customizableServiceIds.size;
        totalBadge.innerText = `${total} Option${total === 1 ? '' : 's'} Available`;
    }
}

window.renderCustomizableCatalogs = function () {
    renderCustomizableMenu(lastMenuQuery);
    renderCustomizableServices(lastServiceQuery);
    renderCategoryQuotas();
    updateCustomizableCounters();
    updatePackageWizardControls();
};

function renderCustomizableMenu(query = '') {
    const container = document.getElementById('customizableMenuList');
    if (!container) return;

    const items = window.inclusionsCatalog.menu || [];
    const q = (query || '').toLowerCase().trim();
    const filtered = q ? items.filter(i => (i.name || '').toLowerCase().includes(q) || (i.category || '').toLowerCase().includes(q)) : items;

    if (filtered.length === 0) {
        container.innerHTML = `
            <div style="grid-column: 1 / -1; padding: 2rem; text-align: center; color: #94a3b8; font-size: 0.85rem; background: #f8fafc; border-radius: 8px; border: 1.5px dashed #cbd5e1;">
                ${q ? 'No menu items matching search query.' : 'No menu items found in your catalog. Click "+ Quick Add Food" above to add items.'}
            </div>
        `;
        return;
    }

    container.innerHTML = filtered.map(item => {
        const id = Number(item.id);
        const isChecked = customizableMenuIds.has(id);
        const img = item.image_url || '';
        const desc = String(item.description || '').trim();

        return `
            <div style="display: flex; align-items: flex-start; gap: 10px; padding: 0.75rem 0.85rem; background: ${isChecked ? '#f0fdf4' : '#ffffff'}; border: 1.5px solid ${isChecked ? '#86efac' : '#e2e8f0'}; border-radius: 10px; transition: all 0.15s ease;"
                 class="catalog-option-card">
                <input type="checkbox" ${isChecked ? 'checked' : ''} 
                       onchange="window.toggleCustomizableItem('menu', ${id}, this.checked); const c = this.closest('.catalog-option-card'); c.style.background = this.checked ? '#f0fdf4' : '#ffffff'; c.style.borderColor = this.checked ? '#86efac' : '#e2e8f0';"
                       style="width: 17px; height: 17px; accent-color: #16a34a; cursor: pointer; flex-shrink: 0; margin-top: 22px;" />
                <div style="width:56px;height:56px;border-radius:10px;overflow:hidden;background:#f1f5f9;flex-shrink:0;display:flex;align-items:center;justify-content:center;color:#cbd5e1;">
                    ${img
                        ? `<img src="${escapeHtml(img)}" alt="" onerror="this.style.display='none';this.parentElement.innerHTML='<i class=\\'fas fa-utensils\\'></i>';" style="width:100%;height:100%;object-fit:cover;">`
                        : `<i class="fas fa-utensils"></i>`}
                </div>
                <div style="flex: 1; min-width: 0; cursor: pointer;" onclick="const cb = this.parentElement.querySelector('input[type=checkbox]'); cb.checked = !cb.checked; cb.dispatchEvent(new Event('change'));">
                    <strong style="color: #0f172a; font-size: 0.88rem; line-height: 1.3; display:block;">${escapeHtml(item.name)}</strong>
                    <div style="display: flex; align-items: center; gap: 6px; margin-top: 4px; flex-wrap: wrap;">
                        ${item.category ? `<span style="font-size: 0.7rem; font-weight: 700; color: #64748b; background: #f1f5f9; padding: 1px 6px; border-radius: 4px;">${escapeHtml(item.category)}</span>` : ''}
                    </div>
                    ${desc.length > 2 ? `<p style="font-size: 0.75rem; color: #64748b; line-height: 1.4; margin: 6px 0 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${escapeHtml(desc)}</p>` : ''}
                </div>
                <div style="display: flex; align-items: center; gap: 4px; margin-left: 2px; flex-shrink: 0;">
                    <button type="button" title="Edit Dish" onclick="window.openQuickEditModal('menu', ${id}, event)"
                            style="width: 28px; height: 28px; display: inline-flex; align-items: center; justify-content: center; border: 1px solid #e2e8f0; background: #f8fafc; color: #475569; border-radius: 6px; cursor: pointer; transition: all 0.15s ease;"
                            onmouseover="this.style.background='#f1f5f9'; this.style.color='#0f172a'; this.style.borderColor='#cbd5e1';"
                            onmouseout="this.style.background='#f8fafc'; this.style.color='#475569'; this.style.borderColor='#e2e8f0';">
                        <i class="fas fa-edit" style="font-size: 0.75rem;"></i>
                    </button>
                    <button type="button" title="Delete Dish" onclick="window.quickDeleteCatalogItem('menu', ${id}, event)"
                            style="width: 28px; height: 28px; display: inline-flex; align-items: center; justify-content: center; border: 1px solid #fee2e2; background: #fef2f2; color: #dc2626; border-radius: 6px; cursor: pointer; transition: all 0.15s ease;"
                            onmouseover="this.style.background='#fee2e2'; this.style.borderColor='#fca5a5';"
                            onmouseout="this.style.background='#fef2f2'; this.style.borderColor='#fee2e2';">
                        <i class="fas fa-trash-alt" style="font-size: 0.75rem;"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function renderCustomizableServices(query = '') {
    const container = document.getElementById('customizableServiceList');
    if (!container) return;

    const items = window.inclusionsCatalog.service || [];
    const q = (query || '').toLowerCase().trim();
    const filtered = q ? items.filter(i => (i.name || '').toLowerCase().includes(q) || (i.category || '').toLowerCase().includes(q)) : items;

    if (filtered.length === 0) {
        container.innerHTML = `
            <div style="grid-column: 1 / -1; padding: 2rem; text-align: center; color: #94a3b8; font-size: 0.85rem; background: #f8fafc; border-radius: 8px; border: 1.5px dashed #cbd5e1;">
                ${q ? 'No services matching search query.' : 'No services found in your catalog. Click "+ Quick Add Service" above to add services.'}
            </div>
        `;
        return;
    }

    container.innerHTML = filtered.map(item => {
        const id = Number(item.id);
        const isChecked = customizableServiceIds.has(id);
        const price = parseFloat(item.price || item.selling_price || 0);
        let unitText = item.unit_type || 'service';
        if (unitText.startsWith('per_')) unitText = unitText.replace('per_', '');
        const img = item.image_url || '';
        const notes = String(item.notes || item.description || '')
            .split(/[\n,]+/)
            .map(note => note.replace(/^\s*[•*-]\s*/, '').trim())
            .filter(Boolean);
        const notesHtml = notes.length
            ? `<details class="package-service-notes" onclick="event.stopPropagation()">
                    <summary>Service notes (${notes.length})</summary>
                    <ul>${notes.map(note => `<li>${escapeHtml(note)}</li>`).join('')}</ul>
               </details>`
            : '';

        return `
            <div style="display: flex; align-items: flex-start; gap: 10px; padding: 0.75rem 0.85rem; background: ${isChecked ? '#eff6ff' : '#ffffff'}; border: 1.5px solid ${isChecked ? '#93c5fd' : '#e2e8f0'}; border-radius: 10px; transition: all 0.15s ease;"
                 class="catalog-option-card service-option-card">
                <input type="checkbox" ${isChecked ? 'checked' : ''} 
                       onchange="window.toggleCustomizableItem('service', ${id}, this.checked); const c = this.closest('.catalog-option-card'); c.style.background = this.checked ? '#eff6ff' : '#ffffff'; c.style.borderColor = this.checked ? '#93c5fd' : '#e2e8f0';"
                       style="width: 17px; height: 17px; accent-color: #2563eb; cursor: pointer; flex-shrink: 0; margin-top: 22px;" />
                <div style="width:56px;height:56px;border-radius:10px;overflow:hidden;background:#f1f5f9;flex-shrink:0;display:flex;align-items:center;justify-content:center;color:#cbd5e1;">
                    ${img
                        ? `<img src="${escapeHtml(img)}" alt="" onerror="this.style.display='none';this.parentElement.innerHTML='<i class=\\'fas fa-concierge-bell\\'></i>';" style="width:100%;height:100%;object-fit:cover;">`
                        : `<i class="fas fa-concierge-bell"></i>`}
                </div>
                <div style="flex: 1; min-width: 0; cursor: pointer;" onclick="const cb = this.parentElement.querySelector('input[type=checkbox]'); cb.checked = !cb.checked; cb.dispatchEvent(new Event('change'));">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 6px;">
                        <strong style="color: #0f172a; font-size: 0.88rem; line-height: 1.3;">${escapeHtml(item.name)}</strong>
                        <span class="service-option-price" style="font-size: 0.75rem; font-weight: 800; color: #1e40af; background: #dbeafe; padding: 2px 7px; border-radius: 6px; white-space: nowrap;">
                            ₱${price.toLocaleString('en-PH', { minimumFractionDigits: 2 })}${unitText && unitText !== 'fixed' ? '/' + escapeHtml(unitText) : ''}
                        </span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px; margin-top: 4px; flex-wrap: wrap;">
                        ${item.category ? `<span style="font-size: 0.7rem; font-weight: 700; color: #64748b; background: #f1f5f9; padding: 1px 6px; border-radius: 4px;">${escapeHtml(item.category)}</span>` : ''}
                    </div>
                    ${notesHtml}
                </div>
                <div style="display: flex; align-items: center; gap: 4px; margin-left: 2px; flex-shrink: 0;">
                    <button type="button" title="Edit Service" onclick="window.openQuickEditModal('service', ${id}, event)"
                            style="width: 28px; height: 28px; display: inline-flex; align-items: center; justify-content: center; border: 1px solid #e2e8f0; background: #f8fafc; color: #475569; border-radius: 6px; cursor: pointer; transition: all 0.15s ease;"
                            onmouseover="this.style.background='#f1f5f9'; this.style.color='#0f172a'; this.style.borderColor='#cbd5e1';"
                            onmouseout="this.style.background='#f8fafc'; this.style.color='#475569'; this.style.borderColor='#e2e8f0';">
                        <i class="fas fa-edit" style="font-size: 0.75rem;"></i>
                    </button>
                    <button type="button" title="Delete Service" onclick="window.quickDeleteCatalogItem('service', ${id}, event)"
                            style="width: 28px; height: 28px; display: inline-flex; align-items: center; justify-content: center; border: 1px solid #fee2e2; background: #fef2f2; color: #dc2626; border-radius: 6px; cursor: pointer; transition: all 0.15s ease;"
                            onmouseover="this.style.background='#fee2e2'; this.style.borderColor='#fca5a5';"
                            onmouseout="this.style.background='#fef2f2'; this.style.borderColor='#fee2e2';">
                        <i class="fas fa-trash-alt" style="font-size: 0.75rem;"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function syncCustomizableSelectionRules() {
    const jsonInput = document.getElementById('package_selection_rules_json');
    if (jsonInput) {
        const cleanQuotas = {};
        let total = 0;
        const categoryCounts = getCustomizableMenuCategoryCounts();
        for (const [cat, available] of Object.entries(categoryCounts)) {
            const rawQuota = customizableCategoryQuotas[cat];
            const num = Number(rawQuota);
            if (String(rawQuota ?? '').trim() && Number.isInteger(num) && num >= 1 && num <= available) {
                cleanQuotas[cat] = num;
                total += num;
            }
        }
        const payload = {
            package_type: 'customizable',
            available_menu_ids: Array.from(customizableMenuIds),
            available_service_ids: Array.from(customizableServiceIds),
            available_equipment_ids: [],
            category_quotas: cleanQuotas,
            total_variants_allowed: total
        };
        jsonInput.value = JSON.stringify(payload);
    }
}

window.setCategoryQuota = function(encodedCat, val) {
    const cat = decodeURIComponent(encodedCat);
    const available = getCustomizableMenuCategoryCounts()[cat] || 0;
    const next = String(val || '').trim() ? Number(val) : NaN;
    if (!Number.isInteger(next) || next < 1 || next > available) {
        delete customizableCategoryQuotas[cat];
    } else {
        customizableCategoryQuotas[cat] = next;
    }
    renderCategoryQuotas();
    syncCustomizableSelectionRules();
    updatePackageWizardControls();
};

function renderCategoryQuotas() {
    const container = document.getElementById('categoryQuotasContainer');
    if (!container) return;

    const catCounts = getCustomizableMenuCategoryCounts();
    const categories = Object.keys(catCounts).sort();
    if (categories.length === 0) {
        container.innerHTML = `
            <div class="customizable-quota-empty" style="grid-column: 1 / -1; padding: 1rem; text-align: center; color: #64748b; font-size: 0.82rem;">
                Select the menu dishes you want to offer above. Their categories and limits will appear here.
            </div>
        `;
        const totalEl = document.getElementById('custTotalVariantsAllowedText');
        if (totalEl) totalEl.innerText = '0';
        const banner = document.getElementById('custQuotaSummaryBanner');
        if (banner) {
            banner.style.display = 'block';
            banner.textContent = 'Choose menu dishes above to configure customer selection limits.';
        }
        return;
    }

    let totalAllowed = 0;
    const summaryParts = [];

    container.innerHTML = categories.map(cat => {
        const quotaValue = customizableCategoryQuotas[cat];
        const quota = String(quotaValue ?? '').trim() ? Number(quotaValue) : NaN;
        const availableInCat = catCounts[cat] || 0;
        const encodedCat = encodeURIComponent(cat).replace(/'/g, '%27');
        const quotaIsValid = Number.isInteger(quota) && quota >= 1 && quota <= availableInCat;

        if (quotaIsValid) {
            totalAllowed += quota;
            summaryParts.push(`${quota} from ${escapeHtml(cat)}`);
        }

        return `
            <div class="customizable-quota-card" style="background: ${quotaIsValid ? '#ffffff' : '#fffaf5'}; border: 1.5px solid ${quotaIsValid ? '#fed7aa' : '#fdba74'}; border-radius: 8px; padding: 10px 12px; display: flex; align-items: center; justify-content: space-between; gap: 10px;">
                <div class="customizable-quota-category">
                    <strong>${escapeHtml(cat)}</strong>
                    <span>${availableInCat} choice${availableInCat === 1 ? '' : 's'} offered</span>
                </div>
                <label class="customizable-quota-input">
                    <span>Customer must choose</span>
                    <span class="customizable-quota-input-control">
                        <input type="number" min="1" max="${availableInCat}" value="${quotaIsValid ? quota : ''}"
                            aria-label="Number of ${escapeHtml(cat)} dishes customers may select"
                            onchange="window.setCategoryQuota('${encodedCat}', this.value)" />
                        <span>of ${availableInCat}</span>
                    </span>
                </label>
            </div>
        `;
    }).join('');

    const totalEl = document.getElementById('custTotalVariantsAllowedText');
    if (totalEl) totalEl.innerText = totalAllowed;

    const banner = document.getElementById('custQuotaSummaryBanner');
    if (banner) {
        banner.style.display = 'block';
        banner.innerHTML = summaryParts.length === categories.length
            ? `<strong>Required customer picks:</strong> ${summaryParts.join(', ')} (${totalAllowed} total)`
            : 'Set the required number of picks for each selected category to continue.';
    }
    updatePackageWizardControls();
}

function renderReviewCustomizable() {
    try {
        // 1. Available Menu / Food
        const menuList = document.getElementById('reviewCustMenuList');
        const menuCountBadge = document.getElementById('reviewCustMenuCount');
        const menuCatalog = (window.inclusionsCatalog && window.inclusionsCatalog.menu) || [];
        const selectedMenuItems = menuCatalog.filter(i => customizableMenuIds.has(Number(i.id)));

        if (menuCountBadge) menuCountBadge.innerText = `${selectedMenuItems.length} item${selectedMenuItems.length === 1 ? '' : 's'}`;
        if (menuList) {
            if (selectedMenuItems.length === 0) {
                menuList.innerHTML = '<div style="color:#94a3b8; font-size:0.85rem; font-style:italic; padding: 6px 0;">No menu items selected. Customers will not have food options to choose from.</div>';
            } else {
                menuList.innerHTML = selectedMenuItems.map(i => {
                    return `
                        <div style="font-size:0.85rem; color:#1e293b; display:flex; justify-content:space-between; align-items:center; padding:5px 0; border-bottom:1px dashed #f1f5f9;">
                            <span><i class="fas fa-check-circle" style="color:#16a34a; font-size:0.8rem; margin-right:6px;"></i><strong>${escapeHtml(i.name)}</strong>${i.category ? ' <span style="color:#64748b; font-size:0.75rem;">(' + escapeHtml(i.category) + ')</span>' : ''}</span>
                        </div>
                    `;
                }).join('');
            }
        }

        // 2. Category Quotas / Selection Limits Summary
        const quotaBanner = document.getElementById('reviewCustQuotaBlock');
        if (quotaBanner) {
            const summaryParts = [];
            let totalAllowed = 0;
            if (typeof customizableCategoryQuotas === 'object' && customizableCategoryQuotas !== null) {
                for (const [cat, val] of Object.entries(customizableCategoryQuotas)) {
                    const num = parseInt(val, 10);
                    if (!isNaN(num) && num > 0) {
                        summaryParts.push(`<span style="background: #ffffff; border: 1px solid #fed7aa; padding: 3px 8px; border-radius: 6px; font-weight: 700; color: #9a3412; font-size: 0.8rem;"><strong style="color: #ea580c;">${num}</strong> required from ${escapeHtml(cat)}</span>`);
                        totalAllowed += num;
                    }
                }
            }
            if (summaryParts.length > 0) {
                quotaBanner.style.display = 'block';
                quotaBanner.innerHTML = `
                    <div style="background: #fff7ed; border: 1.5px solid #fed7aa; border-radius: 10px; padding: 0.85rem 1rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 4px;">
                            <h5 style="font-size: 0.75rem; font-weight: 800; color: #c2410c; text-transform: uppercase; margin: 0;">
                                <i class="fas fa-layer-group" style="margin-right: 5px;"></i>                                 Required Menu Picks by Category
                            </h5>
                            <span style="font-size: 0.75rem; font-weight: 800; color: #ea580c; background: #ffedd5; padding: 2px 8px; border-radius: 12px; border: 1px solid #fed7aa;">
                                Required: ${totalAllowed} dish${totalAllowed === 1 ? '' : 'es'}
                            </span>
                        </div>
                        <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px;">
                            ${summaryParts.join('')}
                        </div>
                        <div style="font-size: 0.78rem; color: #9a3412; margin-top: 6px;">
                            <i class="fas fa-check" style="margin-right: 4px;"></i> Customers must select the required number from every category to continue.
                        </div>
                    </div>
                `;
            } else {
                quotaBanner.style.display = 'none';
            }
        }

        // 3. Available Services
        const svcList = document.getElementById('reviewCustServicesList');
        const svcCountBadge = document.getElementById('reviewCustServicesCount');
        const svcCatalog = (window.inclusionsCatalog && window.inclusionsCatalog.service) || [];
        const selectedSvcItems = svcCatalog.filter(i => customizableServiceIds.has(Number(i.id)));

        if (svcCountBadge) svcCountBadge.innerText = `${selectedSvcItems.length} item${selectedSvcItems.length === 1 ? '' : 's'}`;
        if (svcList) {
            if (selectedSvcItems.length === 0) {
                svcList.innerHTML = '<div style="color:#94a3b8; font-size:0.85rem; font-style:italic; padding: 6px 0;">No services selected.</div>';
            } else {
                svcList.innerHTML = selectedSvcItems.map(i => {
                    const price = parseFloat(i.price || i.selling_price || 0);
                    const unit = (i.unit_type || 'service').replace('per_', '');
                    return `
                        <div style="font-size:0.85rem; color:#1e293b; display:flex; justify-content:space-between; align-items:center; padding:5px 0; border-bottom:1px dashed #f1f5f9;">
                            <span><i class="fas fa-check-circle" style="color:#2563eb; font-size:0.8rem; margin-right:6px;"></i><strong>${escapeHtml(i.name)}</strong></span>
                            <span style="font-weight:700; color:#1e40af; font-size:0.78rem;">₱${price.toLocaleString('en-PH', { minimumFractionDigits: 2 })}${unit && unit !== 'fixed' ? '/' + escapeHtml(unit) : ''}</span>
                        </div>
                    `;
                }).join('');
            }
        }
    } catch (err) {
        console.error("renderReviewCustomizable error:", err);
    }
}

// -------------------------------------------------------------
// Quick Add Options for Customizable Packages (Food, Service, Equipment)
// -------------------------------------------------------------
window.validateQuickAddOptionPrice = function () {
    const input = document.getElementById('quickAddOptionPrice');
    const error = document.getElementById('quickAddOptionPriceError');
    const type = document.getElementById('quickAddOptionType')?.value || '';
    if (!input) return false;
    if (window.applyCommaFormatting) window.applyCommaFormatting(input);

    const rawValue = input.value.replace(/,/g, '').trim();
    const amount = Number(rawValue);
    let message = '';
    if (type === 'service') {
        if (!rawValue) {
            message = 'Enter a service fee.';
        } else if (input.dataset.formatOverflow === 'true') {
            message = 'Use up to 8 whole-number digits and 2 decimal places.';
        } else if (!/^\d+(?:\.\d{1,2})?$/.test(rawValue) || !Number.isFinite(amount)) {
            message = 'Enter a valid service fee with no more than 2 decimal places.';
        } else if (amount <= 0) {
            message = 'Service fee must be greater than zero.';
        } else if (amount > 99999999.99) {
            message = 'The maximum service fee is ₱99,999,999.99.';
        }
    }

    input.setCustomValidity(message);
    if (error) {
        error.textContent = message;
        error.style.display = message ? 'block' : 'none';
    }
    return !message;
};

window.renderQuickAddOptionCategorySuggestions = function () {
    const input = document.getElementById('quickAddOptionCategory');
    const suggestionList = document.getElementById('quickAddOptionCategorySuggestions');
    if (!input || !suggestionList || document.getElementById('quickAddOptionType')?.value !== 'menu') return;

    const query = input.value.trim().toLowerCase();
    const categories = Array.from(new Set((window.inclusionsCatalog.menu || [])
        .map(item => String(item.category || '').trim())
        .filter(Boolean)))
        .filter(category => !query || category.toLowerCase().includes(query))
        .sort((a, b) => a.localeCompare(b));

    if (!categories.length) {
        suggestionList.innerHTML = '';
        suggestionList.style.display = 'none';
        return;
    }

    suggestionList.innerHTML = categories.map(category => `
        <button type="button" class="quick-add-category-suggestion" data-category="${escapeHtml(category)}"
            onmousedown="event.preventDefault()">
            ${escapeHtml(category)}
        </button>
    `).join('');
    suggestionList.style.display = 'block';
};

window.handleQuickAddOptionCategorySuggestionClick = function (event) {
    const suggestionList = event.currentTarget;
    const target = event.target instanceof Element ? event.target.closest('.quick-add-category-suggestion') : null;
    let option = target;

    if (!option) {
        const listRect = suggestionList.getBoundingClientRect();
        const clickY = event.clientY - listRect.top + suggestionList.scrollTop;
        option = Array.from(suggestionList.children).find(child =>
            clickY >= child.offsetTop && clickY < child.offsetTop + child.offsetHeight
        );
    }

    if (!option || !option.dataset.category) return;
    event.preventDefault();
    event.stopPropagation();
    window.selectQuickAddOptionCategory(option.dataset.category);
};

window.selectQuickAddOptionCategory = function (category) {
    const input = document.getElementById('quickAddOptionCategory');
    const suggestionList = document.getElementById('quickAddOptionCategorySuggestions');
    if (input) {
        input.value = category;
        input.setCustomValidity('');
    }
    if (suggestionList) suggestionList.style.display = 'none';
};

window.setQuickAddOptionType = function (type) {
    if (!['menu', 'service', 'equipment'].includes(type)) type = '';

    const footer = document.getElementById('quickAddOptionFooter');
    const hiddenType = document.getElementById('quickAddOptionType');
    const typeWrapper = document.getElementById('quickAddOptionTypeWrapper');
    const nameWrapper = document.getElementById('quickAddOptionNameWrapper');
    const unitWrapper = document.getElementById('quickAddOptionUnitWrapper');
    const descriptionWrapper = document.getElementById('quickAddOptionDescriptionWrapper');
    const photoWrapper = document.getElementById('quickAddOptionPhotoWrapper');
    const priceRow = document.getElementById('quickAddOptionPriceRow');
    const priceWrapper = document.getElementById('quickAddOptionPriceWrapper');
    const priceLabel = document.getElementById('quickAddOptionPriceLabel');
    const priceInput = document.getElementById('quickAddOptionPrice');
    const priceError = document.getElementById('quickAddOptionPriceError');
    const qtyWrapper = document.getElementById('quickAddOptionQtyWrapper');
    const nameLabel = document.getElementById('quickAddOptionNameLabel');
    const nameInput = document.getElementById('quickAddOptionName');
    const unitLabel = document.getElementById('quickAddOptionUnitLabel');
    const unitSelect = document.getElementById('quickAddOptionUnit');
    const categoryInput = document.getElementById('quickAddOptionCategory');
    const categoryWrapper = document.getElementById('quickAddOptionCategoryWrapper');
    const categorySuggestions = document.getElementById('quickAddOptionCategorySuggestions');
    const description = document.getElementById('quickAddOptionDescription');
    const equipmentFlow = type === 'equipment';

    if (categoryInput && categorySuggestions && !categoryInput.dataset.suggestionsBound) {
        categoryInput.addEventListener('input', window.renderQuickAddOptionCategorySuggestions);
        categoryInput.addEventListener('focus', window.renderQuickAddOptionCategorySuggestions);
        categorySuggestions.addEventListener('click', window.handleQuickAddOptionCategorySuggestionClick);
        categoryInput.addEventListener('blur', () => {
            window.setTimeout(() => {
                if (categorySuggestions) categorySuggestions.style.display = 'none';
            }, 250);
        });
        categoryInput.dataset.suggestionsBound = 'true';
    }

    if (hiddenType) hiddenType.value = type;

    const hasType = Boolean(type);
    if (hiddenType) hiddenType.required = true;
    if (window._pkgInclusionReturnState?.direct) {
        window._pkgInclusionReturnState.type = type === 'menu'
            ? 'Menu'
            : (type === 'service' ? 'Service' : (type === 'equipment' ? 'Equipment' : ''));
    }
    if (typeWrapper) typeWrapper.style.display = 'block';
    if (footer) footer.style.display = hasType ? 'flex' : 'none';
    if (nameWrapper) nameWrapper.style.display = hasType ? 'block' : 'none';
    if (unitWrapper) unitWrapper.style.display = hasType ? 'block' : 'none';
    if (descriptionWrapper) descriptionWrapper.style.display = hasType ? 'block' : 'none';
    if (photoWrapper) photoWrapper.style.display = hasType ? 'block' : 'none';
    if (categoryWrapper) categoryWrapper.style.display = type === 'menu' ? 'block' : 'none';
    if (nameInput) nameInput.required = hasType;
    if (unitSelect) unitSelect.required = hasType;
    if (categoryInput) categoryInput.required = type === 'menu';
    if (qtyWrapper) qtyWrapper.style.display = equipmentFlow ? 'block' : 'none';
    if (priceError) {
        priceError.textContent = '';
        priceError.style.display = 'none';
    }
    if (priceInput) priceInput.setCustomValidity('');

    if (!hasType) {
        if (priceRow) priceRow.style.display = 'none';
        if (priceInput) priceInput.required = false;
        if (categoryInput) categoryInput.value = '';
        if (categorySuggestions) {
            categorySuggestions.innerHTML = '';
            categorySuggestions.style.display = 'none';
        }
        return;
    }

    if (type === 'menu') {
        if (nameLabel) nameLabel.innerHTML = 'Dish / Menu Item Name <span style="color: #ef4444;">*</span>';
        if (nameInput) nameInput.placeholder = 'e.g. Sweet & Sour Pork, Roast Beef, Lechon Belly';
        if (unitLabel) unitLabel.innerHTML = 'Serving Unit <span style="color: #ef4444;">*</span>';
        if (unitSelect) {
            unitSelect.innerHTML = `
                <option value="per_pax">Per Pax / Guest</option>
                <option value="per_tray">Per Tray</option>
                <option value="per_platter">Per Platter</option>
                <option value="per_order">Per Order</option>
            `;
            unitSelect.value = 'per_pax';
        }
        if (categoryInput) categoryInput.value = '';
        if (categorySuggestions) {
            categorySuggestions.innerHTML = '';
            categorySuggestions.style.display = 'none';
        }
        if (priceRow) priceRow.style.display = 'none';
        if (priceInput) {
            priceInput.value = '0.00';
            priceInput.required = false;
        }
        if (priceWrapper) priceWrapper.style.display = 'none';
        if (description) description.placeholder = 'Details, ingredients, specifications or notes...';
    } else if (type === 'service') {
        if (nameLabel) nameLabel.innerHTML = 'Service Name <span style="color: #ef4444;">*</span>';
        if (nameInput) nameInput.placeholder = 'e.g. Trained Waitstaff, Event Setup & Cleanup, Bartender';
        if (unitLabel) unitLabel.innerHTML = 'Service Rate Type <span style="color: #ef4444;">*</span>';
        if (unitSelect) {
            unitSelect.innerHTML = `
                <option value="per_event">Per Event (Flat Rate)</option>
                <option value="per_pax">Per Person</option>
                <option value="per_hour">Per Hour</option>
            `;
            unitSelect.value = 'per_event';
        }
        if (categoryInput) categoryInput.value = 'Service';
        if (priceRow) {
            priceRow.style.display = 'grid';
            priceRow.style.gridTemplateColumns = 'minmax(0, 1fr)';
        }
        if (priceWrapper) priceWrapper.style.display = 'block';
        if (priceLabel) priceLabel.innerHTML = 'Service Fee (₱) <span style="color: #ef4444;">*</span>';
        if (priceInput) {
            priceInput.required = true;
            priceInput.value = '';
            priceInput.placeholder = '0.00';
        }
        if (description) description.placeholder = 'Details, inclusions, specifications or notes...';
    } else {
        if (nameLabel) nameLabel.innerHTML = 'Equipment / Item Name <span style="color: #ef4444;">*</span>';
        if (nameInput) nameInput.placeholder = 'e.g. Tiffany Chairs, Round Banquet Table, Chafing Dish';
        if (unitLabel) unitLabel.innerText = 'Unit / Pricing';
        if (unitSelect) {
            unitSelect.innerHTML = `
                <option value="piece">Per Piece</option>
                <option value="set">Per Set</option>
                <option value="pair">Per Pair</option>
                <option value="lot">Per Lot / Package</option>
            `;
            unitSelect.value = 'piece';
        }
        if (categoryInput) categoryInput.value = 'Equipment';
        if (priceRow) {
            priceRow.style.display = 'grid';
            priceRow.style.gridTemplateColumns = '1fr 1fr';
        }
        if (priceWrapper) priceWrapper.style.display = 'block';
        if (priceLabel) priceLabel.innerHTML = 'Rental Rate (₱) <span style="color: #ef4444;">*</span>';
        if (priceInput) {
            priceInput.required = true;
            priceInput.value = '0.00';
        }
    }

    const title = document.getElementById('quickAddOptionModalTitle');
    const subtitle = document.querySelector('#quickAddOptionModal .quick-add-option-subtitle');
    const itemLabel = type === 'menu' ? 'menu item' : type;
    if (title) title.textContent = `Create ${itemLabel}`;
    if (subtitle) subtitle.textContent = `Add a new ${itemLabel} to your catalog${window._pkgInclusionReturnState?.direct ? ' and package' : ''}.`;
};

window.openQuickAddOptionModal = function (type) {
    const modal = document.getElementById('quickAddOptionModal');
    if (!modal) return;

    const form = document.getElementById('quickAddOptionForm');
    if (form) form.reset();
    const photoPreview = document.getElementById('quickAddOptionPhotoPreview');
    if (photoPreview) photoPreview.innerHTML = '';

    const normalizedType = ['menu', 'service', 'equipment'].includes(type) ? type : '';
    window.setQuickAddOptionType(normalizedType);
    const title = document.getElementById('quickAddOptionModalTitle');
    const subtitle = modal.querySelector('.quick-add-option-subtitle');
    if (title) {
        title.textContent = normalizedType
            ? `Create ${normalizedType === 'menu' ? 'menu item' : normalizedType}`
            : 'Quick Add Inclusion';
    }
    if (subtitle) {
        subtitle.textContent = normalizedType
            ? `Add a new ${normalizedType === 'menu' ? 'menu item' : normalizedType} to your catalog and package.`
            : 'Choose an option type, then add it to your catalog and package.';
    }
    safeOpenModal('quickAddOptionModal', true);
};

window.openFixedQuickAddOptionModal = function () {
    window._pkgInclusionReturnState = {
        active: true,
        direct: true,
        type: ''
    };
    window.openQuickAddOptionModal('');
};

window.closeQuickAddOptionModal = function () {
    safeCloseModal('quickAddOptionModal');
    if (window._pkgInclusionReturnState && window._pkgInclusionReturnState.active) {
        if (!window._pkgInclusionReturnState.direct) {
            safeOpenModal('addInclusionModal', true);
        }
        window._pkgInclusionReturnState = null;
    }
};

window.submitQuickAddOption = async function (e) {
    e.preventDefault();
    const type = document.getElementById('quickAddOptionType')?.value || '';
    const name = (document.getElementById('quickAddOptionName')?.value || '').trim();
    const categoryInput = document.getElementById('quickAddOptionCategory');
    const category = (categoryInput?.value || '').trim();
    const unit = document.getElementById('quickAddOptionUnit')?.value || '';
    const priceInput = document.getElementById('quickAddOptionPrice');
    const priceText = (priceInput?.value || '').trim();
    const price = type === 'menu' ? 0 : (Number(priceText.replace(/,/g, '')) || 0);
    const qty = parseInt(document.getElementById('quickAddOptionQty')?.value || 100, 10) || 100;
    const desc = (document.getElementById('quickAddOptionDescription')?.value || '').trim();

    if (!['menu', 'service', 'equipment'].includes(type)) {
        alert('Please choose an option type.');
        return;
    }
    if (!name) {
        alert('Please enter an item name.');
        return;
    }
    if (type === 'menu' && !category.trim()) {
        if (categoryInput) {
            categoryInput.setCustomValidity('Enter a food category, such as Rice, Pork, or Chicken.');
            categoryInput.reportValidity();
            categoryInput.focus();
        }
        return;
    }
    if (categoryInput) categoryInput.setCustomValidity('');
    if (type === 'service' && !window.validateQuickAddOptionPrice()) {
        if (priceInput) priceInput.focus();
        return;
    }

    const btn = document.getElementById('btnQuickOptionSubmit');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Saving...</span>';
    }

    try {
        const formData = new FormData();
        formData.append('item_type', type);
        formData.append('name', name);
        formData.append('category', category);
        formData.append('price', price);
        formData.append('unit_type', unit);
        formData.append('description', desc);
        formData.append('available_qty', qty);
        const fileInput = document.getElementById('quickAddOptionImage');
        if (fileInput && fileInput.files && fileInput.files[0]) {
            formData.append('image', fileInput.files[0]);
        }

        const res = await fetch('/caterer/api/catalogs/quick-add', {
            method: 'POST',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            body: formData
        });

        const data = await res.json();
        if (!res.ok || data.status !== 'success') {
            throw new Error(extractErrorMessage(data, 'Failed to save item'));
        }

        const newItem = data.item;
        if (!window.inclusionsCatalog[type]) {
            window.inclusionsCatalog[type] = [];
        }
        // Unshift so new item appears at the top
        window.inclusionsCatalog[type].unshift(newItem);

        // Pre-select the new item in customizable package
        const newId = Number(newItem.id);
        if (type === 'menu') customizableMenuIds.add(newId);
        else if (type === 'service') customizableServiceIds.add(newId);
        else if (type === 'equipment') customizableEquipmentIds.add(newId);

        // Update UI
        renderCustomizableCatalogs();
        syncCustomizableSelectionRules();
        renderReviewCustomizable();

        // Close modal
        safeCloseModal('quickAddOptionModal');

        if (window._pkgInclusionReturnState?.direct) {
            const categoryLabel = type === 'menu' ? 'Menu / Food' : type.charAt(0).toUpperCase() + type.slice(1);
            packageInclusions.push({
                type: categoryLabel === 'Menu / Food' ? 'Menu' : categoryLabel,
                category: categoryLabel,
                item_id: newId,
                name: newItem.name,
                description: newItem.description || '',
                image_url: newItem.image_url || ''
            });
            syncInclusionsHidden();
            renderInclusionsList();
            if (typeof renderCustInclusionsList === 'function') renderCustInclusionsList();
            window._pkgInclusionReturnState = null;
            if (window.showToast) {
                window.showToast(`Added "${newItem.name}" to this package.`, 'success');
            }
            return;
        }

        // Check if we came from inclusion modal (e.g. fixed-price package create/edit)
        if (window._pkgInclusionReturnState && window._pkgInclusionReturnState.active) {
            const savedState = window._pkgInclusionReturnState;
            window._pkgInclusionReturnState = null;
            safeOpenModal('addInclusionModal', true);
            window.handleInclusionTypeChange(savedState.type, newItem.id);
            if (window.showToast) {
                window.showToast(`Added "${newItem.name}" and selected for inclusion!`, 'success');
            }
            return;
        }

        if (window.showToast) {
            window.showToast(`Added "${newItem.name}" and selected for this package!`, 'success');
        }
    } catch (err) {
        console.error('submitQuickAddOption error:', err);
        alert(err.message || 'An error occurred while saving.');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check"></i> <span>Save &amp; Select</span>';
        }
    }
};

// -------------------------------------------------------------
// Quick Edit & Delete for Catalog Items (Food & Services)
// -------------------------------------------------------------
window.openQuickEditModal = function (type, id, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const modal = document.getElementById('quickEditOptionModal');
    if (!modal) return;

    const list = window.inclusionsCatalog[type] || [];
    const item = list.find(i => Number(i.id) === Number(id));
    if (!item) {
        alert('Item not found in catalog.');
        return;
    }

    const form = document.getElementById('quickEditOptionForm');
    if (form) form.reset();

    const hiddenType = document.getElementById('quickEditOptionType');
    const hiddenId = document.getElementById('quickEditOptionId');
    if (hiddenType) hiddenType.value = type;
    if (hiddenId) hiddenId.value = id;

    const titleEl = document.getElementById('quickEditOptionModalTitle');
    const nameLabel = document.getElementById('quickEditOptionNameLabel');
    const nameInput = document.getElementById('quickEditOptionName');
    const catSelect = document.getElementById('quickEditOptionCategory');
    const categorySuggestions = document.getElementById('quickEditOptionCategorySuggestions');
    const unitLabel = document.getElementById('quickEditOptionUnitLabel');
    const unitSelect = document.getElementById('quickEditOptionUnit');
    const priceLabel = document.getElementById('quickEditOptionPriceLabel');
    const priceInput = document.getElementById('quickEditOptionPrice');
    const descInput = document.getElementById('quickEditOptionDescription');

    const price = parseFloat(item.price || item.selling_price || 0);

    const priceWrapper = document.getElementById('quickEditOptionPriceWrapper');
    if (catSelect) catSelect.value = item.category || (type === 'service' ? 'Service' : '');
    if (categorySuggestions) {
        const categories = Array.from(new Set([
            ...(window.inclusionsCatalog[type] || []).map(entry => String(entry.category || '').trim()),
            String(item.category || '').trim()
        ].filter(Boolean)));
        categorySuggestions.innerHTML = categories.map(category => `<option value="${escapeHtml(category)}"></option>`).join('');
    }

    if (type === 'menu') {
        if (titleEl) titleEl.innerHTML = '<i class="fas fa-edit" style="color: #16a34a; margin-right: 6px;"></i> Edit Food / Dish';
        if (nameLabel) nameLabel.innerHTML = 'Dish / Menu Item Name <span style="color: #ef4444;">*</span>';
        if (unitLabel) unitLabel.innerText = 'Serving Unit';
        if (priceWrapper) priceWrapper.style.display = 'none';
        if (priceInput) {
            priceInput.value = '0.00';
            priceInput.required = false;
        }

        if (unitSelect) {
            unitSelect.innerHTML = `
                <option value="per_pax">Per Pax / Guest</option>
                <option value="per_tray">Per Tray / Pan</option>
                <option value="per_serving">Per Serving</option>
                <option value="per_order">Per Order</option>
            `;
            const u = item.unit_type || item.pricing_unit || 'per_pax';
            unitSelect.value = u;
        }
    } else if (type === 'service') {
        if (titleEl) titleEl.innerHTML = '<i class="fas fa-edit" style="color: #2563eb; margin-right: 6px;"></i> Edit Service';
        if (nameLabel) nameLabel.innerHTML = 'Service Name <span style="color: #ef4444;">*</span>';
        if (unitLabel) unitLabel.innerText = 'Service Rate Type';
        if (priceWrapper) priceWrapper.style.display = 'block';
        if (priceLabel) priceLabel.innerHTML = 'Service Fee (₱) <span style="color: #ef4444;">*</span>';
        if (priceInput) priceInput.required = true;

        if (unitSelect) {
            unitSelect.innerHTML = `
                <option value="per_event">Per Event (Flat Rate)</option>
                <option value="per_hour">Per Hour</option>
                <option value="per_staff">Per Staff Member</option>
                <option value="per_pax">Per Pax / Guest</option>
            `;
            if (item.unit_type) {
                unitSelect.value = item.unit_type;
            }
        }
    }

    if (nameInput) nameInput.value = item.name || '';
    if (priceInput) priceInput.value = price.toFixed(2);
    if (descInput) descInput.value = item.description || '';

    // Populate existing photo preview
    const photoPreview = document.getElementById('quickEditOptionPhotoPreview');
    const photoHint    = document.getElementById('quickEditOptionPhotoHint');
    if (photoPreview) {
        if (item.image_url) {
            photoPreview.innerHTML = `<img src="${item.image_url}" style="width:100%;height:100%;object-fit:cover;border-radius:10px;" onerror="this.parentElement.innerHTML='<i class=\'fas fa-camera\'></i>'"`  + '>';
        } else {
            photoPreview.innerHTML = '<i class="fas fa-camera"></i>';
        }
    }
    if (photoHint) photoHint.textContent = item.image_url ? 'Click to replace photo' : 'Upload or replace photo';

    // Clear any previously-selected file
    const fileInput = document.getElementById('quickEditOptionImage');
    if (fileInput) fileInput.value = '';

    safeOpenModal('quickEditOptionModal', true);
};

window.closeQuickEditOptionModal = function () {
    safeCloseModal('quickEditOptionModal');
};

window.submitQuickEditOption = async function (e) {
    e.preventDefault();
    const type = document.getElementById('quickEditOptionType')?.value || 'menu';
    const id = parseInt(document.getElementById('quickEditOptionId')?.value || 0, 10);
    const name = (document.getElementById('quickEditOptionName')?.value || '').trim();
    const category = document.getElementById('quickEditOptionCategory')?.value || '';
    const unit = document.getElementById('quickEditOptionUnit')?.value || '';
    const price = type === 'menu' ? 0 : (parseFloat(document.getElementById('quickEditOptionPrice')?.value || 0) || 0);
    const desc = (document.getElementById('quickEditOptionDescription')?.value || '').trim();

    if (!name || !id) {
        alert('Please enter an item name.');
        return;
    }

    const btn = document.getElementById('btnQuickEditSubmit');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Saving...</span>';
    }

    try {
        // Use FormData so image file can be included
        const formData = new FormData();
        formData.append('name', name);
        formData.append('category', category);
        formData.append('price', price);
        formData.append('unit_type', unit);
        formData.append('description', desc);
        const fileInput = document.getElementById('quickEditOptionImage');
        if (fileInput && fileInput.files && fileInput.files[0]) {
            formData.append('image', fileInput.files[0]);
        }

        const res = await fetch(`/caterer/api/catalogs/quick-edit/${type}/${id}`, {
            method: 'POST',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            body: formData
        });

        const data = await res.json();
        if (!res.ok || data.status !== 'success') {
            throw new Error(extractErrorMessage(data, 'Failed to update item'));
        }

        const updatedItem = data.item;
        const list = window.inclusionsCatalog[type] || [];
        const idx = list.findIndex(i => Number(i.id) === Number(id));
        if (idx !== -1) {
            list[idx] = { ...list[idx], ...updatedItem };
        }

        // Update UI
        renderCustomizableCatalogs();
        renderReviewCustomizable();

        // Close modal
        safeCloseModal('quickEditOptionModal');

        if (window.showToast) {
            window.showToast(`Updated "${updatedItem.name}" successfully!`, 'success');
        }
    } catch (err) {
        console.error('submitQuickEditOption error:', err);
        alert(err.message || 'An error occurred while updating.');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check"></i> <span>Save Changes</span>';
        }
    }
};

// ---- Photo preview handler for add/edit catalog item modals ----
window.previewQuickCatalogPhoto = function (mode, event) {
    const file = event && event.target && event.target.files && event.target.files[0];
    if (!file) return;
    const previewId = mode === 'edit' ? 'quickEditOptionPhotoPreview' : 'quickAddOptionPhotoPreview';
    const hintId    = mode === 'edit' ? 'quickEditOptionPhotoHint'    : 'quickAddOptionPhotoHint';
    const preview = document.getElementById(previewId);
    const hint    = document.getElementById(hintId);
    const reader  = new FileReader();
    reader.onload = function (e) {
        if (preview) {
            preview.innerHTML = `<img src="${e.target.result}" style="width:100%;height:100%;object-fit:cover;border-radius:10px;">`;
        }
        if (hint) hint.textContent = file.name;
    };
    reader.readAsDataURL(file);
};

window.quickDeleteCatalogItem = async function (type, id, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const list = window.inclusionsCatalog[type] || [];
    const item = list.find(i => Number(i.id) === Number(id));
    const itemName = item ? item.name : 'this item';

    if (!confirm(`Are you sure you want to remove "${itemName}" from your catalog?`)) {
        return;
    }

    try {
        const res = await fetch(`/caterer/api/catalogs/quick-delete/${type}/${id}`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        const data = await res.json();
        if (!res.ok || data.status !== 'success') {
            throw new Error(extractErrorMessage(data, 'Failed to delete item'));
        }

        // Remove from local catalog
        const idx = list.findIndex(i => Number(i.id) === Number(id));
        if (idx !== -1) {
            list.splice(idx, 1);
        }

        // Unselect if selected
        const numId = Number(id);
        if (type === 'menu') customizableMenuIds.delete(numId);
        else if (type === 'service') customizableServiceIds.delete(numId);

        // Update UI
        renderCustomizableCatalogs();
        syncCustomizableSelectionRules();
        renderReviewCustomizable();

        if (window.showToast) {
            window.showToast(`"${itemName}" removed from catalog.`, 'info');
        }
    } catch (err) {
        console.error('quickDeleteCatalogItem error:', err);
        alert(err.message || 'An error occurred while deleting.');
    }
};
