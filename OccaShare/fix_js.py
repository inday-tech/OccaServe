import re
with open(r'C:\OccaServe\OccaShare\app\static\js\caterer\packages.js', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Make it append instead of replace
old_js = '''        // Populate Add-ons Tab
        const addonsGrid = document.getElementById('addonsGrid');
        if (addonsGrid) {
            const addonsLibrary = library.filter(item => item.is_addon === true);
            if (addonsLibrary.length === 0) {
                addonsGrid.innerHTML = '<div class="text-center py-5 text-slate-400 text-xs" style="grid-column: 1 / -1;">No add-ons available in your inventory.</div>';
            } else {
                addonsGrid.innerHTML = addonsLibrary.map(item => {'''

new_js = '''        // Populate Add-ons Tab
        const addonsGrid = document.getElementById('addonsGrid');
        if (addonsGrid) {
            const addonsLibrary = library.filter(item => item.is_addon === true);
            if (addonsLibrary.length > 0) {
                // Remove the "no add-ons" placeholder if it exists (but keep server-rendered items)
                const noAddons = addonsGrid.querySelector('.no-addons-placeholder');
                if (noAddons) noAddons.remove();
                
                addonsGrid.innerHTML += addonsLibrary.map(item => {'''

content = content.replace(old_js, new_js)

old_js_2 = '''                }).join('');
            }
        }'''

new_js_2 = '''                }).join('');
            }
        }'''
# Actually we don't need to change the bottom.

with open(r'C:\OccaServe\OccaShare\app\static\js\caterer\packages.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
