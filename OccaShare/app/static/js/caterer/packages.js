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
    const action = form.getAttribute('action') || '';
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
        if (form.booking_lead_time) form.booking_lead_time.value = 7;
        if (form.reservation_fee) form.reservation_fee.value = 5000;
        if (form.min_contract_amount) form.min_contract_amount.value = '';
        


        // Reset Image Preview
        const preview = document.getElementById('pkgImagePreview');
        const placeholder = document.getElementById('previewPlaceholder');
        if (preview) {
            preview.src = '';
            preview.style.display = 'none';
        }
        if (placeholder) placeholder.style.display = 'flex';

        // Render default standard inclusions
        renderInclusions({});

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
        if (form.price_per_head) form.price_per_head.value = pkg.price_per_head || '';
        if (form.min_guests) form.min_guests.value = pkg.min_guests || 50;
        if (form.service_duration) form.service_duration.value = pkg.service_duration || 8;
        if (form.booking_lead_time) form.booking_lead_time.value = pkg.booking_lead_time || 7;
        if (form.reservation_fee) form.reservation_fee.value = pkg.reservation_fee || 5000;
        if (form.min_contract_amount) form.min_contract_amount.value = pkg.min_contract_amount || '';

        // Cost Breakdown (Explicit Fields)
        if (form.base_pax) form.base_pax.value = pkg.base_pax || 50;
        if (form.labor_cost) form.labor_cost.value = pkg.labor_cost || 0;
        if (form.utility_cost) form.utility_cost.value = pkg.utility_cost || 0;
        if (form.equipment_cost) form.equipment_cost.value = pkg.equipment_cost || 0;


        if (form.selection_rules) {
            form.selection_rules.value = pkg.selection_rules ? JSON.stringify(pkg.selection_rules) : '';
        }
        
        const ingDisplay = document.getElementById('pkgIngredientCostDisplay');
        if (ingDisplay) {
            ingDisplay.innerText = '₱' + (pkg.ingredient_total_cost || 0).toFixed(2) + ' / pax';
            ingDisplay.dataset.cost = pkg.ingredient_total_cost || 0;
        }

        calculateCosts();

        // Inclusions
        renderInclusions(pkg.inclusions || {});

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
        
        loadPkgMenuLibrary();

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
    if (activeInclusions) {
        Object.keys(activeInclusions).forEach(inc => {
            if (activeInclusions[inc]) allInclusions.add(inc);
        });
    }

    allInclusions.forEach(val => {
        const isChecked = activeInclusions ? activeInclusions[val] === true : false;
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
            <button type="button" onclick="window.editCustomInclusion(this, event)" style="color:var(--primary-color); border:none; background:none; cursor:pointer; font-size:11px;"><i class="fas fa-edit"></i></button>
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
        
        const leadTimeVal = parseInt(form.booking_lead_time.value);
        if (isNaN(leadTimeVal) || leadTimeVal < 3) {
            addError(form.booking_lead_time, "Lead time must be at least 3 days.");
        }

        const descVal = form.description.value.trim();
        if (!descVal || descVal.length < 10) {
            addError(form.description, "Please provide a short description (min 10 characters).");
        }
    }
    
    if (tabName === 'perks') {
        const checkedInclusions = document.querySelectorAll('input[name="inclusions"]:checked').length;
        if (checkedInclusions === 0) {
            isValid = false;
            if (!silent) {
                const matrix = document.getElementById('inclusionMatrix');
                if (matrix) {
                    matrix.style.border = '2px dashed #ef4444';
                    setTimeout(() => matrix.style.border = 'none', 3000);
                    
                    const badge = document.createElement('div');
                    badge.className = 'inline-error-badge text-center py-2';
                    badge.style = 'color: #ef4444; font-size: 11px; font-weight: 800; margin-top: 8px;';
                    badge.innerText = "Please select at least 1 inclusion or amenity.";
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
            addError(form.price_per_head, "Price per head must be greater than 0.");
        }
        
        const minGuests = parseInt(form.min_guests.value);
        if (isNaN(minGuests) || minGuests < 10) {
            addError(form.min_guests, "Minimum guests must be at least 10.");
        }
        
        const rawResFee = form.reservation_fee.value.replace(/,/g, '');
        const resFee = parseFloat(rawResFee);
        if (isNaN(resFee) || resFee <= 0) {
            addError(form.reservation_fee, "Reservation fee must be greater than 0.");
        } else if (price > 0 && minGuests > 0) {
            const maxAllowedFee = (price * minGuests) * 0.5; // 50% limit
            if (resFee > maxAllowedFee) {
                addError(form.reservation_fee, `Reservation fee cannot exceed 50% of the total base package cost (₱${maxAllowedFee.toLocaleString()}).`);
            }
        }
        
        // Anti-Bankruptcy Margin Check
        const internalInput = document.getElementById('pkgInternalCostPerPax');
        if (internalInput) {
            const internalCost = parseFloat(internalInput.value) || 0;
            if (price < internalCost) {
                addError(form.price_per_head, `Selling Price (₱${price}) cannot be lower than the Est. Cost / Pax (₱${internalCost.toFixed(2)}). You will lose money on every booking.`);
            }
        }

        // Validate overhead costs
        if (form.labor_cost && (form.labor_cost.value === '' || parseFloat(form.labor_cost.value) < 0)) addError(form.labor_cost, "Cannot be empty or negative.");
        if (form.utility_cost && (form.utility_cost.value === '' || parseFloat(form.utility_cost.value) < 0)) addError(form.utility_cost, "Cannot be empty or negative.");
        if (form.equipment_cost && (form.equipment_cost.value === '' || parseFloat(form.equipment_cost.value) < 0)) addError(form.equipment_cost, "Cannot be empty or negative.");
        if (form.base_pax && (form.base_pax.value === '' || parseInt(form.base_pax.value) < 1)) addError(form.base_pax, "Must be at least 1.");
        
        const rawMinContract = form.min_contract_amount.value.replace(/,/g, '');
        if (rawMinContract) {
            const minContract = parseFloat(rawMinContract);
            if (isNaN(minContract) || minContract < 0) {
                addError(form.min_contract_amount, "Invalid amount.");
            }
        }
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
    
    const isAllValid = isBasicValid && isPerksValid && isMenuValid && isPricingValid;
    
    // Enable or disable Save Package button reactively
    const saveBtn = document.getElementById('pkgSaveBtn');
    if (saveBtn) {
        if (isAllValid) {
            saveBtn.style.opacity = '1';
            saveBtn.style.background = 'var(--primary-color)';
            saveBtn.innerHTML = '<i class="fas fa-check-circle"></i> Save Package';
            saveBtn.disabled = false;
            saveBtn.style.cursor = 'pointer';
            saveBtn.style.pointerEvents = 'auto';
        } else {
            saveBtn.style.opacity = '0.7'; 
            saveBtn.style.background = '#94a3b8';
            saveBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Form Incomplete';
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
    if (pricingStep) {
        if (isBasicValid && isPerksValid && isMenuValid) {
            pricingStep.style.opacity = '1';
            pricingStep.style.pointerEvents = 'auto';
        } else {
            pricingStep.style.opacity = '0.4';
            pricingStep.style.pointerEvents = 'none';
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
        const stepsOrder = ['basic', 'perks', 'menu', 'pricing'];
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
    const stepsOrder = ['basic', 'perks', 'menu', 'pricing'];
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

        container.innerHTML = '';
        if (library.length === 0) {
            container.innerHTML = '<div class="text-center py-5 text-slate-400 text-xs">Your library is currently empty.</div>';
            return;
        }

        container.innerHTML = library.map(item => {
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
                        <div style="font-size: 0.75rem; color: #64748b; font-weight: 700; margin-top: 2px;">₱${(item.cost_price || 0).toLocaleString('en-PH', {minimumFractionDigits: 2})} cost</div>
                    </div>
                    <input type="checkbox" name="linked_menu_ids" value="${item.id}" ${isSelected ? 'checked' : ''} style="display:none;">
                </div>
            `;
        }).join('');
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
}

function filterPkgMenuLibrary() {
    const query = document.getElementById('pkgMenuLibrarySearch')?.value.toLowerCase() || '';
    document.querySelectorAll('.menu-select-card').forEach(card => {
        const name = card.querySelector('h6')?.innerText.toLowerCase() || '';
        card.style.display = name.includes(query) ? 'flex' : 'none';
    });
}

function calculateCosts() {
    const labor = parseFloat(document.getElementById('pkgLaborCost')?.value) || 0;
    const utility = parseFloat(document.getElementById('pkgUtilityCost')?.value) || 0;
    const equip = parseFloat(document.getElementById('pkgEquipmentCost')?.value) || 0;
    const basePax = parseInt(document.getElementById('pkgBasePax')?.value) || 50;
    // Sum selected menu items cost from Step 3 (Only if library is loaded)
    const menuCards = document.querySelectorAll('.menu-select-card');
    if (menuCards.length > 0) {
        let ingCostPerPax = 0;
        document.querySelectorAll('.menu-select-card.selected').forEach(card => {
            ingCostPerPax += parseFloat(card.dataset.cost) || 0;
        });

        const ingDisplay = document.getElementById('pkgIngredientCostDisplay');
        if (ingDisplay) {
            ingDisplay.innerText = '₱' + ingCostPerPax.toFixed(2) + ' / pax';
            ingDisplay.dataset.cost = ingCostPerPax;
        }
    }

    const ingDisplay = document.getElementById('pkgIngredientCostDisplay');
    const ingCostPerPax = parseFloat(ingDisplay?.dataset?.cost) || 0;

    let overheadTotal = labor + utility + equip;
    let overheadPerPax = basePax > 0 ? overheadTotal / basePax : 0;
    let totalCostPerPax = overheadPerPax + ingCostPerPax;

    const display = document.getElementById('totalCostDisplay');
    if (display) display.innerText = '₱' + totalCostPerPax.toLocaleString(undefined, { minimumFractionDigits: 2 });

    const internalInput = document.getElementById('pkgInternalCostPerPax');
    if (internalInput) internalInput.value = totalCostPerPax;

    const manualPriceInput = document.getElementById('pkgManualPriceInput');
    const manualPrice = manualPriceInput ? parseFloat(manualPriceInput.value.replace(/,/g, '')) || 0 : 0;
    const badge = document.getElementById('roiMarginBadge');
    
    if (badge) {
        if (manualPrice > 0) {
            const profit = manualPrice - totalCostPerPax;
            const margin = (profit / manualPrice) * 100;
            
            badge.innerText = `${margin.toFixed(1)}% Margin`;
            
            if (margin < 0) {
                badge.style.background = '#fee2e2';
                badge.style.color = '#ef4444';
                badge.innerText = `LOSS: ${Math.abs(margin).toFixed(1)}%`;
                badge.classList.add('margin-pulse-warning');
            } else if (margin < 25) {
                badge.style.background = '#fff7ed';
                badge.style.color = '#f97316';
                badge.classList.remove('margin-pulse-warning');
            } else {
                badge.style.background = '#f0fdf4';
                badge.style.color = '#22c55e';
                badge.classList.remove('margin-pulse-warning');
            }
        } else {
            badge.innerText = '--% Margin';
            badge.style.background = '#f1f5f9';
            badge.style.color = '#64748b';
            badge.classList.remove('margin-pulse-warning');
        }
    }
}

function showMenuModal(pkgId, pkgName) {
    if (!pkgId) return;
    currentPackageId = pkgId;
    const title = document.getElementById('targetPkgDisplay');
    if (title) title.innerText = `Package: ${pkgName}`;
    
    const menuPkgIdInput = document.getElementById('modalMenuPackageId');
    if (menuPkgIdInput) menuPkgIdInput.value = pkgId;
    
    switchMenuMode('current');
    
    safeOpenModal('menuModal');
}

function hideMenuModal() {
    safeCloseModal('menuModal');
}

async function switchMenuMode(mode) {
    document.querySelectorAll('.mtab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('#menuModal .tab-pane-pro').forEach(p => p.style.display = 'none');
    
    const activeBtn = document.querySelector(`.mtab-btn[onclick="window.switchMenuMode('${mode}')"]`);
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
        if (!res.ok) throw new Error("Failed to load menu items");
        const items = await res.json();
        
        if (items.length === 0) {
            container.innerHTML = '<div class="text-center py-10 text-slate-400">No items curated for this package yet.</div>';
            return;
        }

        container.innerHTML = items.map(item => `
            <div class="menu-item-pro-row" style="display: flex; align-items: center; gap: 1rem; background: #fff; padding: 0.75rem; border-radius: 0.5rem; border: 1px solid #e2e8f0; border-left: 4px solid var(--primary-color); margin-bottom: 0.5rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                <img src="${item.image_url || DISH_PLACEHOLDER}" class="dish-thumb" style="width: 40px; height: 40px; border-radius: 0.5rem; object-fit: cover;">
                <div class="dish-info-pro" style="flex: 1;">
                    <h6 style="margin: 0; font-size: 0.85rem; font-weight: 700; color: #1e293b;">${item.name}</h6>
                    <span style="font-size: 0.7rem; color: #94a3b8;">${item.category}</span>
                </div>
                <button type="button" onclick="window.unlinkDish(${item.id})" class="text-red-500 hover:text-red-700" style="border:none; background:none; cursor:pointer; font-size: 1.1rem; padding: 0.5rem; transition: color 0.2s;" title="Unlink Dish"><i class="fas fa-unlink"></i></button>
            </div>
        `).join('');
    } catch (e) {
        console.error("[Packages] Error loading package menu:", e);
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
        const linkedIds = Array.isArray(linkedItems) ? linkedItems.map(i => i.id) : [];

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
                        `<button type="button" onclick="window.linkDish(${item.id})" class="btn-sm-outline" style="font-size: 10px; padding: 0.25rem 0.5rem;">Link Dish</button>`
                    }
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error("[Packages] Error loading library items:", e);
        container.innerHTML = '<div class="text-center py-5 text-red-500">Error loading library.</div>';
    }
}

function filterLibraryItems() {
    const query = document.getElementById('librarySearchInput')?.value.toLowerCase() || '';
    document.querySelectorAll('.library-item-row').forEach(row => {
        const name = row.dataset.name || '';
        row.style.display = name.includes(query) ? 'flex' : 'none';
    });
}

async function linkDish(dishId) {
    if (!window.apiAction) return;
    
    const doLink = async () => {
        const formData = new FormData();
        formData.append('item_id', dishId);
        
        const res = await window.apiAction(`/caterer/packages/${currentPackageId}/menu/link`, {
            method: 'POST',
            body: formData
        });
        if (res) loadLibraryItems();
    };

    if (window.showConfirm) {
        window.showConfirm('Link this dish to the current package?', doLink, 'Link Dish', 'Yes, Link It', 'success');
    } else {
        if (confirm('Link this dish?')) doLink();
    }
}

async function unlinkDish(dishId) {
    if (!window.apiAction) return;
    
    const doUnlink = async () => {
        const res = await window.apiAction(`/caterer/packages/${currentPackageId}/menu/${dishId}/unlink`, {
            method: 'POST'
        });
        if (res) loadPackageMenu();
    };

    if (window.showConfirm) {
        window.showConfirm('Are you sure you want to remove this dish from the package?', doUnlink, 'Unlink Dish', 'Yes, Unlink', 'danger');
    } else {
        if (confirm('Remove this dish from the package?')) doUnlink();
    }
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
