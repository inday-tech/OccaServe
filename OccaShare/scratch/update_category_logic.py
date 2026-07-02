import re

file_path = r"c:\OccaServe\OccaShare\app\static\js\caterer\packages.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_logic = """        library.forEach(item => {
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
        });"""

new_logic = """        library.forEach(item => {
            if (item.is_addon) {
                addonCats.push(item);
            } else if (String(item.id).startsWith('eq_')) {
                eqCats.push(item);
            } else if (String(item.id).startsWith('svc_')) {
                svcCats.push(item);
            } else {
                foodCats.push(item);
            }
        });"""

if old_logic in content:
    content = content.replace(old_logic, new_logic)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Logic replaced successfully.")
else:
    print("Could not find the old logic.")
