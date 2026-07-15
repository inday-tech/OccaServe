import re

js_path = r"c:\OccaServe\OccaShare\app\static\js\caterer\packages.js"
with open(js_path, "r", encoding="utf-8") as f:
    js = f.read()

# 1. Update STEPS_ORDER
js = js.replace(
    "const STEPS_ORDER = ['basic', 'inclusions', 'menu', 'addons', 'pricing', 'booking', 'review'];",
    "let STEPS_ORDER = ['basic', 'components', 'food', 'services', 'equipment', 'addons', 'review'];\nconst ALL_STEPS = ['basic', 'components', 'food', 'services', 'equipment', 'addons', 'review'];"
)

# 2. Add Component Toggle Logic
toggle_logic = """
// --- NEW COMPONENT TOGGLE LOGIC ---
let packageComponents = { food: true, services: true, equipment: true };

window.togglePackageComponent = function(type, isEnabled) {
    packageComponents[type] = isEnabled;
    
    // Update STEPS_ORDER dynamically
    STEPS_ORDER = ['basic', 'components'];
    if (packageComponents.food) STEPS_ORDER.push('food');
    if (packageComponents.services) STEPS_ORDER.push('services');
    if (packageComponents.equipment) STEPS_ORDER.push('equipment');
    STEPS_ORDER.push('addons', 'review');
    
    // Hide/Show sidebar buttons
    document.getElementById('step-btn-food').style.display = packageComponents.food ? 'flex' : 'none';
    document.getElementById('step-btn-services').style.display = packageComponents.services ? 'flex' : 'none';
    document.getElementById('step-btn-equipment').style.display = packageComponents.equipment ? 'flex' : 'none';
    
    // Also clear selections if turned off
    if (!isEnabled) {
        let containerId = type === 'food' ? 'tab-food' : `tab-${type}`;
        let container = document.getElementById(containerId);
        if (container) {
            container.querySelectorAll('input[name="linked_menu_ids"]:checked').forEach(cb => {
                cb.checked = false;
                let card = cb.closest('.menu-select-card');
                if (card) {
                    card.classList.remove('selected');
                    card.style.background = 'white';
                    card.style.borderColor = '#e2e8f0';
                    let icon = card.querySelector('.fa-check-circle');
                    if(icon) icon.className = 'far fa-circle text-slate-300';
                }
            });
        }
    }
};

window.toggleFoodMode = function(mode) {
    let rulesContainer = document.getElementById('selectionRulesContainer');
    if (rulesContainer) {
        rulesContainer.parentElement.style.display = mode === 'customer' ? 'block' : 'none';
    }
};
// ----------------------------------
"""

js = js.replace("let currentPackageId = null;", "let currentPackageId = null;\n" + toggle_logic)

# 3. Update Validation
validation_old = """
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
"""

validation_new = """
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
    
    if (tabName === 'components') {
        if (!packageComponents.food && !packageComponents.services && !packageComponents.equipment) {
            isValid = false;
            if (window.showError) window.showError("Please include at least one package component (Food, Services, or Equipment).");
            else alert("Please include at least one package component.");
        }
    }
    
    if (['food', 'services', 'equipment'].includes(tabName)) {
        let container = document.getElementById(`tab-${tabName}`);
        if (container) {
            let checked = container.querySelectorAll('input[name="linked_menu_ids"]:checked');
            if (checked.length === 0) {
                isValid = false;
                let cap = tabName.charAt(0).toUpperCase() + tabName.slice(1);
                if (window.showError) window.showError(`Please select at least one item for ${cap}.`);
                else alert(`Please select at least one item for ${cap}.`);
            }
        }
    }
"""
js = js.replace(validation_old, validation_new)


with open(r"c:\OccaServe\OccaShare\scratch\packages_modified.js", "w", encoding="utf-8") as f:
    f.write(js)
