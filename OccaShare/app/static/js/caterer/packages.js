// Professional Package Management Logic (Wizard Optimized v15.0)
console.log("[Packages] v15.0 Loading...");

// Constants
const DISH_PLACEHOLDER = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100%25' height='100%25' fill='%23f8fafc'/%3E%3Cpath d='M30 40 L70 40 L50 70 Z' fill='%23e2e8f0'/%3E%3Ctext x='50%25' y='85%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='8' font-weight='800' fill='%23cbd5e1'%3ENO DISH IMAGE%3C/text%3E%3C/svg%3E";

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

async function openAddPackageModal() {
    try {
        const form = document.getElementById('packageForm');
        if (!form) {
            console.error('[Packages] packageForm not found');
            return;
        }
        
        const title = document.getElementById('packageModalTitle');
        if (title) title.innerText = 'Create New Package';

        form.action = '/caterer/packages/add';
        form.reset();

        // Reset wizard to Step 1
        const firstStep = document.getElementById('step-btn-basic');
        if (firstStep) switchPackageTab(firstStep, 'basic');

        // Reset new fields to defaults
        if (form.pricing_mode) form.pricing_mode.value = 'per_pax';
        if (form.reservation_fee_type) form.reservation_fee_type.value = 'fixed';
        if (form.reservation_fee_value) form.reservation_fee_value.value = 5000;
        if (form.transportation_cost) form.transportation_cost.value = 0;

        window.togglePricingMode('per_pax');        // Reset Image Preview
        const preview = document.getElementById('pkgImagePreview');
        const placeholder = document.getElementById('previewPlaceholder');
        if (preview) {
            preview.src = '';
            preview.style.display = 'none';
        }
        if (placeholder) placeholder.style.display = 'flex';

        // Clear checked perks
        document.querySelectorAll('#tab-perks input[name="linked_menu_ids"]').forEach(cb => cb.checked = false);

        // Clear dynamic costs
        calculateCosts();

        // Initialize Menu Library Tab
        loadPkgMenuLibrary();
        
        if (typeof window.reactivelyValidateForm === 'function') {
            window.reactivelyValidateForm(true);
        }
        
        safeOpenModal('packageModal');
    } catch (e) {
        console.error('[Packages] Error opening package modal:', e);
    }
}

async function editPackage(pkgId) {
    if (!pkgId) {
        console.error('[Packages] No package ID provided to editPackage');
        return;
    }

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
        if (form.price_per_head) form.price_per_head.value = pkg.price_per_head || '';
        if (form.min_guests) form.min_guests.value = pkg.min_guests || 50;
        if (form.service_duration) form.service_duration.value = pkg.service_duration || 8;
        if (form.reservation_fee_type) form.reservation_fee_type.value = pkg.reservation_fee_type || 'fixed';
        if (form.reservation_fee_value) form.reservation_fee_value.value = pkg.reservation_fee_value || 5000;
        if (form.additional_guest_price) form.additional_guest_price.value = pkg.additional_guest_price || 0;

        // Cost Breakdown (Explicit Fields)
        if (form.labor_cost) form.labor_cost.value = pkg.labor_cost || 0;
        if (form.utility_cost) form.utility_cost.value = pkg.utility_cost || 0;
        if (form.transportation_cost) form.transportation_cost.value = pkg.transportation_cost || 0;

        window.togglePricingMode(form.pricing_mode ? form.pricing_mode.value : 'per_pax');

        if (form.selection_rules) {
            form.selection_rules.value = pkg.selection_rules ? JSON.stringify(pkg.selection_rules) : '';
        }
        
        const ingDisplay = document.getElementById('pkgIngredientCostDisplay');
        if (ingDisplay) {
            ingDisplay.innerText = '₱' + (pkg.ingredient_total_cost || 0).toFixed(2) + ' / pax';
            ingDisplay.dataset.cost = pkg.ingredient_total_cost || 0;
        }

        calculateCosts();

        // Perks/Inclusions are now fetched from linked items via loadPkgMenuLibrary()

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

        // Reset wizard to Step 1
        const firstStep = document.getElementById('step-btn-basic');
        if (firstStep) switchPackageTab(firstStep, 'basic');
        
        await loadPkgMenuLibrary();

        if (typeof window.reactivelyValidateForm === 'function') {
            window.reactivelyValidateForm(true);
        }

        safeOpenModal('packageModal');
    } catch (e) {
        console.error('[Packages] Error loading package details:', e);
        if (window.showError) {
            window.showError("Could not load package details. Please refresh the page or check your connection.");
        } else {
            alert("Oops! Could not load package details.");
        }
    }
}

// Old Inclusions logic removed to favor Inventory Linking

// Dynamic Wizard Navigation & Step validations
function validateTab(tabName, silent = false) {
    const form = document.getElementById('packageForm');
    if (!form) return true;
    
    let isValid = true;
    
    // Clear previous inline errors
    if (!silent) {
        document.querySelectorAll('.inline-error-badge').forEach(b => b.remove());
        document.querySelectorAll('.control-pro').forEach(c => {
            c.style.borderColor = '';
            c.classList.remove('error-pulse');
        });
    }

    const addError = (input, msg) => {
        isValid = false;
        if (silent || !input) return;
        input.style.borderColor = '#ef4444';
        const badge = document.createElement('small');
        badge.className = 'inline-error-badge';
        badge.style = 'color: #ef4444; font-size: 11px; font-weight: 700; margin-top: 4px; display: block;';
        badge.innerText = msg;
        input.closest('.form-group-pro').appendChild(badge);
        
        // Add a premium pulse warning class
        input.classList.add('error-pulse');
        setTimeout(() => input.classList.remove('error-pulse'), 1000);
    };

    if (tabName === 'basic') {
        const nameVal = form.name.value.trim();
        if (!nameVal) {
            addError(form.name, "Package Name is required.");
        } else {
            // Check for duplication
            const currentPkgId = getActivePackageId();
            const cards = document.querySelectorAll('.package-card-pro');
            let isDuplicate = false;
            cards.forEach(card => {
                const cardId = card.id.replace('package-', '');
                if (currentPkgId && cardId === currentPkgId) return; // Skip self
                
                const titleEl = card.querySelector('.package-name-pro');
                if (titleEl && titleEl.innerText.trim().toLowerCase() === nameVal.toLowerCase()) {
                    isDuplicate = true;
                }
            });
            
            if (isDuplicate) {
                addError(form.name, "A package with this name already exists in your library.");
            }
        }
        
        const serviceTypeVal = form.service_type.value.trim();
        if (!serviceTypeVal) {
            addError(form.service_type, "Please select a Service Type.");
        }
        


        const descVal = form.description.value.trim();
        if (!descVal || descVal.length < 10) {
            addError(form.description, "Please provide a short description (min 10 characters).");
        }
    }
    
    if (tabName === 'perks') {
        const checkedInclusions = document.querySelectorAll('#tab-perks input[name="linked_menu_ids"]:checked').length;
        if (checkedInclusions === 0) {
            isValid = false;
            if (!silent) {
                const matrix = document.querySelector('.inclusion-matrix');
                if (matrix) {
                    matrix.style.border = '2px dashed #ef4444';
                    setTimeout(() => matrix.style.border = 'none', 3000);
                    
                    const badge = document.createElement('div');
                    badge.className = 'inline-error-badge text-center py-2';
                    badge.style = 'color: #ef4444; font-size: 11px; font-weight: 800; margin-top: 8px;';
                    badge.innerText = "Please select at least 1 inclusion or equipment from your inventory.";
                    matrix.parentNode.appendChild(badge);
                }
            }
        }
    }
    
    if (tabName === 'menu') {
        const selectedDishes = document.querySelectorAll('.menu-select-card.selected').length;
        if (selectedDishes === 0) {
            isValid = false;
            if (!silent) {
                const container = document.getElementById('pkgMenuLibraryContainer');
                if (container) {
                    container.style.border = '2px dashed #ef4444';
                    setTimeout(() => container.style.border = '', 3000);
                    
                    const badge = document.createElement('div');
                    badge.className = 'inline-error-badge text-center py-2';
                    badge.style = 'color: #ef4444; font-size: 11px; font-weight: 800;';
                    badge.innerText = "Please select at least 1 menu item from your library.";
                    container.parentNode.appendChild(badge);
                }
            }
        }
    }
    
    if (tabName === 'pricing') {
        const rawPrice = form.price_per_head.value.replace(/,/g, '');
        const price = parseFloat(rawPrice);
        if (isNaN(price) || price <= 0) {
            addError(form.price_per_head, "Price must be greater than 0.");
        }
        
        const mode = form.pricing_mode ? form.pricing_mode.value : 'per_pax';
        const minGuests = parseInt(form.min_guests.value);
        if (mode === 'per_pax' && (isNaN(minGuests) || minGuests < 10)) {
            addError(form.min_guests, "Minimum guests must be at least 10.");
        }
        
        const rawResFee = form.reservation_fee_value.value.replace(/,/g, '');
        const resFee = parseFloat(rawResFee);
        const resType = form.reservation_fee_type ? form.reservation_fee_type.value : 'fixed';
        if (isNaN(resFee) || resFee < 0) {
            addError(form.reservation_fee_value, "Reservation fee cannot be negative.");
        } else if (price > 0) {
            if (resType === 'fixed' && mode === 'per_pax' && minGuests > 0) {
                const maxAllowedFee = (price * minGuests) * 0.5; // 50% limit
                if (resFee > maxAllowedFee) {
                    addError(form.reservation_fee_value, `Reservation fee cannot exceed 50% of the base package (₱${maxAllowedFee.toLocaleString()}).`);
                }
            } else if (resType === 'fixed' && mode === 'fixed') {
                const maxAllowedFee = price * 0.5;
                if (resFee > maxAllowedFee) {
                    addError(form.reservation_fee_value, `Reservation fee cannot exceed 50% of the fixed price (₱${maxAllowedFee.toLocaleString()}).`);
                }
            } else if (resType === 'percentage' && resFee > 50) {
                addError(form.reservation_fee_value, "Reservation fee percentage cannot exceed 50%.");
            }
        }
        
        // Anti-Bankruptcy Margin Check
        const internalInput = document.getElementById('pkgInternalCostPerPax');
        if (internalInput) {
            const internalCost = parseFloat(internalInput.value) || 0;
            if (price < internalCost) {
                const costLabel = mode === 'per_pax' ? 'Est. Cost / Pax' : 'Total Est. Cost';
                addError(form.price_per_head, `Selling Price (₱${price}) cannot be lower than the ${costLabel} (₱${internalCost.toFixed(2)}).`);
            }
        }

        // Validate overhead costs
        if (form.labor_cost && (form.labor_cost.value === '' || parseFloat(form.labor_cost.value) < 0)) addError(form.labor_cost, "Cannot be empty or negative.");
        if (form.utility_cost && (form.utility_cost.value === '' || parseFloat(form.utility_cost.value) < 0)) addError(form.utility_cost, "Cannot be empty or negative.");
        if (form.base_pax && (form.base_pax.value === '' || parseInt(form.base_pax.value) < 1)) addError(form.base_pax, "Must be at least 1.");
        
    }
    
    if (tabName === 'addons') {
        return true;
    }
    
    return isValid;
}

window.reactivelyValidateForm = function(isInitialLoad = false) {
    const activeTabEl = document.querySelector('#packageModal .tab-pane-pro.active');
    const activeTabId = activeTabEl ? activeTabEl.id.replace('tab-', '') : null;

    const isBasicValid = validateTab('basic', isInitialLoad ? true : activeTabId !== 'basic');
    const isPerksValid = validateTab('perks', isInitialLoad ? true : activeTabId !== 'perks');
    const isMenuValid = validateTab('menu', isInitialLoad ? true : activeTabId !== 'menu');
    const isPricingValid = validateTab('pricing', isInitialLoad ? true : activeTabId !== 'pricing');
    const isAddonsValid = validateTab('addons', isInitialLoad ? true : activeTabId !== 'addons');
    
    const isAllValid = isBasicValid && isPerksValid && isMenuValid && isAddonsValid && isPricingValid;
    
    // Enable or disable Save Package button reactively
    const saveBtn = document.getElementById('pkgSaveBtn');
    if (saveBtn) {
        const isEditMode = getActivePackageId() !== null;
        if (isAllValid || isEditMode) {
            saveBtn.style.opacity = '1';
            saveBtn.style.background = 'var(--primary-color)';
            saveBtn.innerHTML = '<i class="fas fa-check-circle"></i> Save Package';
            saveBtn.disabled = false;
            saveBtn.style.cursor = 'pointer';
            saveBtn.style.pointerEvents = 'auto';
        } else {
            saveBtn.style.opacity = '0.7'; 
            saveBtn.style.background = '#94a3b8';
            saveBtn.innerHTML = '<i class="fas fa-save"></i> Save Package';
            saveBtn.disabled = true;
            saveBtn.style.cursor = 'not-allowed';
            saveBtn.style.pointerEvents = 'none';
        }
    }
    
    // Dynamically toggle locks on step buttons themselves!
    const basicStep = document.getElementById('step-btn-basic');
    const perksStep = document.getElementById('step-btn-perks');
    const menuStep = document.getElementById('step-btn-menu');
    const pricingStep = document.getElementById('step-btn-pricing');
    
    if (perksStep) {
        if (isBasicValid) {
            perksStep.style.opacity = '1';
            perksStep.style.pointerEvents = 'auto';
        } else {
            perksStep.style.opacity = '0.4';
            perksStep.style.pointerEvents = 'none';
        }
    }
    if (menuStep) {
        if (isBasicValid && isPerksValid) {
            menuStep.style.opacity = '1';
            menuStep.style.pointerEvents = 'auto';
        } else {
            menuStep.style.opacity = '0.4';
            menuStep.style.pointerEvents = 'none';
        }
    }
    const addonsStep = document.getElementById('step-btn-addons');
    if (addonsStep) {
        if (isBasicValid && isPerksValid && isMenuValid) {
            addonsStep.style.opacity = '1';
            addonsStep.style.pointerEvents = 'auto';
        } else {
            addonsStep.style.opacity = '0.4';
            addonsStep.style.pointerEvents = 'none';
        }
    }
    if (pricingStep) {
        if (isBasicValid && isPerksValid && isMenuValid && isAddonsValid) {
            pricingStep.style.opacity = '1';
            pricingStep.style.pointerEvents = 'auto';
        } else {
            pricingStep.style.opacity = '0.4';
            pricingStep.style.pointerEvents = 'none';
        }
    }
    const reviewStep = document.getElementById('step-btn-review');
    if (reviewStep) {
        if (isAllValid) {
            reviewStep.style.opacity = '1';
            reviewStep.style.pointerEvents = 'auto';
        } else {
            reviewStep.style.opacity = '0.4';
            reviewStep.style.pointerEvents = 'none';
        }
    }
};

window.goToWizardNextStep = function(nextTab) {
    const nextBtn = document.getElementById('step-btn-' + nextTab);
    if (nextBtn) {
        switchPackageTab(nextBtn, nextTab);
    }
};

window.goToWizardBackStep = function(prevTab) {
    const prevBtn = document.getElementById('step-btn-' + prevTab);
    if (prevBtn) {
        // Validation bypass on back navigation
        document.querySelectorAll('.pkg-step-side, .pkg-step').forEach(s => s.classList.remove('active'));
        prevBtn.classList.add('active');

        document.querySelectorAll('#packageModal .tab-pane-pro').forEach(p => p.classList.remove('active'));
        const target = document.getElementById('tab-' + prevTab);
        if (target) {
            target.classList.add('active');
        }
        
        // Update Progress Bar
        const stepsOrder = ['basic', 'perks', 'menu', 'addons', 'pricing', 'review'];
        const targetIdx = stepsOrder.indexOf(prevTab);
        const progressEl = document.getElementById('pkgWizardProgress');
        if (progressEl) {
            const pct = ((targetIdx + 1) / stepsOrder.length) * 100;
            progressEl.style.width = pct + '%';
        }

        // Update Footer Buttons dynamically
        switchPackageTab(prevBtn, prevTab);
    }
};

function switchPackageTab(el, tabName) {
    if (!el) return;
    
    // Validate previous tabs on forward click
    const stepsOrder = ['basic', 'perks', 'menu', 'addons', 'pricing', 'review'];
    const targetIdx = stepsOrder.indexOf(tabName);
    const activeStepEl = document.querySelector('.pkg-step-side.active') || document.querySelector('.pkg-step.active');
    const currentTabName = activeStepEl ? activeStepEl.id.replace('step-btn-', '') : 'basic';
    const currentIdx = stepsOrder.indexOf(currentTabName);
    
    if (targetIdx > currentIdx) {
        for (let i = currentIdx; i < targetIdx; i++) {
            if (!validateTab(stepsOrder[i])) {
                const failEl = document.getElementById('step-btn-' + stepsOrder[i]);
                if (failEl) {
                    document.querySelectorAll('.pkg-step-side, .pkg-step').forEach(s => s.classList.remove('active'));
                    failEl.classList.add('active');
                }
                return;
            }
        }
    }

    document.querySelectorAll('.pkg-step-side, .pkg-step').forEach(s => s.classList.remove('active'));
    el.classList.add('active');

    document.querySelectorAll('#packageModal .tab-pane-pro').forEach(p => p.classList.remove('active'));
    const target = document.getElementById('tab-' + tabName);
    if (target) {
        target.classList.add('active');
        const body = document.querySelector('#packageModal .occ-modal-body');
        if (body) body.scrollTop = 0;
    }

    // Update Progress Bar
    const progressEl = document.getElementById('pkgWizardProgress');
    if (progressEl) {
        const pct = ((targetIdx + 1) / stepsOrder.length) * 100;
        progressEl.style.width = pct + '%';
    }

    // Footer is now static (Cancel & Save) in the HTML for the sidebar layout
    
    if (typeof window.reactivelyValidateForm === 'function') {
        window.reactivelyValidateForm(true);
    }
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

        // Populate tab-perks (Equipment/Services) and tab-addons checkboxes
        document.querySelectorAll('#tab-perks input[name="linked_menu_ids"], #tab-addons input[name="linked_menu_ids"]').forEach(cb => {
            const baseVal = cb.value.split('_q')[0];
            const val = isNaN(baseVal) ? baseVal : parseInt(baseVal);
            
            const linkedItem = linkedItems.find(i => i.id === val || i.id === baseVal);
            cb.checked = !!linkedItem;
            
            const card = cb.closest('.menu-select-card');
            if (card) {
                const qtyContainer = card.querySelector('.qty-container');
                const qtyInput = card.querySelector('.inc-qty-input');
                
                if (cb.checked) {
                    card.classList.add('selected');
                    card.style.background = '#f0fdf4';
                    card.style.borderColor = '#22c55e';
                    const icon = card.querySelector('i');
                    if(icon) icon.className = 'fas fa-check-circle text-green-500';
                    
                    if (qtyContainer) {
                        qtyContainer.style.display = 'block';
                        if (qtyInput && linkedItem && linkedItem.quantity) {
                            qtyInput.value = linkedItem.quantity;
                            cb.value = baseVal + '_q' + linkedItem.quantity;
                        }
                    }
                } else {
                    card.classList.remove('selected');
                    card.style.background = 'white';
                    card.style.borderColor = '#e2e8f0';
                    const icon = card.querySelector('i');
                    if(icon) icon.className = 'far fa-circle text-slate-200';
                    
                    if (qtyContainer) {
                        qtyContainer.style.display = 'none';
                        if (qtyInput) qtyInput.value = 1;
                        cb.value = baseVal + '_q1';
                    }
                }
            }
        });

        // Filter library to only show food items in Menu Setup
        const excludeCats = ['rentals', 'services', 'equipment'];
        const foodLibrary = library.filter(item => {
            const cat = item.category ? item.category.toLowerCase() : '';
            return !excludeCats.includes(cat) && !item.is_addon;
        });

        container.innerHTML = '';
        if (foodLibrary.length === 0) {
            container.innerHTML = '<div class="text-center py-5 text-slate-400 text-xs">Your menu library is currently empty.</div>';
            return;
        }

        // Group by category
        const grouped = {};
        foodLibrary.forEach(item => {
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
            html += items.map(item => {
                const isSelected = linkedIds.includes(item.id);
                return `
                    <div class="menu-select-card ${isSelected ? 'selected' : ''}" 
                         data-id="${item.id}"
                         data-cost="${item.cost_price || 0}"
                         data-category="${item.category}"
                         onclick="window.toggleLibItemSelectCard(this, ${item.id})"
                         style="position: relative; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 0.5rem; padding: 1.25rem 0.75rem; border: 1px solid ${isSelected ? 'var(--primary-color)' : '#e2e8f0'}; border-radius: 0.75rem; cursor: pointer; transition: all 0.2s; background: ${isSelected ? '#f0fdf4' : 'white'}; box-shadow: ${isSelected ? '0 4px 12px rgba(0,0,0,0.05)' : 'none'};">
                        
                        <div style="position: absolute; top: 10px; right: 10px; font-size: 1.2rem; color: ${isSelected ? 'var(--primary-color)' : '#cbd5e1'}; transition: all 0.2s;">
                            ${isSelected ? '<i class="fas fa-check-circle"></i>' : '<i class="far fa-circle"></i>'}
                        </div>

                        <img src="${item.image_url || DISH_PLACEHOLDER}" alt="${item.name}" onerror="this.src='${DISH_PLACEHOLDER}'" style="width: 64px; height: 64px; border-radius: 50%; object-fit: cover; border: 3px solid #f8fafc; margin-bottom: 0.25rem; box-shadow: 0 4px 8px rgba(0,0,0,0.06);">
                        
                        <div style="flex: 1; width: 100%;">
                            <h6 style="margin: 0; font-size: 0.85rem; font-weight: 800; color: #1e293b; line-height: 1.2; text-overflow: ellipsis; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">${item.name}</h6>
                            <div style="font-size: 0.65rem; font-weight: 800; color: var(--primary-color); text-transform: uppercase; margin-top: 6px; letter-spacing: 0.05em;">${item.category}</div>
                            ${(item.price && parseFloat(item.price) > 0) ? `<div style="font-size: 0.75rem; color: #64748b; font-weight: 700; margin-top: 4px;">Ala Carte Price: ₱${parseFloat(item.price).toLocaleString('en-PH', {minimumFractionDigits: 2})}</div>` : '<div style="font-size: 0.75rem; color: #10b981; font-weight: 700; margin-top: 4px;">Bundled in Package</div>'}
                            <div style="font-size: 0.65rem; color: #94a3b8; font-weight: 600; margin-top: 2px;">Est. Puhunan: ₱${(item.cost_price || 0).toLocaleString('en-PH', {minimumFractionDigits: 2})}</div>
                        </div>
                        <input type="checkbox" name="linked_menu_ids" value="${item.id}" ${isSelected ? 'checked' : ''} style="display:none;">
                    </div>
                `;
            }).join('');
        }
        container.innerHTML = html;
        
        // Populate Add-ons Tab
        const addonsGrid = document.getElementById('addonsGrid');
        if (addonsGrid) {
            const addonsLibrary = library.filter(item => item.is_addon === true);
            if (addonsLibrary.length > 0) {
                addonsGrid.innerHTML += addonsLibrary.map(item => {
                    const isSelected = linkedIds.includes(item.id);
                    return `
                        <div class="menu-select-card ${isSelected ? 'selected' : ''}" 
                             data-id="${item.id}"
                             data-cost="${item.cost_price || 0}"
                             onclick="window.toggleLibItemSelectCard(this, ${item.id})"
                             style="position: relative; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 0.5rem; padding: 1.25rem 0.75rem; border: 1px solid ${isSelected ? 'var(--primary-color)' : '#e2e8f0'}; border-radius: 0.75rem; cursor: pointer; transition: all 0.2s; background: ${isSelected ? '#f0fdf4' : 'white'}; box-shadow: ${isSelected ? '0 4px 12px rgba(0,0,0,0.05)' : 'none'};">
                            
                            <div style="position: absolute; top: 10px; right: 10px; font-size: 1.2rem; color: ${isSelected ? 'var(--primary-color)' : '#cbd5e1'}; transition: all 0.2s;">
                                ${isSelected ? '<i class="fas fa-check-circle"></i>' : '<i class="far fa-circle"></i>'}
                            </div>
        
                            <img src="${item.image_url || DISH_PLACEHOLDER}" alt="${item.name}" onerror="this.src='${DISH_PLACEHOLDER}'" style="width: 64px; height: 64px; border-radius: 50%; object-fit: cover; border: 3px solid #f8fafc; margin-bottom: 0.25rem; box-shadow: 0 4px 8px rgba(0,0,0,0.06);">
                            
                            <div style="flex: 1; width: 100%;">
                                <h6 style="margin: 0; font-size: 0.85rem; font-weight: 800; color: #1e293b; line-height: 1.2; text-overflow: ellipsis; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">${item.name}</h6>
                                <div style="font-size: 0.75rem; color: #64748b; font-weight: 700; margin-top: 4px;">Charge: ₱${(item.addon_price || item.price || 0).toLocaleString('en-PH', {minimumFractionDigits: 2})}</div>
                                <div style="font-size: 0.65rem; color: #94a3b8; font-weight: 600; margin-top: 2px;">Est. Puhunan: ₱${(item.cost_price || 0).toLocaleString('en-PH', {minimumFractionDigits: 2})}</div>
                            </div>
                            <input type="checkbox" name="linked_menu_ids" value="${item.id}" ${isSelected ? 'checked' : ''} style="display:none;">
                        </div>
                    `;
                }).join('');
            }
        }
        
        calculateCosts(); // Initial calc
        updateSelectionRulesBuilder();
    } catch (e) {
        console.error('[Packages] Menu library fetch error:', e);
        container.innerHTML = '<div class="text-center py-5 text-red-400 text-xs">Error loading library.</div>';
    }
}

function toggleLibItemSelectCard(card, id) {
    const cb = card.querySelector('input[type="checkbox"]');
    if (!cb) return;
    cb.checked = !cb.checked;
    
    const qtyContainer = card.querySelector('.qty-container');
    
    if (cb.checked) {
        card.classList.add('selected');
        card.style.background = '#f0fdf4';
        card.style.borderColor = '#22c55e';
        card.querySelector('i').className = 'fas fa-check-circle text-green-500';
        if (qtyContainer) qtyContainer.style.display = 'block';
    } else {
        card.classList.remove('selected');
        card.style.background = 'white';
        card.style.borderColor = '#e2e8f0';
        card.querySelector('i').className = 'far fa-circle text-slate-200';
        if (qtyContainer) qtyContainer.style.display = 'none';
    }
    calculateCosts();
    updateSelectionRulesBuilder();
    
    if (typeof window.reactivelyValidateForm === 'function') {
        window.reactivelyValidateForm(false);
    }
}

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
    document.querySelectorAll('.menu-select-card.selected').forEach(card => {
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
    calculateCosts();
}

function filterPkgMenuLibrary() {
    const query = document.getElementById('pkgMenuLibrarySearch')?.value.toLowerCase() || '';
    document.querySelectorAll('.menu-select-card').forEach(card => {
        const name = card.querySelector('h6')?.innerText.toLowerCase() || '';
        card.style.display = name.includes(query) ? 'flex' : 'none';
    });
}

function calculateCosts() {
    const form = document.getElementById('packageForm');
    const labor = parseFloat(document.getElementById('pkgLaborCost')?.value.replace(/,/g, '')) || 0;
    const utility = parseFloat(document.getElementById('pkgUtilityCost')?.value.replace(/,/g, '')) || 0;
    const transport = parseFloat(document.getElementById('pkgTransportCost')?.value.replace(/,/g, '')) || 0;
    const minGuests = parseInt(form.min_guests ? form.min_guests.value : 50) || 1;
    const mode = form.pricing_mode ? form.pricing_mode.value : 'per_pax';
    
    // Sum selected menu items cost from Step 3 (Only if library is loaded)
    const menuCards = document.querySelectorAll('.menu-select-card');
    let servicesCostTotal = 0;
    
    // Calculate linked services from Tab 2
    document.querySelectorAll('#tab-perks .menu-select-card.selected').forEach(card => {
        servicesCostTotal += parseFloat(card.dataset.cost) || 0;
    });

    if (menuCards.length > 0) {
        const selectedDishesByCategory = {};
        document.querySelectorAll('#tab-menu .menu-select-card.selected').forEach(card => {
            const cat = card.dataset.category || 'Uncategorized';
            const cost = parseFloat(card.dataset.cost) || 0;
            if (!selectedDishesByCategory[cat]) selectedDishesByCategory[cat] = [];
            selectedDishesByCategory[cat].push(cost);
        });

        let rules = {};
        const hiddenInput = document.getElementById('selectionRulesHidden');
        if (hiddenInput && hiddenInput.value) {
            try {
                rules = JSON.parse(hiddenInput.value);
            } catch (e) {}
        }

        let ingCostPerPaxVar = 0;
        for (const [cat, costs] of Object.entries(selectedDishesByCategory)) {
            costs.sort((a, b) => b - a);
            const limit = rules[cat] ? parseInt(rules[cat]) : costs.length;
            const effectiveLimit = Math.min(limit, costs.length);
            for (let i = 0; i < effectiveLimit; i++) {
                ingCostPerPaxVar += costs[i];
            }
        }
        
        window._tempIngCostPerPax = ingCostPerPaxVar;
    }

    const ingCostPerPax = window._tempIngCostPerPax || 0;

    let overheadTotal = labor + utility + transport;
    let overheadPerPax = mode === 'per_pax' ? (overheadTotal / minGuests) : overheadTotal;
    let servicesCostPerPax = mode === 'per_pax' ? (servicesCostTotal / minGuests) : servicesCostTotal;
    let foodCostPerPax = ingCostPerPax;
    
    let totalCostPerPax = overheadPerPax + foodCostPerPax + servicesCostPerPax;

    const display = document.getElementById('totalCostDisplay');
    if (display) display.innerText = '₱' + totalCostPerPax.toLocaleString(undefined, { minimumFractionDigits: 2 });

    const internalInput = document.getElementById('pkgInternalCostPerPax');
    if (internalInput) internalInput.value = totalCostPerPax;

    // Update Financial Analysis Panel displays
    const fFood = document.getElementById('analysisFoodCost');
    if (fFood) fFood.innerText = '₱' + foodCostPerPax.toLocaleString(undefined, { minimumFractionDigits: 2 });
    const fServ = document.getElementById('analysisServicesCost');
    if (fServ) fServ.innerText = '₱' + servicesCostPerPax.toLocaleString(undefined, { minimumFractionDigits: 2 });
    const fOverhead = document.getElementById('analysisOperationalCost');
    if (fOverhead) fOverhead.innerText = '₱' + overheadPerPax.toLocaleString(undefined, { minimumFractionDigits: 2 });
    const profitDisplay = document.getElementById('analysisProfit');
    const roiDisplay = document.getElementById('analysisROI');
    const manualPriceInput = document.getElementById('pkgManualPriceInput');
    const manualPrice = manualPriceInput ? parseFloat(manualPriceInput.value.replace(/,/g, '')) || 0 : 0;
    const badge = document.getElementById('roiMarginBadge');
    
    let profit = 0;
    let margin = 0;
    
    if (badge) {
        if (manualPrice > 0) {
            profit = manualPrice - totalCostPerPax;
            margin = (profit / totalCostPerPax) * 100; // Expected ROI based on cost
            
            badge.innerText = `${margin.toFixed(1)}% ROI`;
            
            if (margin < 0) {
                badge.style.background = '#fee2e2';
                badge.style.color = '#ef4444';
            } else if (margin < 15) {
                badge.style.background = '#fef3c7';
                badge.style.color = '#d97706';
            } else {
                badge.style.background = '#dcfce3';
                badge.style.color = '#16a34a';
            }
        } else {
            badge.innerText = '--% ROI';
            badge.style.background = '#f1f5f9';
            badge.style.color = '#94a3b8';
        }
    }
    
    if (profitDisplay) profitDisplay.innerText = '₱' + profit.toLocaleString(undefined, { minimumFractionDigits: 2 });
    if (roiDisplay) roiDisplay.innerText = margin.toFixed(1) + '%';

    // Populate Review Tab
    const rName = document.getElementById('reviewName');
    const rType = document.getElementById('reviewType');
    const rMode = document.getElementById('reviewPricingMode');
    const rPrice = document.getElementById('reviewPrice');
    const rROI = document.getElementById('reviewROI');
    const rRes = document.getElementById('reviewReservation');
    const rDishes = document.getElementById('reviewDishesCount');
    const rServices = document.getElementById('reviewServicesCount');

    if (rName && form) {
        rName.innerText = form.name.value || 'Untitled Package';
        if (rType) rType.innerText = form.service_type.value || 'General';
        
        const mode = form.pricing_mode ? form.pricing_mode.value : 'per_pax';
        if (rMode) rMode.innerText = mode === 'fixed' ? 'Fixed (Event Based)' : 'Per Pax (Guest Based)';
        
        if (rPrice) rPrice.innerText = '₱' + manualPrice.toLocaleString(undefined, { minimumFractionDigits: 2 }) + (mode === 'fixed' ? ' total' : ' / pax');
        if (rROI) {
            rROI.innerText = margin.toFixed(1) + '%';
            rROI.style.color = margin < 0 ? '#ef4444' : '#1e293b';
        }

        const resType = form.reservation_fee_type ? form.reservation_fee_type.value : 'fixed';
        const resVal = form.reservation_fee_value ? parseFloat(form.reservation_fee_value.value) || 0 : 0;
        if (rRes) rRes.innerText = resType === 'percentage' ? resVal + '%' : '₱' + resVal.toLocaleString();
        
        const rExcessContainer = document.getElementById('reviewExcessPaxContainer');
        const rExcess = document.getElementById('reviewExcessPax');
        if (rExcessContainer && rExcess) {
            if (mode === 'fixed') {
                const excessVal = parseFloat(form.additional_guest_price?.value) || 0;
                rExcess.innerText = '₱' + excessVal.toLocaleString(undefined, { minimumFractionDigits: 2 });
                rExcessContainer.style.display = 'block';
            } else {
                rExcessContainer.style.display = 'none';
            }
        }
        
        if (rDishes) rDishes.innerText = document.querySelectorAll('#tab-menu .menu-select-card.selected').length;
        if (rServices) rServices.innerText = document.querySelectorAll('#tab-perks .menu-select-card.selected').length;
        
        const rAddons = document.getElementById('reviewAddonsCount');
        if (rAddons) {
            rAddons.innerText = document.querySelectorAll('#tab-addons .menu-select-card.selected').length;
        }
    }
}

window.togglePricingMode = function(mode) {
    const minGuestsLabel = document.querySelector('input[name="min_guests"]')?.previousElementSibling;
    if (minGuestsLabel) {
        minGuestsLabel.innerText = mode === 'fixed' ? 'Base Pax Included' : 'Min Guests';
    }
    
    const excessGroup = document.getElementById('excessPaxGroup');
    if (excessGroup) {
        excessGroup.style.display = mode === 'fixed' ? 'block' : 'none';
    }

    const perHeadLabel = document.querySelector('label[for="pkgManualPriceInput"]') || document.querySelector('#pkgManualPriceInput')?.previousElementSibling;
    if (perHeadLabel) {
        perHeadLabel.innerText = mode === 'fixed' ? 'Total Package Price (₱) *' : 'Selling Price Per Pax (₱) *';
    }
    
    // Update Financial Panel labels dynamically
    const fFoodLabel = document.getElementById('analysisFoodCostLabel');
    if (fFoodLabel) fFoodLabel.innerText = mode === 'fixed' ? 'Total Est. Food Cost (Puhunan):' : 'Est. Food Cost (Puhunan / Pax):';
    
    const fServLabel = document.getElementById('analysisServicesCostLabel');
    if (fServLabel) fServLabel.innerText = mode === 'fixed' ? 'Total Est. Services/Rentals Cost (Puhunan):' : 'Est. Services/Rentals Cost (Puhunan / Pax):';
    
    const fOpLabel = document.getElementById('analysisOperationalCostLabel');
    if (fOpLabel) fOpLabel.innerText = mode === 'fixed' ? 'Total Est. Operational Cost (Puhunan):' : 'Est. Operational Cost (Puhunan / Pax):';
    
    const fTotalLabel = document.getElementById('analysisTotalCostLabel');
    if (fTotalLabel) fTotalLabel.innerText = mode === 'fixed' ? 'Total Est. Base Cost (Puhunan):' : 'Total Est. Base Cost (Puhunan / Pax):';
    
    calculateCosts();
};


async function archivePackage(id) {
    const doArchive = async () => {
        try {
            const res = await fetch(`/caterer/packages/${id}/archive`, { method: 'POST' });
            if (res.ok) window.location.reload();
            else alert('Archive failed.');
        } catch (e) { console.error(e); }
    };

    if (window.showConfirm) {
        window.showConfirm('Linked bookings will retain their records, but it will be hidden from your active offerings.', doArchive, 'Archive this package', 'Archive Now', 'danger');
    }
}

async function togglePackageStatus(id, el) {
    if (!window.apiAction) return;
    const res = await window.apiAction(`/caterer/packages/${id}/toggle-status`, { method: 'POST' });
    if (res) {
        el.classList.toggle('active');
        const isActive = el.classList.contains('active');
        el.innerText = isActive ? 'active' : 'hidden';
    }
}

function filterPackages() {
    const query = document.getElementById('packageSearchInput')?.value.toLowerCase() || '';
    let visibleCount = 0;
    document.querySelectorAll('.package-card-pro').forEach(card => {
        const textContent = card.textContent.toLowerCase();
        const match = textContent.includes(query);
        card.style.display = match ? 'block' : 'none';
        if (match) visibleCount++;
    });

    const searchEmpty = document.getElementById('searchEmptyState');
    if (searchEmpty) {
        searchEmpty.style.display = visibleCount === 0 ? 'flex' : 'none';
    }
}

function previewPackageImage(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const preview = document.getElementById('pkgImagePreview');
            const placeholder = document.getElementById('previewPlaceholder');
            if (preview) {
                preview.src = e.target.result;
                preview.style.display = 'block';
                if (placeholder) placeholder.style.display = 'none';
            }
        };
        reader.readAsDataURL(input.files[0]);
    }
}

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    const pkgForm = document.getElementById('packageForm');
    if (pkgForm) {
        pkgForm.addEventListener('input', () => {
            calculateCosts();
            if (typeof window.reactivelyValidateForm === 'function') {
                window.reactivelyValidateForm(false);
            }
        });
        pkgForm.addEventListener('change', () => {
            if (typeof window.reactivelyValidateForm === 'function') {
                window.reactivelyValidateForm(false);
            }
        });
        
        pkgForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = pkgForm.querySelector('button[type="submit"]');
            
            // Strict Validation Guard for ALL tabs on submit
            const stepsOrder = ['basic', 'perks', 'menu', 'pricing'];
            for (let tab of stepsOrder) {
                if (!validateTab(tab)) {
                    const stepBtn = document.getElementById('step-btn-' + tab);
                    if (stepBtn) switchPackageTab(stepBtn, tab);
                    return;
                }
            }
            
            // Clean numeric inputs
            pkgForm.querySelectorAll('.js-format-comma, input[type="number"]:not(.selection-rule-input), input[inputmode="numeric"]').forEach(input => {
                input.value = input.value.replace(/[, \s]/g, '');
            });

            // Ensure selection rules are compiled before submit
            if (typeof compileSelectionRules === 'function') compileSelectionRules();

            const data = new FormData(pkgForm);
            
            if (window.apiAction) {
                const res = await window.apiAction(pkgForm.action, {
                    method: 'POST',
                    body: data
                }, btn);

                if (res) {
                    safeCloseModal('packageModal');
                    setTimeout(() => window.location.reload(), 800);
                }
            }
        });
    }

    const manualPriceInput = document.getElementById('pkgManualPriceInput');
    if (manualPriceInput) {
        manualPriceInput.addEventListener('input', calculateCosts);
    }
});

// ROI Management
let currentRoiPackageId = null;
let currentMarkupType = 'percentage';

window.openRoiModal = function(pkgId, pkgName, markupType, markupValue) {
    currentRoiPackageId = pkgId;
    currentMarkupType = markupType || 'percentage';
    const sub = document.getElementById('roiModalSubtitle');
    if (sub) sub.innerText = `Package: ${pkgName}`;
    
    const valInput = document.getElementById('roiMarkupValue');
    if (valInput) valInput.value = markupValue || 0;
    
    window.setMarkupType(currentMarkupType);
    safeOpenModal('roiModal');
};

window.hideRoiModal = function() {
    safeCloseModal('roiModal');
};

window.setMarkupType = function(type) {
    currentMarkupType = type;
    const btnPct = document.getElementById('btn-markup-percentage');
    const btnFix = document.getElementById('btn-markup-fixed');
    const symbol = document.getElementById('markupSymbol');
    const label = document.getElementById('markupValueLabel');

    if (type === 'percentage') {
        if (btnPct) { btnPct.style.background = 'white'; btnPct.style.color = 'var(--primary-color)'; btnPct.style.boxShadow = '0 2px 4px rgba(0,0,0,0.05)'; }
        if (btnFix) { btnFix.style.background = 'transparent'; btnFix.style.color = 'var(--color-neutral-500)'; btnFix.style.boxShadow = 'none'; }
        if (symbol) symbol.innerText = '%';
        if (label) label.innerText = 'Markup Value (%)';
    } else {
        if (btnFix) { btnFix.style.background = 'white'; btnFix.style.color = 'var(--primary-color)'; btnFix.style.boxShadow = '0 2px 4px rgba(0,0,0,0.05)'; }
        if (btnPct) { btnPct.style.background = 'transparent'; btnPct.style.color = 'var(--color-neutral-500)'; btnPct.style.boxShadow = 'none'; }
        if (symbol) symbol.innerText = '₱';
        if (label) label.innerText = 'Markup Amount (₱)';
    }
};

window.saveRoi = async function() {
    const valInput = document.getElementById('roiMarkupValue');
    const val = parseFloat(valInput ? valInput.value : 0) || 0;
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
    if (event.target == pModal) safeCloseModal('packageModal');
    if (event.target == mModal) safeCloseModal('menuModal');
    if (event.target == rModal) safeCloseModal('roiModal');
};

window.toggleAllInContainer = function(checkbox, selector) {
    const container = document.querySelector(selector);
    if (!container) return;
    
    const isChecked = checkbox.checked;
    const cards = container.querySelectorAll('.menu-select-card');
    
    cards.forEach(card => {
        const id = card.dataset.id;
        const cb = card.querySelector('input[type="checkbox"]');
        if (!cb || !id) return;
        
        // If the card's state doesn't match the master checkbox state, toggle it
        if (cb.checked !== isChecked) {
            window.toggleLibItemSelectCard(card, id);
        }
    });
};

// Final Consolidated Exports
window.openAddPackageModal = openAddPackageModal;
window.editPackage = editPackage;
window.switchPackageTab = switchPackageTab;
window.addCustomInclusion = addCustomInclusion;
window.editCustomInclusion = editCustomInclusion;
window.calculateCosts = calculateCosts;
window.showMenuModal = showMenuModal;
window.hideMenuModal = hideMenuModal;
window.switchMenuMode = switchMenuMode;
window.filterLibraryItems = filterLibraryItems;
window.linkDish = linkDish;
window.unlinkDish = unlinkDish;
window.archivePackage = archivePackage;
window.toggleLibItemSelectCard = toggleLibItemSelectCard;
window.togglePackageStatus = togglePackageStatus;
window.filterPackages = filterPackages;
window.previewPackageImage = previewPackageImage;
window.validateTab = validateTab;
window.toggleAllInContainer = toggleAllInContainer;

console.log("[Packages] v18.0 Exported.");

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('packageForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            // Trigger visual validation for all tabs
            const isBasicValid = window.validateTab ? window.validateTab('basic', false) : true;
            const isPerksValid = window.validateTab ? window.validateTab('perks', false) : true;
            const isMenuValid = window.validateTab ? window.validateTab('menu', false) : true;
            const isPricingValid = window.validateTab ? window.validateTab('pricing', false) : true;
            
            if (!(isBasicValid && isPerksValid && isMenuValid && isPricingValid)) {
                e.preventDefault();
                
                // Focus on the first tab that has an error
                if (!isBasicValid) {
                    window.switchPackageTab(document.getElementById('step-btn-basic'), 'basic');
                } else if (!isPerksValid) {
                    window.switchPackageTab(document.getElementById('step-btn-perks'), 'perks');
                } else if (!isMenuValid) {
                    window.switchPackageTab(document.getElementById('step-btn-menu'), 'menu');
                } else if (!isPricingValid) {
                    window.switchPackageTab(document.getElementById('step-btn-pricing'), 'pricing');
                }
            }
        });
    }
});
