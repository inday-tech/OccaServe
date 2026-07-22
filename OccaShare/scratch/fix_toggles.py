import os

html_path = r"c:\OccaServe\OccaShare\templates\caterer\packages.html"
js_path = r"c:\OccaServe\OccaShare\app\static\js\caterer\packages.js"

# 1. FIX HTML (Check the toggles by default and make sidebars visible by default)
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Make sidebar buttons visible by default
html = html.replace(
    '<div id="step-btn-food" class="pkg-step-side" onclick="window.switchPackageTab(this, \'food\')" style="display: none;">',
    '<div id="step-btn-food" class="pkg-step-side" onclick="window.switchPackageTab(this, \'food\')" style="display: flex;">'
)
html = html.replace(
    '<div id="step-btn-services" class="pkg-step-side" onclick="window.switchPackageTab(this, \'services\')" style="display: none;">',
    '<div id="step-btn-services" class="pkg-step-side" onclick="window.switchPackageTab(this, \'services\')" style="display: flex;">'
)
html = html.replace(
    '<div id="step-btn-equipment" class="pkg-step-side" onclick="window.switchPackageTab(this, \'equipment\')" style="display: none;">',
    '<div id="step-btn-equipment" class="pkg-step-side" onclick="window.switchPackageTab(this, \'equipment\')" style="display: flex;">'
)

# Make toggles checked by default
html = html.replace(
    '<input id="toggle-food" onchange="window.togglePackageComponent(\'food\', this.checked)" type="checkbox"/>',
    '<input id="toggle-food" onchange="window.togglePackageComponent(\'food\', this.checked)" type="checkbox" checked/>'
)
html = html.replace(
    '<input id="toggle-services" onchange="window.togglePackageComponent(\'services\', this.checked)" type="checkbox"/>',
    '<input id="toggle-services" onchange="window.togglePackageComponent(\'services\', this.checked)" type="checkbox" checked/>'
)
html = html.replace(
    '<input id="toggle-equipment" onchange="window.togglePackageComponent(\'equipment\', this.checked)" type="checkbox"/>',
    '<input id="toggle-equipment" onchange="window.togglePackageComponent(\'equipment\', this.checked)" type="checkbox" checked/>'
)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

# 2. FIX JS (Initialize toggles on openAddPackageModal and editPackage)
with open(js_path, "r", encoding="utf-8") as f:
    js = f.read()

open_add_modal_replacement = """        // Clear checked inclusions
        document.querySelectorAll('input[name="linked_menu_ids"]').forEach(cb => cb.checked = false);

        // Reset toggles to ON
        let tFood = document.getElementById('toggle-food');
        let tSvc = document.getElementById('toggle-services');
        let tEq = document.getElementById('toggle-equipment');
        if (tFood) tFood.checked = true;
        if (tSvc) tSvc.checked = true;
        if (tEq) tEq.checked = true;
        if (window.togglePackageComponent) {
            window.togglePackageComponent('food', true);
            window.togglePackageComponent('services', true);
            window.togglePackageComponent('equipment', true);
        }

        await loadPkgMenuLibrary();"""

js = js.replace("""        // Clear checked inclusions
        document.querySelectorAll('input[name="linked_menu_ids"]').forEach(cb => cb.checked = false);

        await loadPkgMenuLibrary();""", open_add_modal_replacement)


edit_modal_replacement = """        if (form.selection_rules) {
            form.selection_rules.value = pkg.selection_rules ? JSON.stringify(pkg.selection_rules) : '';
        }
        
        // Wait for library to load so we can determine toggles based on existing selections
        await loadPkgMenuLibrary();
        
        // Determine what toggles should be on based on what's checked
        setTimeout(() => {
            let hasFood = document.querySelectorAll('#tab-food input[name="linked_menu_ids"]:checked').length > 0;
            let hasServices = document.querySelectorAll('#tab-services input[name="linked_menu_ids"]:checked').length > 0;
            let hasEquipment = document.querySelectorAll('#tab-equipment input[name="linked_menu_ids"]:checked').length > 0;
            
            // If it's a new package, or they really have none, just default them to ON or OFF
            // Let's assume they only turn on what they have
            let tFood = document.getElementById('toggle-food');
            let tSvc = document.getElementById('toggle-services');
            let tEq = document.getElementById('toggle-equipment');
            
            // If nothing is checked (e.g. brand new draft), turn all on by default to be safe
            if (!hasFood && !hasServices && !hasEquipment) {
                hasFood = hasServices = hasEquipment = true;
            }
            
            if (tFood) { tFood.checked = hasFood; window.togglePackageComponent('food', hasFood); }
            if (tSvc) { tSvc.checked = hasServices; window.togglePackageComponent('services', hasServices); }
            if (tEq) { tEq.checked = hasEquipment; window.togglePackageComponent('equipment', hasEquipment); }
        }, 100);"""
        
js = js.replace("""        if (form.selection_rules) {
            form.selection_rules.value = pkg.selection_rules ? JSON.stringify(pkg.selection_rules) : '';
        }

        // Image Preview Handling""", edit_modal_replacement + "\n\n        // Image Preview Handling")

# Also, ensure 'filterServices' and 'filterEquipment' are defined
filter_functions = """
window.filterServices = function() {
    const searchVal = document.getElementById('pkgServicesSearch').value.toLowerCase();
    const container = document.getElementById('inc-services-grid');
    if (!container) return;
    const cards = container.querySelectorAll('.menu-select-card');
    cards.forEach(card => {
        card.style.display = card.textContent.toLowerCase().includes(searchVal) ? 'flex' : 'none';
    });
};

window.filterEquipment = function() {
    const searchVal = document.getElementById('pkgEquipmentSearch').value.toLowerCase();
    const container = document.getElementById('inc-equipment-grid');
    if (!container) return;
    const cards = container.querySelectorAll('.menu-select-card');
    cards.forEach(card => {
        card.style.display = card.textContent.toLowerCase().includes(searchVal) ? 'flex' : 'none';
    });
};
"""
js = js + "\n" + filter_functions

with open(js_path, "w", encoding="utf-8") as f:
    f.write(js)
