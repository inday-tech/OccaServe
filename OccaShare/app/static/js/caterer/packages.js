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
        if (msgs.length) return msgs.join('\r\n');
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

    const pricingModeGroup = document.getElementById('pkgPricingModeGroup');
    if (pricingModeGroup) {
        pricingModeGroup.classList.remove('form-grid-full');
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
        if (pricingLabelText) pricingLabelText.textContent = 'Starting price per guest (₱)';
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
        if (pricingLabelText) pricingLabelText.textContent = 'Package price (base total)';
        if (pricingUnitHint) pricingUnitHint.textContent = 'Included guests × Business Settings rate per guest.';
        if (priceInput) {
            priceInput.readOnly = true;
            priceInput.placeholder = '0.00';
            priceInput.required = true;
        }
    } else {
        if (pricingLabelText) pricingLabelText.textContent = 'Price per guest (₱)';
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
    customizableCategoryRemovalCredits = {};
    lastMenuQuery = '';
    lastServiceQuery = '';
    lastEquipmentQuery = '';
    lastMenuCategory = '';
    lastServiceCategory = '';
    lastEquipmentCategory = '';
    const mSearch = document.getElementById('custMenuSearchInput');
    const sSearch = document.getElementById('custServiceSearchInput');
    const eSearch = document.getElementById('custEquipmentSearchInput');
    if (mSearch) mSearch.value = '';
    if (sSearch) sSearch.value = '';
    if (eSearch) eSearch.value = '';
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
        lastEquipmentQuery = '';
        lastMenuCategory = '';
        lastServiceCategory = '';
        lastEquipmentCategory = '';
        const mSearchEdit = document.getElementById('custMenuSearchInput');
        const sSearchEdit = document.getElementById('custServiceSearchInput');
        const eSearchEdit = document.getElementById('custEquipmentSearchInput');
        if (mSearchEdit) mSearchEdit.value = '';
        if (sSearchEdit) sSearchEdit.value = '';
        if (eSearchEdit) eSearchEdit.value = '';
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
                customizableCategoryRemovalCredits = rules.category_removal_credits && typeof rules.category_removal_credits === 'object'
                    ? Object.assign({}, rules.category_removal_credits) : {};
            }
        } else {
            customizableCategoryQuotas = {};
            customizableCategoryRemovalCredits = {};
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
            const extraRateInput = form.elements.namedItem('additional_guest_price');
            const extraRateText = String(extraRateInput?.value || '').trim();
            const extraRate = Number(extraRateText);
            const rateFloor = Math.max(0, Number(window.CATERER_STARTING_PRICE) || 0);
            if (extraRateText && (!/^\d{1,8}(?:\.\d{1,2})?$/.test(extraRateText)
                || !Number.isFinite(extraRate) || extraRate <= 0 || extraRate < rateFloor || extraRate > 99999999.99)) {
                addError(extraRateInput, `Enter a valid extra guest rate of at least ₱${rateFloor.toFixed(2)}.`);
            }
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
        const capacity = mode === 'fixed'
            ? Number(value('base_pax')) >= globalMinPax
            : Number(value('min_guests')) >= globalMinPax;
        return Boolean(value('name')) && packageNameValidationStatus === 'valid'
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
    const btnDoneText = document.getElementById('btnInclusionSaveDoneText');
    const desc = document.getElementById('customInclusionDescription');
    const searchInput = document.getElementById('inclusionItemSearch');
    const doneButton = document.getElementById('btnInclusionSaveDone');

    if (editIndexEl) editIndexEl.value = '-1';
    if (title) title.innerText = 'Add package item';
    if (subtitle) subtitle.innerText = 'Choose an item from your catalog.';
    if (btnDoneText) btnDoneText.innerText = 'Add to package';
    if (doneButton) {
        doneButton.disabled = true;
        doneButton.hidden = true;
    }
    if (desc) desc.value = '';
    const categorySelect = document.getElementById('customInclusionCategory');
    if (categorySelect) categorySelect.disabled = false;
    if (searchInput) {
        searchInput.value = '';
        searchInput.setAttribute('aria-expanded', 'false');
    }
    setInclusionCatalogOptionsOpen(false);
    resetInclusionImagePicker('');

    // Ensure catalog is populated across all item types
    if (!window.inclusionsCatalog || !window.inclusionsCatalog.equipment || !window.inclusionsCatalog.menu || !window.inclusionsCatalog.service) {
        await window.fetchInclusionsCatalog();
    }

    // Start with only the requested choices; legacy equipment inclusions remain editable.
    setInclusionCategoryChoices(true);
    const catSelect = document.getElementById('customInclusionCategory');
    if (catSelect) catSelect.disabled = false;
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
    const catSelect = document.getElementById('customInclusionCategory');
    if (catSelect && catSelect.value !== normType) {
        catSelect.value = normType;
    }

    const lblItem = document.getElementById('lblInclusionItem');
    const btnCreateCatalog = document.getElementById('btnCreateNewCatalogItem');
    const searchInput = document.getElementById('inclusionItemSearch');
    const catalogSection = document.querySelector('#addInclusionModal .inclusion-catalog-section');
    const descriptionSection = document.querySelector('#addInclusionModal .inclusion-description-section');
    const photoSection = document.querySelector('#addInclusionModal .inclusion-photo-section');
    const doneButton = document.getElementById('btnInclusionSaveDone');
    const doneText = document.getElementById('btnInclusionSaveDoneText');

    if (!normType) {
        if (catalogSection) catalogSection.style.display = 'none';
        if (descriptionSection) descriptionSection.style.display = 'none';
        if (photoSection) photoSection.style.display = 'none';
        if (doneButton) {
            doneButton.disabled = true;
            doneButton.hidden = true;
        }
        if (doneText) doneText.innerText = 'Add to package';
        const itemIdEl = document.getElementById('customInclusionItemId');
        const nameEl = document.getElementById('customInclusionName');
        if (itemIdEl) itemIdEl.value = '';
        if (nameEl) nameEl.value = '';
        const searchInput = document.getElementById('inclusionItemSearch');
        if (searchInput) {
            searchInput.value = '';
            searchInput.setAttribute('aria-expanded', 'false');
        }
        setInclusionCatalogOptionsOpen(false);
        if (!inclusionImageFile) resetInclusionImagePicker('');
        return;
    }
    if (catalogSection) catalogSection.style.display = 'block';
    if (descriptionSection) descriptionSection.style.display = 'block';
    if (photoSection) photoSection.style.display = 'block';
    if (doneButton) {
        doneButton.disabled = true;
        doneButton.hidden = false;
    }
    const isEditing = Number(document.getElementById('customInclusionEditIndex')?.value ?? -1) >= 0;
    if (doneText) doneText.innerText = isEditing ? 'Save changes' : 'Add to package';

    // Update UI text and placeholders
    if (lblItem) lblItem.innerHTML = `Catalog item <span style="color: #ef4444;">*</span>`;
    if (btnCreateCatalog) {
        btnCreateCatalog.setAttribute('aria-label', `Create new ${normType.toLowerCase()}`);
        btnCreateCatalog.title = `Create new ${normType.toLowerCase()}`;
    }
    if (btnCreateCatalog) btnCreateCatalog.style.display = 'inline-flex';
    if (searchInput) {
        searchInput.placeholder = `Search ${normType.toLowerCase()} catalog...`;
        searchInput.value = '';
    }

    const itemIdEl = document.getElementById('customInclusionItemId');
    const nameEl = document.getElementById('customInclusionName');
    if (itemIdEl) itemIdEl.value = '';
    if (nameEl) nameEl.value = '';
    resetInclusionImagePicker('');

    // Populate the searchable picker.
    window.populateCatalogSelect(normType, '', preselectId);
};

// Populate the combined search-and-select catalog picker.
window.populateCatalogSelect = function (type, filterQuery = '', preselectId = null) {
    const searchInput = document.getElementById('inclusionItemSearch');
    const optionsContainer = document.getElementById('inclusionCatalogOptions');
    if (!searchInput || !optionsContainer) return;

    const catalogKey = type.toLowerCase();
    const items = window.inclusionsCatalog[catalogKey] || [];
    const query = (filterQuery || '').toLowerCase().trim();

    const filtered = query ? items.filter(i => {
        const n = (i.name || '').toLowerCase();
        const c = (i.category || '').toLowerCase();
        return n.includes(query) || c.includes(query);
    }) : items;

    let html = '';
    if (filtered.length === 0) {
        html = `<div class="inclusion-catalog-empty" role="status">${items.length ? 'No matching items.' : 'No catalog items available.'}</div>`;
    } else {
        html = filtered.map(item => `
            <button type="button" class="inclusion-catalog-option" role="option"
                aria-selected="${preselectId && String(item.id) === String(preselectId) ? 'true' : 'false'}"
                data-item-id="${Number(item.id)}"
                onmousedown="event.preventDefault()"
                onclick="window.handleCatalogItemSelected('${Number(item.id)}')">
                ${escapeHtml(item.name)}
            </button>
        `).join('');
    }

    optionsContainer.innerHTML = html;

    if (preselectId) {
        window.handleCatalogItemSelected(String(preselectId));
    }
};

window.showInclusionCatalogOptions = function () {
    const type = document.getElementById('customInclusionCategory')?.value || '';
    if (!type) return;
    const input = document.getElementById('inclusionItemSearch');
    const selectedId = document.getElementById('customInclusionItemId')?.value || '';
    window.populateCatalogSelect(type, selectedId ? '' : (input?.value || ''));
    setInclusionCatalogOptionsOpen(true);
};

function setInclusionCatalogOptionsOpen(open) {
    const picker = document.querySelector('#addInclusionModal .inclusion-catalog-picker');
    const options = document.getElementById('inclusionCatalogOptions');
    const input = document.getElementById('inclusionItemSearch');
    const toggle = document.querySelector('#addInclusionModal .inclusion-catalog-picker-toggle');
    if (!picker || !options) return;

    if (!open) {
        options.hidden = true;
        picker.classList.remove('opens-up');
        if (input) input.setAttribute('aria-expanded', 'false');
        if (toggle) toggle.setAttribute('aria-expanded', 'false');
        return;
    }

    const modalBody = document.querySelector('#addInclusionModal .inclusion-modal-body');
    const pickerRect = picker.getBoundingClientRect();
    const bodyRect = modalBody?.getBoundingClientRect();
    const availableBelow = Math.max(0, Math.floor((bodyRect?.bottom ?? window.innerHeight) - pickerRect.bottom - 10));
    const availableAbove = Math.max(0, Math.floor(pickerRect.top - (bodyRect?.top ?? 0) - 10));
    const openUp = availableBelow < 150 && availableAbove > availableBelow;
    picker.classList.toggle('opens-up', openUp);
    options.style.maxHeight = `${Math.max(80, Math.min(220, openUp ? availableAbove : availableBelow))}px`;
    options.hidden = false;
    if (input) input.setAttribute('aria-expanded', 'true');
    if (toggle) toggle.setAttribute('aria-expanded', 'true');
}

window.toggleInclusionCatalogOptions = function () {
    const options = document.getElementById('inclusionCatalogOptions');
    if (!options || options.hidden) {
        window.showInclusionCatalogOptions();
        document.getElementById('inclusionItemSearch')?.focus();
        return;
    }
    setInclusionCatalogOptionsOpen(false);
};

window.handleInclusionCatalogKeydown = function (event) {
    const options = document.getElementById('inclusionCatalogOptions');
    if (event.key === 'Escape') {
        setInclusionCatalogOptionsOpen(false);
    } else if (event.key === 'ArrowDown') {
        if (options?.hidden) window.showInclusionCatalogOptions();
        options?.querySelector('.inclusion-catalog-option')?.focus();
        event.preventDefault();
    } else if (event.key === 'Enter' && options && !options.hidden) {
        const firstOption = options.querySelector('.inclusion-catalog-option');
        if (firstOption) {
            event.preventDefault();
            firstOption.click();
        }
    }
};

// Filter catalog items through the combined picker field.
window.filterInclusionCatalogItems = function (query) {
    const catSelect = document.getElementById('customInclusionCategory');
    const type = catSelect ? catSelect.value : '';
    const itemIdEl = document.getElementById('customInclusionItemId');
    const nameEl = document.getElementById('customInclusionName');
    const doneButton = document.getElementById('btnInclusionSaveDone');
    if (itemIdEl) itemIdEl.value = '';
    if (nameEl) nameEl.value = '';
    if (doneButton) doneButton.disabled = true;
    if (!inclusionImageFile) resetInclusionImagePicker('');
    window.populateCatalogSelect(type, query);
    setInclusionCatalogOptionsOpen(true);
};

// Handle selection of a catalog item
window.handleCatalogItemSelected = function (selectedId) {
    const itemIdEl = document.getElementById('customInclusionItemId');
    const nameEl = document.getElementById('customInclusionName');
    const doneButton = document.getElementById('btnInclusionSaveDone');
    const type = document.getElementById('customInclusionCategory')?.value || '';
    const catalogKey = type.toLowerCase();
    const item = (window.inclusionsCatalog[catalogKey] || []).find(entry => Number(entry.id) === Number(selectedId));
    const searchInput = document.getElementById('inclusionItemSearch');
    const optionsContainer = document.getElementById('inclusionCatalogOptions');

    if (!selectedId || !item) {
        if (itemIdEl) itemIdEl.value = '';
        if (nameEl) nameEl.value = '';
        if (doneButton) doneButton.disabled = true;
        if (!inclusionImageFile) resetInclusionImagePicker('');
        return;
    }

    const itemName = item.name || '';

    if (itemIdEl) itemIdEl.value = selectedId;
    if (searchInput) {
        searchInput.value = itemName;
        searchInput.setAttribute('aria-expanded', 'false');
    }
    if (nameEl) {
        nameEl.value = itemName;
        nameEl.style.borderColor = '';
    }
    setInclusionCatalogOptionsOpen(false);
    optionsContainer?.querySelectorAll('.inclusion-catalog-option').forEach(option => {
        option.setAttribute('aria-selected', Number(option.dataset.itemId) === Number(selectedId) ? 'true' : 'false');
    });

    if (doneButton) doneButton.disabled = false;

    // Show the catalog item's existing photo unless the user already picked a new one
    if (!inclusionImageFile) {
        resetInclusionImagePicker(findCatalogImage(type, selectedId, itemName));
    }

};

// Edit Existing Inclusion
window.editInclusion = async function (index) {
    if (typeof index !== 'number' || index < 0 || index >= packageInclusions.length) return;
    const item = packageInclusions[index];

    const editIndexEl = document.getElementById('customInclusionEditIndex');
    const title = document.getElementById('inclusionModalTitle');
    const subtitle = document.getElementById('inclusionModalSubtitle');
    const btnDoneText = document.getElementById('btnInclusionSaveDoneText');
    const desc = document.getElementById('customInclusionDescription');

    if (editIndexEl) editIndexEl.value = String(index);
    if (title) title.innerText = 'Edit package item';
    if (subtitle) subtitle.innerText = 'Update the selected item or its package notes.';
    if (btnDoneText) btnDoneText.innerText = 'Save changes';
    if (desc) desc.value = item.description || '';

    const catalogType = getPackageInclusionCatalogType(item);
    const itemType = catalogType.charAt(0).toUpperCase() + catalogType.slice(1);

    // Ensure catalog is populated
    if (!Array.isArray(window.inclusionsCatalog[catalogType]) || window.inclusionsCatalog[catalogType].length === 0) {
        await window.fetchInclusionsCatalog();
    }

    window.handleInclusionTypeChange(itemType, item.item_id);
    const catalogItems = window.inclusionsCatalog[catalogType] || [];
    const linkedCatalogItem = item.item_id
        ? catalogItems.find(entry => Number(entry.id) === Number(item.item_id))
        : null;
    if (linkedCatalogItem) {
        window.openQuickEditModal(catalogType, linkedCatalogItem.id);
        return;
    }

    // If item_id wasn't in catalog yet, set name manually
    const nameEl = document.getElementById('customInclusionName');
    if (nameEl) nameEl.value = item.name || '';

    setInclusionCategoryChoices(itemType === 'Equipment');
    const typeSelect = document.getElementById('customInclusionCategory');
    if (typeSelect) typeSelect.disabled = true;
    const catalogSection = document.querySelector('#addInclusionModal .inclusion-catalog-section');
    if (catalogSection) catalogSection.style.display = 'none';
    const photoSection = document.querySelector('#addInclusionModal .inclusion-photo-section');
    if (photoSection) photoSection.style.display = 'none';
    resetInclusionImagePicker(item.image_url || findCatalogImage(itemType, item.item_id, item.name));

    safeOpenModal('addInclusionModal', true);
};

// Close Modal
window.closeAddInclusionModal = function () {
    safeCloseModal('addInclusionModal');
    const typeSelect = document.getElementById('customInclusionCategory');
    if (typeSelect) typeSelect.disabled = false;
    const catalogSection = document.querySelector('#addInclusionModal .inclusion-catalog-section');
    if (catalogSection) catalogSection.style.display = 'none';
    const photoSection = document.querySelector('#addInclusionModal .inclusion-photo-section');
    if (photoSection) photoSection.style.display = 'none';
};

// Save Inclusion (Add or Edit)
window.saveInclusion = async function () {
    const editIndexEl = document.getElementById('customInclusionEditIndex');
    const catSelect = document.getElementById('customInclusionCategory');
    const searchInput = document.getElementById('inclusionItemSearch');
    const itemIdEl = document.getElementById('customInclusionItemId');
    const nameEl = document.getElementById('customInclusionName');
    const descEl = document.getElementById('customInclusionDescription');

    const selectedType = catSelect ? catSelect.value : 'Equipment';
    if (!['Menu', 'Service', 'Equipment'].includes(selectedType)) {
        if (catSelect) catSelect.focus();
        return;
    }
    const itemId = itemIdEl ? itemIdEl.value : '';
    let nameVal = (nameEl ? nameEl.value : '').trim();

    // Validation: Item must be chosen
    if (!nameVal) {
        if (searchInput) {
            searchInput.style.borderColor = '#ef4444';
            searchInput.focus();
        }
        return;
    }
    if (searchInput) searchInput.style.borderColor = '';

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
        const saveButton = document.getElementById('btnInclusionSaveDone');
        const hint = document.getElementById('inclusionPhotoHint');
        if (saveButton) saveButton.disabled = true;
        if (hint) { hint.textContent = 'Uploading photo...'; hint.style.color = '#64748b'; }
        try {
            imageUrl = await uploadInclusionImage(selectedType, parseInt(itemId, 10));
            inclusionImageFile = null;
            inclusionCurrentImage = imageUrl;
        } catch (err) {
            if (hint) { hint.textContent = (err && err.message) || 'Failed to upload the photo.'; hint.style.color = '#dc2626'; }
            return;
        } finally {
            if (saveButton) saveButton.disabled = false;
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
        const existing = packageInclusions[editIndex];
        packageInclusions[editIndex] = {
            ...existing,
            description: descVal
        };
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

        safeCloseModal('addInclusionModal');
    }
};

function getPackageInclusionCatalogType(item) {
    const itemType = String(item.type || '').toLowerCase();
    if (itemType.includes('equipment')) return 'equipment';
    if (itemType.includes('service')) return 'service';
    const category = String(item.category || '').toLowerCase();
    if (category.includes('equipment')) return 'equipment';
    if (category.includes('service')) return 'service';
    return 'menu';
}

window.archiveInclusion = async function (index, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    if (!Number.isInteger(index) || index < 0 || index >= packageInclusions.length) return;
    const item = packageInclusions[index];
    if (!item.item_id) {
        alert('This item is not linked to a catalog entry, so it cannot be archived. Use Remove to take it out of this package.');
        return;
    }
    await window.quickDeleteCatalogItem(getPackageInclusionCatalogType(item), item.item_id, event);
};

// Remove an unlinked item from this package only.
window.removeInclusion = function (index) {
    if (typeof index !== 'number' || index < 0 || index >= packageInclusions.length) return;
    if (!confirm(`Remove "${packageInclusions[index].name}" from this package?`)) return;
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
    if (!['Menu', 'Menu / Food', 'Service', 'Equipment'].includes(type)) return;
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

    const quickType = (type === 'Menu' || type === 'Menu / Food')
        ? 'menu'
        : type.toLowerCase();
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
        if (createdName && window.showToast) {
            window.showToast(`"${createdName}" is selected. Add it to the package to continue.`, 'success');
        }
    }, 150);
};

// Render clean, professional list / card layout for inclusions
function renderInclusionsList() {
    const container = document.getElementById('inclusionsListGrouped');
    const totalBadge = document.getElementById('inclusionsTotalBadge');
    if (!container) return;

    const totalCount = packageInclusions.length;
    const groups = [
        { type: 'Menu', label: 'Menu / Food', icon: 'fas fa-utensils', items: [] },
        { type: 'Service', label: 'Services', icon: 'fas fa-concierge-bell', items: [] },
        { type: 'Equipment', label: 'Equipment', icon: 'fas fa-chair', items: [] }
    ];
    const groupByType = Object.fromEntries(groups.map(group => [group.type, group]));
    packageInclusions.forEach((item, index) => {
        const type = getPackageInclusionCatalogType(item);
        const groupType = type.charAt(0).toUpperCase() + type.slice(1);
        groupByType[groupType].items.push({ item, index });
    });
    // Update Header Badge
    if (totalBadge) {
        totalBadge.innerText = `${totalCount} item${totalCount === 1 ? '' : 's'}`;
        totalBadge.style.background = totalCount > 0 ? '#e2e8f0' : '#f1f5f9';
        totalBadge.style.color = totalCount > 0 ? '#0f172a' : '#475569';
    }

    // Update the total count.
    if (totalCount === 0) {
        container.innerHTML = `
            <div class="inclusions-empty-state" style="text-align: center; padding: 3.5rem 2rem; background: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 16px; margin: 0.5rem 0;">
                <div style="width: 56px; height: 56px; border-radius: 50%; background: #e2e8f0; color: #64748b; display: inline-flex; align-items: center; justify-content: center; font-size: 1.5rem; margin-bottom: 1rem;">
                    <i class="fas fa-layer-group"></i>
                </div>
                <h4 style="font-size: 1.1rem; font-weight: 800; color: #1e293b; margin: 0 0 0.4rem 0;">No inclusions added yet</h4>
                <p style="font-size: 0.85rem; color: #64748b; max-width: 420px; margin: 0 auto 1.5rem auto; line-height: 1.5;">Add the menu items, services, and equipment included in this package.</p>
                <button type="button" class="btn-primary-pro" onclick="window.openAddInclusionModal()"
                    style="display: inline-flex; align-items: center; gap: 8px; padding: 0.65rem 1.25rem; font-size: 0.875rem; font-weight: 800; border-radius: 10px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
                    <i class="fas fa-plus"></i>
                    <span>Add item</span>
                </button>
            </div>
        `;
        return;
    }

    const groupStyles = {
        Menu: { accent: '#16a34a', iconBg: '#f0fdf4' },
        Service: { accent: '#2563eb', iconBg: '#eff6ff' },
        Equipment: { accent: '#ea580c', iconBg: '#fff7ed' }
    };
    container.innerHTML = groups.filter(group => group.items.length).map(group => {
        const style = groupStyles[group.type];
        const cards = group.items.map(({ item, index }) => {
            const catalog = (window.inclusionsCatalog && window.inclusionsCatalog[group.type.toLowerCase()]) || [];
            const catalogItem = item.item_id
                ? catalog.find(entry => Number(entry.id) === Number(item.item_id))
                : catalog.find(entry => String(entry.name || '').toLowerCase() === String(item.name || '').toLowerCase());
            const image = item.image_url || catalogItem?.image_url || '';
            const description = item.description || catalogItem?.description || '';
            const archiveButton = item.item_id && catalogItem
                ? `<button type="button" class="inclusion-action-button inclusion-archive-button" onclick="window.archiveInclusion(${index}, event)" title="Archive item" aria-label="Archive item">
                       <i class="fas fa-archive" aria-hidden="true"></i><span>Archive</span>
                   </button>`
                : `<button type="button" class="inclusion-action-button" onclick="window.removeInclusion(${index})" title="Remove from package" aria-label="Remove from package">
                       <i class="fas fa-minus-circle" aria-hidden="true"></i><span>Remove</span>
                   </button>`;
            return `
                <article class="inclusion-item-card">
                    <div class="inclusion-item-card-thumbnail" style="background:${style.iconBg};color:${style.accent};">
                        ${image
                            ? `<img src="${escapeHtml(image)}" alt="" onerror="this.style.display='none';this.parentElement.innerHTML='<i class=\\'${group.icon}\\'></i>';">`
                            : `<i class="${group.icon}"></i>`}
                    </div>
                    <div class="inclusion-item-card-details">
                        <strong>${escapeHtml(item.name)}</strong>
                        ${description ? `<p>${escapeHtml(description)}</p>` : ''}
                    </div>
                    <div class="inclusion-item-card-actions">
                        <button type="button" class="inclusion-action-button" onclick="window.editInclusion(${index})" title="Edit item" aria-label="Edit item">
                            <i class="fas fa-edit" aria-hidden="true"></i><span>Edit</span>
                        </button>
                        ${archiveButton}
                    </div>
                </article>
            `;
        }).join('');
        return `
            <section class="inclusion-category-group" aria-label="${group.label}">
                <header>
                    <h5 style="color:${style.accent};"><i class="${group.icon}" aria-hidden="true"></i>${group.label}</h5>
                    <span>${group.items.length}</span>
                </header>
                <div class="inclusion-category-items">${cards}</div>
            </section>
        `;
    }).join('');
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
let customizableCategoryRemovalCredits = {};

let lastMenuQuery = '';
let lastServiceQuery = '';
let lastEquipmentQuery = '';
let lastMenuCategory = '';
let lastServiceCategory = '';
let lastEquipmentCategory = '';
const equipmentCategoryOptions = [
    'Chairs', 'Tables', 'Furniture Sets', 'Tents & Canopies', 'Stage & Platform',
    'Audio Equipment', 'Lighting Equipment', 'Visual Equipment', 'Buffet Equipment',
    'Tableware & Utensils', 'Decorations', 'Event Styling', 'Miscellaneous', 'Others'
];

function catalogCategorySuggestions(type) {
    return document.getElementById(`cust${type.charAt(0).toUpperCase() + type.slice(1)}CategoryOptions`);
}

function catalogSearchInput(type) {
    return document.getElementById(`cust${type.charAt(0).toUpperCase() + type.slice(1)}SearchInput`);
}

function getCatalogCategory(type) {
    if (type === 'menu') return lastMenuCategory;
    if (type === 'service') return lastServiceCategory;
    return lastEquipmentCategory;
}

function setCatalogCategory(type, category) {
    if (type === 'menu') lastMenuCategory = category;
    else if (type === 'service') lastServiceCategory = category;
    else lastEquipmentCategory = category;
}

function populateCatalogCategorySuggestions() {
    const categoryFallback = {
        menu: 'Uncategorized',
        service: 'Service',
        equipment: 'Equipment'
    };
    ['menu', 'service', 'equipment'].forEach(type => {
        const suggestions = catalogCategorySuggestions(type);
        if (!suggestions) return;

        const categories = [...new Set([
            ...(type === 'equipment' ? equipmentCategoryOptions : []),
            ...(window.inclusionsCatalog[type] || [])
                .map(item => String(item.category || '').trim() || categoryFallback[type])
        ])].sort((a, b) => a.localeCompare(b));

        suggestions.innerHTML = categories
            .map(category => `<option value="${escapeHtml(category)}"></option>`).join('');
        const selectedCategory = getCatalogCategory(type);
        if (selectedCategory && !categories.includes(selectedCategory)) {
            const input = catalogSearchInput(type);
            if (input && input.value === selectedCategory) input.value = '';
            setCatalogCategory(type, '');
        }
    });
}

function updateCatalogActionLabels() {
    const labels = {
        menu: 'Menu',
        service: 'Service',
        equipment: 'Equipment'
    };
    Object.entries(labels).forEach(([type, label]) => {
        const element = document.getElementById(`cust${label}ActionLabel`);
        if (element) {
            const hasCatalogItems = (window.inclusionsCatalog[type] || []).length > 0;
            element.textContent = `${hasCatalogItems ? 'Add' : 'Create'} ${label.toLowerCase()}`;
        }
    });
}

function getCustomizableMenuCategoryCounts() {
    const counts = {};
    (window.inclusionsCatalog.menu || [])
        .filter(item => customizableMenuIds.has(Number(item.id)))
        .forEach(item => {
            const category = String(item.category || '').trim() || 'Uncategorized';
            counts[category] = (counts[category] || 0) + 1;
        });
    return counts;
}

function updateInlineMenuCategoryQuotas() {
    const categoryCounts = getCustomizableMenuCategoryCounts();
    document.querySelectorAll('#customizableMenuList .menu-category-heading').forEach(heading => {
        const category = heading.dataset.category || '';
        const available = categoryCounts[category] || 0;
        const input = heading.querySelector('input[type="number"]');
        const offered = heading.querySelector('.menu-category-offered');
        if (offered) offered.textContent = String(available);
        if (input) {
            input.max = String(available);
            input.disabled = available === 0;
            const quota = Number(customizableCategoryQuotas[category]);
            input.value = Number.isInteger(quota) && quota >= 1 && quota <= available ? String(quota) : '';
        }
    });
}

window.toggleCustomizableItem = function (type, id, checked) {
    const numId = Number(id);
    if (type === 'menu') {
        if (checked) customizableMenuIds.add(numId);
        else customizableMenuIds.delete(numId);
        updateCustomizableCounters('menu');
        updateInlineMenuCategoryQuotas();
        renderCategoryQuotas();
    } else if (type === 'service') {
        if (checked) customizableServiceIds.add(numId);
        else customizableServiceIds.delete(numId);
        updateCustomizableCounters('service');
    } else if (type === 'equipment') {
        if (checked) customizableEquipmentIds.add(numId);
        else customizableEquipmentIds.delete(numId);
        updateCustomizableCounters('equipment');
    }
    syncCustomizableSelectionRules();
    updatePackageWizardControls();
};

window.toggleAllCustomizableCatalog = function (type) {
    const catalog = window.inclusionsCatalog[type] || [];
    const selectedIds = type === 'menu'
        ? customizableMenuIds
        : type === 'service'
            ? customizableServiceIds
            : customizableEquipmentIds;
    const allSelected = catalog.length > 0 && catalog.every(item => selectedIds.has(Number(item.id)));
    const selectAll = !allSelected;
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
    } else if (type === 'equipment') {
        if (selectAll) catalog.forEach(i => customizableEquipmentIds.add(Number(i.id)));
        else customizableEquipmentIds.clear();
        renderCustomizableEquipment(lastEquipmentQuery);
        updateCustomizableCounters('equipment');
    }
    syncCustomizableSelectionRules();
    updatePackageWizardControls();
};

window.filterCustomizableCatalog = function (type, query) {
    const categories = (window.inclusionsCatalog[type] || []).map(item => {
        const fallback = type === 'menu' ? 'Uncategorized' : (type === 'service' ? 'Service' : 'Equipment');
        return String(item.category || '').trim() || fallback;
    });
    const matchedCategory = categories.find(category =>
        category.toLowerCase() === String(query || '').trim().toLowerCase()
    ) || '';
    const searchQuery = matchedCategory ? '' : query;
    setCatalogCategory(type, matchedCategory);

    if (type === 'menu') {
        lastMenuQuery = searchQuery;
        renderCustomizableMenu(searchQuery);
    } else if (type === 'service') {
        lastServiceQuery = searchQuery;
        renderCustomizableServices(searchQuery);
    } else if (type === 'equipment') {
        lastEquipmentQuery = searchQuery;
        renderCustomizableEquipment(searchQuery);
    }
};

function updateCustomizableCounters(type) {
    const menuBadge = document.getElementById('custMenuCountBadge');
    const serviceBadge = document.getElementById('custServiceCountBadge');
    const equipmentBadge = document.getElementById('custEquipmentCountBadge');
    const totalBadge = document.getElementById('custTotalAvailableBadge');

    if (menuBadge) menuBadge.innerText = `${customizableMenuIds.size} selected`;
    if (serviceBadge) serviceBadge.innerText = `${customizableServiceIds.size} selected`;
    if (equipmentBadge) equipmentBadge.innerText = `${customizableEquipmentIds.size} selected`;
    document.querySelectorAll('[data-catalog-toggle]').forEach(button => {
        const type = button.dataset.catalogToggle;
        const catalog = (window.inclusionsCatalog && window.inclusionsCatalog[type]) || [];
        const selectedIds = type === 'menu'
            ? customizableMenuIds
            : type === 'service'
                ? customizableServiceIds
                : customizableEquipmentIds;
        const allSelected = catalog.length > 0 && catalog.every(item => selectedIds.has(Number(item.id)));
        button.textContent = allSelected ? 'Deselect all' : 'Select all';
        button.setAttribute('aria-pressed', String(allSelected));
        button.disabled = catalog.length === 0;
    });
    updateCatalogActionLabels();

    if (totalBadge) {
        const total = customizableMenuIds.size + customizableServiceIds.size + customizableEquipmentIds.size;
        totalBadge.innerText = `${total} Option${total === 1 ? '' : 's'} Available`;
    }
}

window.renderCustomizableCatalogs = function () {
    populateCatalogCategorySuggestions();
    renderCustomizableMenu(lastMenuQuery);
    renderCustomizableServices(lastServiceQuery);
    renderCustomizableEquipment(lastEquipmentQuery);
    renderCategoryQuotas();
    updateCustomizableCounters();
    updatePackageWizardControls();
};

function renderCustomizableEquipment(query = '') {
    const container = document.getElementById('customizableEquipmentList');
    if (!container) return;
    const items = window.inclusionsCatalog.equipment || [];
    const q = (query || '').toLowerCase().trim();
    const filtered = items.filter(item => {
        const matchesQuery = !q || `${item.name || ''} ${item.category || ''}`.toLowerCase().includes(q);
        const matchesCategory = !lastEquipmentCategory || (String(item.category || '').trim() || 'Equipment') === lastEquipmentCategory;
        return matchesQuery && matchesCategory;
    });
    if (!filtered.length) {
        container.innerHTML = `<div class="customizable-equipment-empty">${q || lastEquipmentCategory ? 'No equipment matches these filters.' : 'No equipment in your catalog yet. Create equipment to get started.'}</div>`;
        return;
    }
    container.innerHTML = filtered.map(item => {
        const id = Number(item.id);
        const selected = customizableEquipmentIds.has(id);
        const price = Number(item.price || item.rental_price || 0);
        return `<div class="catalog-option-card equipment-option-card${selected ? ' is-selected' : ''}">
            <input type="checkbox" ${selected ? 'checked' : ''}
                onchange="const c = this.closest('.catalog-option-card'); c.classList.toggle('is-selected', this.checked); window.toggleCustomizableItem('equipment', ${id}, this.checked)">
            <div class="equipment-option-copy" onclick="const cb = this.parentElement.querySelector('input[type=checkbox]'); cb.checked = !cb.checked; cb.dispatchEvent(new Event('change'))">
                <strong>${escapeHtml(item.name || 'Equipment')}</strong>
            </div>
            <span class="equipment-option-price">₱${price.toLocaleString('en-PH', { minimumFractionDigits: 2 })}</span>
            <div class="catalog-option-actions">
                <button type="button" title="Edit Equipment" onclick="window.openQuickEditModal('equipment', ${id}, event)"
                        class="catalog-action-button" aria-label="Edit equipment">
                    <i class="fas fa-edit" aria-hidden="true"></i>
                </button>
                <button type="button" title="Archive Equipment" onclick="window.quickDeleteCatalogItem('equipment', ${id}, event)"
                        class="catalog-action-button catalog-archive-button" aria-label="Archive equipment">
                    <i class="fas fa-archive" aria-hidden="true"></i>
                </button>
            </div>
        </div>`;
    }).join('');
}

function renderCustomizableMenu(query = '') {
    const container = document.getElementById('customizableMenuList');
    if (!container) return;

    const items = window.inclusionsCatalog.menu || [];
    const q = (query || '').toLowerCase().trim();
    const filtered = items.filter(item => {
        const matchesQuery = !q || `${item.name || ''} ${item.category || ''}`.toLowerCase().includes(q);
        const matchesCategory = !lastMenuCategory || (String(item.category || '').trim() || 'Uncategorized') === lastMenuCategory;
        return matchesQuery && matchesCategory;
    });

    if (filtered.length === 0) {
        container.innerHTML = `
            <div style="grid-column: 1 / -1; padding: 2rem; text-align: center; color: #94a3b8; font-size: 0.85rem; background: #f8fafc; border-radius: 8px; border: 1.5px dashed #cbd5e1;">
                ${q || lastMenuCategory ? 'No menu items match these filters.' : 'No menu items in your catalog yet. Create a menu item to get started.'}
            </div>
        `;
        return;
    }

    const sorted = [...filtered].sort((a, b) => {
        const categoryOrder = String(a.category || 'Uncategorized').localeCompare(String(b.category || 'Uncategorized'));
        return categoryOrder || String(a.name || '').localeCompare(String(b.name || ''));
    });
    const selectedMenuCounts = getCustomizableMenuCategoryCounts();

    container.innerHTML = sorted.map((item, index) => {
        const id = Number(item.id);
        const isChecked = customizableMenuIds.has(id);
        const img = item.image_url || '';
        const desc = String(item.description || '').trim();
        const category = String(item.category || 'Uncategorized').trim() || 'Uncategorized';
        const previousCategory = index > 0
            ? (String(sorted[index - 1].category || 'Uncategorized').trim() || 'Uncategorized')
            : '';
        const selectedInCategory = selectedMenuCounts[category] || 0;
        const quotaValue = customizableCategoryQuotas[category];
        const quotaValid = Number.isInteger(Number(quotaValue)) && Number(quotaValue) >= 1 && Number(quotaValue) <= selectedInCategory;
        const removalCredit = Number(customizableCategoryRemovalCredits[category]) || 0;
        const encodedCategory = encodeURIComponent(category).replace(/'/g, '%27');
        const categoryHeading = category !== previousCategory
            ? `<div class="menu-category-heading" data-category="${escapeHtml(category)}" style="display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;">
                    <h5>${escapeHtml(category)}</h5>
                    <label class="menu-category-quota" title="Maximum number of choices customers can select in this category">
                        <span>Choose</span>
                        <input type="number" min="1" max="${selectedInCategory}" value="${quotaValid ? quotaValue : ''}"
                            aria-label="Maximum number of ${escapeHtml(category)} choices"
                            ${selectedInCategory ? '' : 'disabled'}
                            onchange="window.setCategoryQuota('${encodedCategory}', this.value)" />
                        <span>of <span class="menu-category-offered">${selectedInCategory}</span></span>
                    </label>
                    <label class="menu-category-removal-credit" style="display:flex;align-items:center;gap:6px;color:#64748b;font-size:.74rem;white-space:nowrap;">
                        <span>Credit if removed (₱/guest)</span>
                        <input type="number" min="0" max="999999" step="0.01" value="${removalCredit || ''}"
                            aria-label="Credit per guest if all ${escapeHtml(category)} choices are removed"
                            onchange="window.setCategoryRemovalCredit('${encodedCategory}', this.value)"
                            style="width:96px;min-height:34px;padding:5px 8px;border:1px solid #cbd5e1;border-radius:7px;" />
                    </label>
               </div>`
            : '';

        return `
            ${categoryHeading}
            <div style="display: flex; align-items: flex-start; gap: 10px; padding: 0.75rem 0.85rem; background: ${isChecked ? 'rgba(var(--primary-color-rgb, 255, 123, 84), 0.08)' : '#ffffff'}; border: 1.5px solid ${isChecked ? 'var(--primary-color, #f97316)' : '#e2e8f0'}; border-radius: 10px; transition: all 0.15s ease;"
                 class="catalog-option-card${isChecked ? ' is-selected' : ''}">
                <input type="checkbox" ${isChecked ? 'checked' : ''} 
                       onchange="const c = this.closest('.catalog-option-card'); c.classList.toggle('is-selected', this.checked); c.style.background = this.checked ? 'rgba(var(--primary-color-rgb, 255, 123, 84), 0.08)' : '#ffffff'; c.style.borderColor = this.checked ? 'var(--primary-color, #f97316)' : '#e2e8f0'; window.toggleCustomizableItem('menu', ${id}, this.checked);"
                       style="width: 16px; height: 16px; accent-color: var(--primary-color, #f97316); cursor: pointer; flex-shrink: 0; margin-top: 22px;" />
                <div style="width:56px;height:56px;border-radius:10px;overflow:hidden;background:#f1f5f9;flex-shrink:0;display:flex;align-items:center;justify-content:center;color:#cbd5e1;">
                    ${img
                        ? `<img src="${escapeHtml(img)}" alt="" onerror="this.style.display='none';this.parentElement.innerHTML='<i class=\\'fas fa-utensils\\'></i>';" style="width:100%;height:100%;object-fit:cover;">`
                        : `<i class="fas fa-utensils"></i>`}
                </div>
                <div style="flex: 1; min-width: 0; cursor: pointer;" onclick="const cb = this.parentElement.querySelector('input[type=checkbox]'); cb.checked = !cb.checked; cb.dispatchEvent(new Event('change'));">
                    <strong style="color: #0f172a; font-size: 0.88rem; line-height: 1.3; display:block;">${escapeHtml(item.name)}</strong>
                    ${desc.length > 2 ? `<p style="font-size: 0.75rem; color: #64748b; line-height: 1.4; margin: 6px 0 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${escapeHtml(desc)}</p>` : ''}
                </div>
                <div class="catalog-option-actions">
                    <button type="button" title="Edit Dish" onclick="window.openQuickEditModal('menu', ${id}, event)"
                            class="catalog-action-button" aria-label="Edit dish">
                        <i class="fas fa-edit" aria-hidden="true"></i>
                    </button>
                    <button type="button" title="Archive Dish" onclick="window.quickDeleteCatalogItem('menu', ${id}, event)"
                            class="catalog-action-button catalog-archive-button" aria-label="Archive dish">
                        <i class="fas fa-archive" aria-hidden="true"></i>
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
    const filtered = items.filter(item => {
        const matchesQuery = !q || `${item.name || ''} ${item.category || ''}`.toLowerCase().includes(q);
        const matchesCategory = !lastServiceCategory || (String(item.category || '').trim() || 'Service') === lastServiceCategory;
        return matchesQuery && matchesCategory;
    });

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="customizable-catalog-empty">
                ${q || lastServiceCategory ? 'No services match these filters.' : 'No services in your catalog yet. Create a service to get started.'}
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
        const priceHtml = price > 0
            ? `<span class="service-option-price" style="font-size: 0.75rem; font-weight: 800; color: var(--primary-color, #f97316); background: rgba(var(--primary-color-rgb, 255, 123, 84), 0.1); padding: 2px 7px; border-radius: 6px; white-space: nowrap;">
                   ₱${price.toLocaleString('en-PH', { maximumFractionDigits: 2 })}${unitText && unitText !== 'fixed' ? '/' + escapeHtml(unitText) : ''}
               </span>`
            : '';
        const img = item.image_url || '';
        const notes = String(item.notes || item.description || '')
            .split(/[\r\n,]+/)
            .map(note => note.replace(/^\s*[•*-]\s*/, '').trim())
            .filter(Boolean);
        const notesHtml = notes.length
            ? `<details class="package-service-notes" onclick="event.stopPropagation()">
                    <summary>Service notes (${notes.length})</summary>
                    <ul>${notes.map(note => `<li>${escapeHtml(note)}</li>`).join('')}</ul>
               </details>`
            : '';

        return `
            <div style="display: flex; align-items: flex-start; gap: 10px; padding: 0.75rem 0.85rem; background: ${isChecked ? 'rgba(var(--primary-color-rgb, 255, 123, 84), 0.08)' : '#ffffff'}; border: 1.5px solid ${isChecked ? 'var(--primary-color, #f97316)' : '#e2e8f0'}; border-radius: 10px; transition: all 0.15s ease;"
                 class="catalog-option-card service-option-card${isChecked ? ' is-selected' : ''}">
                <input type="checkbox" ${isChecked ? 'checked' : ''} 
                       onchange="const c = this.closest('.catalog-option-card'); c.classList.toggle('is-selected', this.checked); c.style.background = this.checked ? 'rgba(var(--primary-color-rgb, 255, 123, 84), 0.08)' : '#ffffff'; c.style.borderColor = this.checked ? 'var(--primary-color, #f97316)' : '#e2e8f0'; window.toggleCustomizableItem('service', ${id}, this.checked);"
                       style="width: 16px; height: 16px; accent-color: var(--primary-color, #f97316); cursor: pointer; flex-shrink: 0; margin-top: 22px;" />
                <div style="width:56px;height:56px;border-radius:10px;overflow:hidden;background:#f1f5f9;flex-shrink:0;display:flex;align-items:center;justify-content:center;color:#cbd5e1;">
                    ${img
                        ? `<img src="${escapeHtml(img)}" alt="" onerror="this.style.display='none';this.parentElement.innerHTML='<i class=\\'fas fa-concierge-bell\\'></i>';" style="width:100%;height:100%;object-fit:cover;">`
                        : `<i class="fas fa-concierge-bell"></i>`}
                </div>
                <div style="flex: 1; min-width: 0; cursor: pointer;" onclick="const cb = this.parentElement.querySelector('input[type=checkbox]'); cb.checked = !cb.checked; cb.dispatchEvent(new Event('change'));">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 6px;">
                        <strong style="color: #0f172a; font-size: 0.88rem; line-height: 1.3;">${escapeHtml(item.name)}</strong>
                        ${priceHtml}
                    </div>
                    ${notesHtml}
                </div>
                <div class="catalog-option-actions">
                    <button type="button" title="Edit Service" onclick="window.openQuickEditModal('service', ${id}, event)"
                            class="catalog-action-button" aria-label="Edit service">
                        <i class="fas fa-edit" aria-hidden="true"></i>
                    </button>
                    <button type="button" title="Archive Service" onclick="window.quickDeleteCatalogItem('service', ${id}, event)"
                            class="catalog-action-button catalog-archive-button" aria-label="Archive service">
                        <i class="fas fa-archive" aria-hidden="true"></i>
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
        const cleanRemovalCredits = {};
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
        for (const [cat, rawCredit] of Object.entries(customizableCategoryRemovalCredits)) {
            const credit = Number(rawCredit);
            if (Number.isFinite(credit) && credit > 0 && credit <= 999999 && categoryCounts[cat]) {
                cleanRemovalCredits[cat] = Math.round(credit * 100) / 100;
            }
        }
        const payload = {
            package_type: 'customizable',
            available_menu_ids: Array.from(customizableMenuIds),
            available_service_ids: Array.from(customizableServiceIds),
            available_equipment_ids: Array.from(customizableEquipmentIds),
            category_quotas: cleanQuotas,
            category_removal_credits: cleanRemovalCredits,
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
    updateInlineMenuCategoryQuotas();
    renderCategoryQuotas();
    syncCustomizableSelectionRules();
    updatePackageWizardControls();
};

window.setCategoryRemovalCredit = function(encodedCat, val) {
    const cat = decodeURIComponent(encodedCat);
    const credit = Number(String(val || '').trim());
    if (!Number.isFinite(credit) || credit <= 0 || credit > 999999) {
        delete customizableCategoryRemovalCredits[cat];
    } else {
        customizableCategoryRemovalCredits[cat] = Math.round(credit * 100) / 100;
    }
    syncCustomizableSelectionRules();
};

function renderCategoryQuotas() {
    const catCounts = getCustomizableMenuCategoryCounts();
    let totalAllowed = 0;
    for (const [category, available] of Object.entries(catCounts)) {
        const quota = Number(customizableCategoryQuotas[category]);
        if (Number.isInteger(quota) && quota >= 1 && quota <= available) {
            totalAllowed += quota;
        }
    }
    const totalEl = document.getElementById('custTotalVariantsAllowedText');
    if (totalEl) totalEl.innerText = String(totalAllowed);
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
                        summaryParts.push(`<span style="background: #ffffff; border: 1px solid #fed7aa; padding: 3px 8px; border-radius: 6px; font-weight: 700; color: #9a3412; font-size: 0.8rem;"><strong style="color: #ea580c;">Up to ${num}</strong> from ${escapeHtml(cat)}</span>`);
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
                                <i class="fas fa-layer-group" style="margin-right: 5px;"></i> Menu Choices by Category
                            </h5>
                            <span style="font-size: 0.75rem; font-weight: 800; color: #ea580c; background: #ffedd5; padding: 2px 8px; border-radius: 12px; border: 1px solid #fed7aa;">
                                Maximum: ${totalAllowed} dish${totalAllowed === 1 ? '' : 'es'}
                            </span>
                        </div>
                        <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px;">
                            ${summaryParts.join('')}
                        </div>
                        <div style="font-size: 0.78rem; color: #9a3412; margin-top: 6px;">
                            Customers can leave a category empty. A removal credit applies only when a per-guest amount is set for that category.
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
                    const priceHtml = price > 0
                        ? `<span style="font-weight:700; color:#1e40af; font-size:0.78rem;">₱${price.toLocaleString('en-PH', { maximumFractionDigits: 2 })}${unit && unit !== 'fixed' ? '/' + escapeHtml(unit) : ''}</span>`
                        : '';
                    return `
                        <div style="font-size:0.85rem; color:#1e293b; display:flex; justify-content:space-between; align-items:center; padding:5px 0; border-bottom:1px dashed #f1f5f9;">
                            <span><i class="fas fa-check-circle" style="color:#2563eb; font-size:0.8rem; margin-right:6px;"></i><strong>${escapeHtml(i.name)}</strong></span>
                            ${priceHtml}
                        </div>
                    `;
                }).join('');
            }
        }

        // 4. Available Equipment
        const equipmentList = document.getElementById('reviewCustEquipmentList');
        const equipmentCountBadge = document.getElementById('reviewCustEquipmentCount');
        const equipmentCatalog = (window.inclusionsCatalog && window.inclusionsCatalog.equipment) || [];
        const selectedEquipmentItems = equipmentCatalog.filter(i => customizableEquipmentIds.has(Number(i.id)));

        if (equipmentCountBadge) equipmentCountBadge.innerText = `${selectedEquipmentItems.length} item${selectedEquipmentItems.length === 1 ? '' : 's'}`;
        if (equipmentList) {
            if (selectedEquipmentItems.length === 0) {
                equipmentList.innerHTML = '<div style="color:#94a3b8; font-size:0.85rem; font-style:italic; padding: 6px 0;">No equipment selected.</div>';
            } else {
                equipmentList.innerHTML = selectedEquipmentItems.map(i => `
                    <div style="font-size:0.85rem; color:#1e293b; display:flex; justify-content:space-between; align-items:center; padding:5px 0; border-bottom:1px dashed #f1f5f9;">
                        <span><i class="fas fa-check-circle" style="color:#7c3aed; font-size:0.8rem; margin-right:6px;"></i><strong>${escapeHtml(i.name)}</strong>${i.category ? ' <span style="color:#64748b; font-size:0.75rem;">(' + escapeHtml(i.category) + ')</span>' : ''}</span>
                    </div>
                `).join('');
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
    if (type === 'service' && rawValue) {
        if (input.dataset.formatOverflow === 'true') {
            message = 'Use up to 8 whole-number digits and 2 decimal places.';
        } else if (!/^\d+(?:\.\d{1,2})?$/.test(rawValue) || !Number.isFinite(amount)) {
            message = 'Enter a valid service fee with no more than 2 decimal places.';
        } else if (amount <= 0) {
            message = 'Service fee must be greater than zero.';
        } else if (amount > 99999999.99) {
            message = 'The maximum service fee is ₱99,999,999.99.';
        }
    }

    input.setCustomValidity('');
    if (error) {
        error.textContent = message;
        error.style.display = message ? 'block' : 'none';
    }
    return !message;
};

window.sanitizeMoneyInput = function (input) {
    if (!input || input.readOnly) return;
    const original = input.value;
    let cleaned = original.replace(/[^\d.]/g, '');
    const decimalIndex = cleaned.indexOf('.');
    if (decimalIndex >= 0) {
        cleaned = cleaned.slice(0, decimalIndex + 1)
            + cleaned.slice(decimalIndex + 1).replace(/\./g, '').slice(0, 2);
    }
    const [whole = '', fraction] = cleaned.split('.');
    cleaned = whole.slice(0, 8) + (fraction !== undefined ? `.${fraction}` : '');
    if (input.value !== cleaned) {
        const cursor = input.selectionStart;
        input.value = cleaned;
        if (cursor !== null) input.setSelectionRange(Math.min(cursor, cleaned.length), Math.min(cursor, cleaned.length));
    }
};

window.validateSwapFee = function (inputId, errorId) {
    const input = document.getElementById(inputId);
    const error = document.getElementById(errorId);
    if (!input) return false;
    const value = input.value.trim();
    let message = '';
    if (value && !/^\d{1,8}(?:\.\d{1,2})?$/.test(value)) {
        message = 'Use up to 8 whole-number digits and 2 decimal places; fee cannot exceed ₱99,999,999.99.';
    } else if (value && Number(value) <= 0) {
        message = 'Enter an amount greater than ₱0, or leave this field blank.';
    } else if (value && (!Number.isFinite(Number(value)) || Number(value) > 99999999.99)) {
        message = 'The maximum dish swap fee is ₱99,999,999.99.';
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
    const nameLabel = document.getElementById('quickAddOptionNameLabel');
    const nameInput = document.getElementById('quickAddOptionName');
    const unitLabel = document.getElementById('quickAddOptionUnitLabel');
    const unitSelect = document.getElementById('quickAddOptionUnit');
    const categoryInput = document.getElementById('quickAddOptionCategory');
    const categoryWrapper = document.getElementById('quickAddOptionCategoryWrapper');
    const categorySuggestions = document.getElementById('quickAddOptionCategorySuggestions');
    const description = document.getElementById('quickAddOptionDescription');
    const upgradeFeeWrapper = document.getElementById('quickAddOptionUpgradeFeeWrapper');
    const upgradeFeeInput = document.getElementById('quickAddOptionUpgradeFee');
    const customCategoryWrapper = document.getElementById('quickAddOptionCustomCategoryWrapper');
    const customCategoryInput = document.getElementById('quickAddOptionCustomCategory');
    const equipmentFlow = type === 'equipment';

    if (categoryInput?.tagName === 'INPUT' && categorySuggestions && !categoryInput.dataset.suggestionsBound) {
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
    if (footer) footer.style.setProperty('display', hasType ? 'flex' : 'none', 'important');
    if (nameWrapper) nameWrapper.style.display = hasType ? 'block' : 'none';
    if (unitWrapper) unitWrapper.style.display = 'none';
    if (priceWrapper) priceWrapper.style.display = type === 'service' ? 'block' : 'none';
    if (descriptionWrapper) descriptionWrapper.style.display = hasType ? 'block' : 'none';
    if (photoWrapper) photoWrapper.style.display = hasType ? 'block' : 'none';
    if (categoryWrapper) categoryWrapper.style.display = type === 'menu' ? 'block' : 'none';
    if (upgradeFeeWrapper) upgradeFeeWrapper.style.display = type === 'menu' ? 'block' : 'none';
    if (upgradeFeeInput && type !== 'menu') upgradeFeeInput.value = '';
    if (customCategoryWrapper) customCategoryWrapper.style.display = 'none';
    if (customCategoryInput) { customCategoryInput.required = false; customCategoryInput.value = ''; }
    if (nameInput) nameInput.required = hasType;
    if (unitSelect) unitSelect.required = false;
    if (categoryInput) categoryInput.required = type === 'menu';
    if (categoryInput) categoryInput.setCustomValidity('');
    const upgradeFeeError = document.getElementById('quickAddOptionUpgradeFeeError');
    if (upgradeFeeError) upgradeFeeError.textContent = '';
    if (priceRow) priceRow.style.display = type === 'service' ? 'grid' : 'none';
    if (priceRow) priceRow.style.gridTemplateColumns = '1fr';
    if (priceInput) priceInput.required = false;
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
        if (description) description.placeholder = 'Details, ingredients, specifications or notes...';
    } else if (type === 'service') {
        if (nameLabel) nameLabel.innerHTML = 'Service Name <span style="color: #ef4444;">*</span>';
        if (nameInput) nameInput.placeholder = 'e.g. Trained Waitstaff, Event Setup & Cleanup, Bartender';
        if (unitSelect) {
            unitSelect.innerHTML = `
                <option value="per_event">Per Event (Flat Rate)</option>
                <option value="per_pax">Per Person</option>
                <option value="per_hour">Per Hour</option>
            `;
            unitSelect.value = 'per_event';
        }
        if (categoryInput) categoryInput.value = 'Service';
        if (priceLabel) priceLabel.innerHTML = 'Service Fee (₱) <span style="font-weight: 400; color: #94a3b8; text-transform: none;">(Optional)</span>';
        if (priceInput) {
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
        if (priceInput) priceInput.value = '';
    }

    const title = document.getElementById('quickAddOptionModalTitle');
    const subtitle = document.querySelector('#quickAddOptionModal .quick-add-option-subtitle');
    const itemLabel = type === 'menu' ? 'menu item' : type;
    if (title) title.textContent = `Create ${itemLabel}`;
    if (subtitle) subtitle.textContent = `Save this ${itemLabel} to your catalog to reuse in future packages${window._pkgInclusionReturnState?.direct ? ' and add it to this package' : ''}.`;
};

window.toggleQuickAddCustomCategory = function (category) {
    const wrapper = document.getElementById('quickAddOptionCustomCategoryWrapper');
    const input = document.getElementById('quickAddOptionCustomCategory');
    const show = category === 'Other' && document.getElementById('quickAddOptionType')?.value === 'menu';
    if (wrapper) wrapper.style.display = show ? 'block' : 'none';
    if (input) {
        input.required = show;
        if (!show) input.value = '';
    }
};

window.openQuickAddOptionModal = function (type) {
    const modal = document.getElementById('quickAddOptionModal');
    if (!modal) return;

    const form = document.getElementById('quickAddOptionForm');
    if (form) form.reset();
    const typeSelect = document.getElementById('quickAddOptionType');
    if (typeSelect) typeSelect.disabled = false;
    const photoPreview = document.getElementById('quickAddOptionPhotoPreview');
    if (photoPreview) photoPreview.innerHTML = '';
    const photoHint = document.getElementById('quickAddOptionPhotoHint');
    const photoDescription = document.getElementById('quickAddOptionPhotoDescription');
    if (photoHint) photoHint.textContent = 'Upload photo';
    if (photoDescription) photoDescription.textContent = 'JPG or PNG · shown on package details';
    const typeLabel = document.getElementById('quickAddOptionTypeLabel');
    if (typeLabel) typeLabel.innerHTML = 'What would you like to add? <span style="color: #ef4444;">*</span>';

    const normalizedType = ['menu', 'service', 'equipment'].includes(type) ? type : '';
    window.setQuickAddOptionType(normalizedType);
    const title = document.getElementById('quickAddOptionModalTitle');
    const subtitle = modal.querySelector('.quick-add-option-subtitle');
    if (title) {
        title.textContent = normalizedType
            ? `Create ${normalizedType === 'menu' ? 'menu item' : normalizedType}`
            : 'Quick Add Inclusion';
    }
    const saveButton = document.querySelector('#quickAddOptionFooter #btnQuickOptionSubmit span');
    if (saveButton) saveButton.textContent = 'Save';
    const addAnotherButton = document.getElementById('btnQuickOptionAddAnother');
    if (addAnotherButton) {
        addAnotherButton.disabled = false;
        addAnotherButton.textContent = 'Save & add another';
    }
    const submitButton = document.getElementById('btnQuickOptionSubmit');
    if (submitButton) submitButton.disabled = false;
    if (subtitle) {
        subtitle.textContent = normalizedType
            ? `Save this ${normalizedType === 'menu' ? 'menu item' : normalizedType} to your catalog to reuse in future packages.`
            : 'Choose an option type, then save it to your catalog to reuse in future packages.';
    }
    safeOpenModal('quickAddOptionModal', true);
};

window.openFixedQuickAddOptionModal = function () {
    window.openAddInclusionModal();
};

window.closeQuickAddOptionModal = function () {
    safeCloseModal('quickAddOptionModal');
    const typeSelect = document.getElementById('quickAddOptionType');
    if (typeSelect) typeSelect.disabled = false;
    if (window._pkgInclusionReturnState && window._pkgInclusionReturnState.active) {
        if (!window._pkgInclusionReturnState.direct) {
            safeOpenModal('addInclusionModal', true);
        }
        window._pkgInclusionReturnState = null;
    }
};

window.submitQuickAddOption = async function (e) {
    e.preventDefault();
    const saveAnother = e.submitter?.value === 'add_another';
    const type = document.getElementById('quickAddOptionType')?.value || '';
    const name = (document.getElementById('quickAddOptionName')?.value || '').trim();
    const categoryInput = document.getElementById('quickAddOptionCategory');
    const category = (type === 'menu' ? categoryInput?.value : '')?.trim() || '';
    const customCategory = (document.getElementById('quickAddOptionCustomCategory')?.value || '').trim();
    const unit = document.getElementById('quickAddOptionUnit')?.value || '';
    const priceInput = document.getElementById('quickAddOptionPrice');
    const priceText = (priceInput?.value || '').trim();
    const price = type === 'menu' ? 0 : (Number(priceText.replace(/,/g, '')) || 0);
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
    if (type === 'menu' && category === 'Other' && !customCategory) {
        const customCategoryInput = document.getElementById('quickAddOptionCustomCategory');
        if (customCategoryInput) { customCategoryInput.reportValidity(); customCategoryInput.focus(); }
        return;
    }
    if (categoryInput) categoryInput.setCustomValidity('');
    if (type === 'menu' && !window.validateSwapFee('quickAddOptionUpgradeFee', 'quickAddOptionUpgradeFeeError')) {
        document.getElementById('quickAddOptionUpgradeFee')?.focus();
        return;
    }
    if (type === 'service' && !window.validateQuickAddOptionPrice()) {
        priceInput?.focus();
        return;
    }

    const btn = document.getElementById('btnQuickOptionSubmit');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Saving...</span>';
    }
    const addAnotherButton = document.getElementById('btnQuickOptionAddAnother');
    if (addAnotherButton) addAnotherButton.disabled = true;

    try {
        const formData = new FormData();
        formData.append('item_type', type);
        formData.append('name', name);
        formData.append('category', category);
        formData.append('custom_category', customCategory);
        const upgradeFeeText = document.getElementById('quickAddOptionUpgradeFee')?.value.trim() || '';
        if (type === 'menu' && upgradeFeeText) {
            formData.append('upgrade_fee', String(Number(upgradeFeeText.replace(/,/g, ''))));
        }
        if (type === 'service' && priceText) formData.append('price', price);
        formData.append('unit_type', unit);
        formData.append('description', desc);
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
        }

        if (saveAnother) {
            if (window._pkgInclusionReturnState?.active && !window._pkgInclusionReturnState.direct) {
                const categoryLabel = type === 'menu' ? 'Menu / Food' : type.charAt(0).toUpperCase() + type.slice(1);
                packageInclusions.push({
                    type: type === 'menu' ? 'Menu' : categoryLabel,
                    category: categoryLabel,
                    item_id: newId,
                    name: newItem.name,
                    description: newItem.description || '',
                    image_url: newItem.image_url || ''
                });
                syncInclusionsHidden();
                renderInclusionsList();
                if (typeof renderCustInclusionsList === 'function') renderCustInclusionsList();
            }
            const form = document.getElementById('quickAddOptionForm');
            form?.reset();
            const typeSelect = document.getElementById('quickAddOptionType');
            if (typeSelect) typeSelect.value = type;
            window.setQuickAddOptionType(type);
            const photoPreview = document.getElementById('quickAddOptionPhotoPreview');
            if (photoPreview) photoPreview.innerHTML = '';
            const photoHint = document.getElementById('quickAddOptionPhotoHint');
            if (photoHint) photoHint.textContent = 'Upload photo';
            const photoDescription = document.getElementById('quickAddOptionPhotoDescription');
            if (photoDescription) photoDescription.textContent = 'JPG or PNG · shown on package details';
            if (window._pkgInclusionReturnState?.active && !window._pkgInclusionReturnState.direct) {
                window._pkgInclusionReturnState.type = type === 'menu'
                    ? 'Menu'
                    : type.charAt(0).toUpperCase() + type.slice(1);
            }
            if (window.showToast) window.showToast(`Saved "${newItem.name}". Add another item or save to finish.`, 'success');
            document.getElementById('quickAddOptionName')?.focus();
            return;
        }

        // Close the form only when the caterer is finished adding items.
        safeCloseModal('quickAddOptionModal');

        if (window._pkgInclusionReturnState?.direct) {
            window._pkgInclusionReturnState = null;
            if (window.showToast) window.showToast(`Added "${newItem.name}" to this package.`, 'success');
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
            btn.innerHTML = '<i class="fas fa-check"></i> <span>Save</span>';
        }
        const addAnotherButton = document.getElementById('btnQuickOptionAddAnother');
        if (addAnotherButton) {
            addAnotherButton.disabled = false;
            addAnotherButton.textContent = 'Save & add another';
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
    type = String(type || '').toLowerCase();
    if (!['menu', 'service', 'equipment'].includes(type)) {
        alert('Invalid catalog item type.');
        return;
    }
    const list = window.inclusionsCatalog[type] || [];
    const item = list.find(i => Number(i.id) === Number(id));
    if (!item) {
        alert('Item not found in catalog.');
        return;
    }

    const modalId = {
        menu: 'editMenuItemModal',
        service: 'editServiceItemModal',
        equipment: 'editEquipmentItemModal'
    }[type];
    const modal = document.getElementById(modalId);
    if (!modal) return;
    if (modal.parentElement !== document.body) document.body.appendChild(modal);

    const prefix = type === 'menu' ? 'editMenuItem' : `edit${type[0].toUpperCase()}${type.slice(1)}Item`;
    const form = document.getElementById(`${prefix}Form`);
    if (form) form.reset();
    if (form) {
        form.dataset.dirty = 'false';
        if (!form.dataset.dirtyTracking) {
            form.addEventListener('input', () => { form.dataset.dirty = 'true'; });
            form.addEventListener('change', () => { form.dataset.dirty = 'true'; });
            form.dataset.dirtyTracking = 'true';
        }
    }
    const value = (suffix) => document.getElementById(`${prefix}${suffix}`);
    const idField = value('Id');
    const nameField = value('Name');
    const descriptionField = value('Description');
    const imageField = value('Image');
    const preview = value('PhotoPreview');
    const photoHint = value('PhotoHint');
    if (idField) idField.value = String(item.id);
    if (nameField) nameField.value = item.name || '';
    if (descriptionField) descriptionField.value = item.description || '';
    if (imageField) imageField.value = '';
    if (preview) {
        preview.innerHTML = item.image_url
            ? `<img src="${escapeHtml(item.image_url)}" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:10px;">`
            : '';
    }
    if (photoHint) photoHint.textContent = item.image_url ? 'Click to replace photo' : 'Upload photo';

    if (type === 'menu') {
        const categoryField = value('Category');
        const customCategoryField = value('CustomCategory');
        const currentCategory = String(item.category || '');
        const isPreset = categoryField && Array.from(categoryField.options).some(option => option.value === currentCategory);
        if (categoryField) {
            categoryField.value = isPreset ? currentCategory : 'Other';
            window.toggleCatalogEditCustomCategory('menu', categoryField.value);
        }
        if (customCategoryField && categoryField?.value === 'Other') customCategoryField.value = currentCategory;
        const feeField = value('UpgradeFee');
        if (feeField) feeField.value = Number(item.upgrade_fee) > 0 ? String(item.upgrade_fee) : '';
        window.validateSwapFee('editMenuItemUpgradeFee', 'editMenuItemUpgradeFeeError');
    } else if (type === 'service') {
        const feeField = value('Fee');
        if (feeField) feeField.value = Number(item.price ?? item.selling_price) > 0 ? String(item.price ?? item.selling_price) : '';
        window.validateCatalogEditServiceFee();
    }

    safeOpenModal(modalId, true);
};

window.toggleCatalogEditCustomCategory = function (type, category) {
    if (type !== 'menu') return;
    const wrapper = document.getElementById('editMenuItemCustomCategoryWrapper');
    const input = document.getElementById('editMenuItemCustomCategory');
    const visible = category === 'Other';
    if (wrapper) wrapper.hidden = !visible;
    if (input) {
        input.required = visible;
        if (!visible) input.value = '';
    }
};

window.validateCatalogEditServiceFee = function () {
    const input = document.getElementById('editServiceItemFee');
    const error = document.getElementById('editServiceItemFeeError');
    if (!input) return false;
    window.sanitizeMoneyInput(input);
    const raw = input.value.trim();
    let message = '';
    if (raw && (!/^\d{1,8}(?:\.\d{1,2})?$/.test(raw) || Number(raw) <= 0 || Number(raw) > 99999999.99)) {
        message = 'Enter a fee greater than 0, up to 8 whole-number digits and 2 decimal places, or leave it blank.';
    }
    input.setCustomValidity(message);
    if (error) {
        error.textContent = message;
        error.style.display = message ? 'block' : 'none';
    }
    return !message;
};

window.closeCatalogEditModal = function (modalId) {
    const form = document.querySelector(`#${modalId} form`);
    if (form && !form.dataset.saving && form.dataset.dirty === 'true' &&
        !window.confirm('Discard your changes? Choose OK to discard changes or Cancel to continue editing.')) return;
    safeCloseModal(modalId);
    if (form) {
        form.reset();
        delete form.dataset.dirty;
        delete form.dataset.saving;
    }
};

window.submitCatalogItemEdit = async function (event, type) {
    event.preventDefault();
    const prefix = type === 'menu' ? 'editMenuItem' : `edit${type[0].toUpperCase()}${type.slice(1)}Item`;
    const value = (suffix) => document.getElementById(`${prefix}${suffix}`);
    const id = value('Id')?.value;
    const name = value('Name')?.value.trim() || '';
    const description = value('Description')?.value.trim() || '';
    if (!id || !name) {
        alert('Item name is required.');
        return;
    }
    if (type === 'menu' && !window.validateSwapFee('editMenuItemUpgradeFee', 'editMenuItemUpgradeFeeError')) {
        value('UpgradeFee')?.focus();
        return;
    }
    if (type === 'service' && !window.validateCatalogEditServiceFee()) {
        value('Fee')?.focus();
        return;
    }

    const form = event.currentTarget;
    const submitButton = form.querySelector('button[type="submit"]');
    if (form) form.dataset.saving = 'true';
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = 'Saving...';
    }

    try {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('description', description);
        if (type === 'menu') {
            const category = value('Category').value;
            const customCategory = value('CustomCategory')?.value.trim() || '';
            const fee = value('UpgradeFee')?.value.trim() || '';
            formData.append('category', category);
            formData.append('custom_category', customCategory);
            formData.append('upgrade_fee', fee ? String(Number(fee)) : '0');
        } else if (type === 'service') {
            formData.append('price', value('Fee')?.value.trim() || '');
        }
        const image = value('Image')?.files?.[0];
        if (image) formData.append('image', image);

        const response = await fetch(`/caterer/api/catalogs/quick-edit/${type}/${id}`, {
            method: 'POST',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            body: formData
        });
        const result = await response.json();
        if (!response.ok || result.status !== 'success') {
            throw new Error(extractErrorMessage(result, 'Failed to update item'));
        }

        const updatedItem = result.item;
        const catalog = window.inclusionsCatalog[type] || [];
        const catalogIndex = catalog.findIndex(entry => Number(entry.id) === Number(id));
        if (catalogIndex >= 0) catalog[catalogIndex] = { ...catalog[catalogIndex], ...updatedItem };
        window.inclusionsCatalog[type] = catalog;
        let packageChanged = false;
        packageInclusions = packageInclusions.map(inclusion => {
            if (Number(inclusion.item_id) !== Number(id) ||
                getPackageInclusionCatalogType(inclusion) !== type) return inclusion;
            packageChanged = true;
            return {
                ...inclusion,
                name: updatedItem.name,
                description: updatedItem.description || '',
                image_url: updatedItem.image_url || inclusion.image_url || ''
            };
        });
        if (packageChanged) {
            syncInclusionsHidden();
            renderInclusionsList();
            if (typeof renderCustInclusionsList === 'function') renderCustInclusionsList();
        }
        renderCustomizableCatalogs();
        renderReviewCustomizable();
        safeCloseModal({
            menu: 'editMenuItemModal',
            service: 'editServiceItemModal',
            equipment: 'editEquipmentItemModal'
        }[type]);
        if (window.showToast) window.showToast(`Updated "${updatedItem.name}" successfully!`, 'success');
    } catch (error) {
        console.error('submitCatalogItemEdit error:', error);
        alert(error.message || 'Failed to update item.');
    } finally {
        if (form) delete form.dataset.saving;
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.textContent = 'Save changes';
        }
    }
};

window.previewCatalogEditPhoto = function (type, event) {
    const file = event && event.target && event.target.files && event.target.files[0];
    if (!file) return;
    const prefix = type === 'menu' ? 'editMenuItem' : `edit${type[0].toUpperCase()}${type.slice(1)}Item`;
    const preview = document.getElementById(`${prefix}PhotoPreview`);
    const hint = document.getElementById(`${prefix}PhotoHint`);
    const reader  = new FileReader();
    reader.onload = function (e) {
        if (preview) {
            preview.innerHTML = `<img src="${e.target.result}" style="width:100%;height:100%;object-fit:cover;border-radius:10px;">`;
        }
        if (hint) hint.textContent = file.name;
        const form = document.getElementById(`${prefix}Form`);
        if (form) form.dataset.dirty = 'true';
    };
    reader.readAsDataURL(file);
};

window.quickDeleteCatalogItem = async function (type, id, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    type = String(type || '').toLowerCase();
    const list = window.inclusionsCatalog[type] || [];
    const item = list.find(i => Number(i.id) === Number(id));
    const itemName = item ? item.name : 'this item';

    if (!confirm(`Archive "${itemName}"? It will be removed from this package and moved to Archives, where you can restore it later.`)) {
        return false;
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
            throw new Error(extractErrorMessage(data, 'Failed to archive item'));
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
        else if (type === 'equipment') customizableEquipmentIds.delete(numId);

        const previousInclusionCount = packageInclusions.length;
        packageInclusions = packageInclusions.filter(inclusion =>
            !(Number(inclusion.item_id) === numId && getPackageInclusionCatalogType(inclusion) === type)
        );
        if (packageInclusions.length !== previousInclusionCount) {
            syncInclusionsHidden();
            renderInclusionsList();
            if (typeof renderCustInclusionsList === 'function') renderCustInclusionsList();
        }

        // Update UI
        renderCustomizableCatalogs();
        syncCustomizableSelectionRules();
        renderReviewCustomizable();

        if (window.showToast) {
            window.showToast(`"${itemName}" archived. You can restore it from Archives.`, 'success');
        }
        return true;
    } catch (err) {
        console.error('quickDeleteCatalogItem error:', err);
        alert(err.message || 'An error occurred while archiving.');
        return false;
    }
};
