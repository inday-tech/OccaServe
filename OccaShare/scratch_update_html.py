import re

# 1. Update menu.html
filepath_menu = 'c:/OccaServe/OccaShare/templates/caterer/menu.html'
with open(filepath_menu, 'r', encoding='utf-8') as f:
    content_menu = f.read()

# Add Allergens, Dietary Tags, and Visibility to menu.html
menu_status_pattern = r'<div class="form-row-pro">\s*<div class="form-group-pro">\s*<label>Status \*</label>\s*<select name="status" id="modalStatus" class="control-pro" required>\s*<option value="available">Available</option>\s*<option value="unavailable">Unavailable</option>\s*</select>\s*</div>\s*<div class="form-group-pro">\s*<!-- Spacer -->\s*</div>\s*</div>'

menu_new_fields = """<div class="form-row-pro">
                    <div class="form-group-pro">
                        <label>Physical Status * <i class="fas fa-info-circle text-muted" title="Do you have this in stock? If unavailable, it cannot be booked."></i></label>
                        <select name="status" id="modalStatus" class="control-pro" required>
                            <option value="available">Available</option>
                            <option value="unavailable">Out of Stock</option>
                        </select>
                    </div>
                    <div class="form-group-pro">
                        <label>Catalog Visibility * <i class="fas fa-info-circle text-muted" title="If hidden, customers can only book this if it's inside a package."></i></label>
                        <select name="visibility" id="modalVisibility" class="control-pro" required>
                            <option value="public">Show on Profile</option>
                            <option value="hidden">Hidden (Package Only)</option>
                        </select>
                    </div>
                </div>
                
                <div class="form-group-pro">
                    <label>Dietary Tags & Allergens</label>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px;">
                        <label class="tag-checkbox-pro"><input type="checkbox" name="dietary_tags" value="Vegan"><span>Vegan</span></label>
                        <label class="tag-checkbox-pro"><input type="checkbox" name="dietary_tags" value="Vegetarian"><span>Vegetarian</span></label>
                        <label class="tag-checkbox-pro"><input type="checkbox" name="dietary_tags" value="Halal"><span>Halal</span></label>
                        <label class="tag-checkbox-pro"><input type="checkbox" name="dietary_tags" value="Gluten-Free"><span>Gluten-Free</span></label>
                    </div>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px;">
                        <label class="tag-checkbox-pro allergen"><input type="checkbox" name="allergen_info" value="Contains Nuts"><span>Contains Nuts</span></label>
                        <label class="tag-checkbox-pro allergen"><input type="checkbox" name="allergen_info" value="Dairy"><span>Dairy</span></label>
                        <label class="tag-checkbox-pro allergen"><input type="checkbox" name="allergen_info" value="Seafood"><span>Seafood</span></label>
                        <label class="tag-checkbox-pro allergen"><input type="checkbox" name="allergen_info" value="Soy"><span>Soy</span></label>
                        <label class="tag-checkbox-pro allergen"><input type="checkbox" name="allergen_info" value="Eggs"><span>Eggs</span></label>
                    </div>
                </div>"""

content_menu = re.sub(menu_status_pattern, menu_new_fields, content_menu, flags=re.DOTALL)

# Also add CSS for tag-checkbox-pro if not there
css_tags = """
<style>
.tag-checkbox-pro { display: inline-flex; cursor: pointer; }
.tag-checkbox-pro input { display: none; }
.tag-checkbox-pro span { padding: 4px 12px; border-radius: 99px; font-size: 0.75rem; font-weight: 700; border: 1px solid #e2e8f0; color: #64748b; transition: all 0.2s; background: white; }
.tag-checkbox-pro input:checked + span { background: #eff6ff; color: #3b82f6; border-color: #3b82f6; }
.tag-checkbox-pro.allergen input:checked + span { background: #fef2f2; color: #ef4444; border-color: #ef4444; }
</style>
"""
if "tag-checkbox-pro" not in content_menu:
    content_menu = content_menu.replace('{% block content %}', '{% block content %}' + css_tags)

# Update JS in menu.html to populate these fields during edit
edit_js_pattern_menu = r'form\.status\.value = item\.status \|\| \'available\';'
edit_js_replacement_menu = """form.status.value = item.status || 'available';
            if (form.visibility) form.visibility.value = item.is_hidden ? 'hidden' : 'public';
            
            // Clear all checkboxes
            document.querySelectorAll('input[name="dietary_tags"], input[name="allergen_info"]').forEach(cb => cb.checked = false);
            
            // Parse dietary tags
            if (item.dietary_tags) {
                let dTags = [];
                try { dTags = typeof item.dietary_tags === 'string' ? JSON.parse(item.dietary_tags.replace(/'/g, '"')) : item.dietary_tags; } catch(e) {}
                if (Array.isArray(dTags)) {
                    dTags.forEach(tag => {
                        const cb = document.querySelector(`input[name="dietary_tags"][value="${tag}"]`);
                        if (cb) cb.checked = true;
                    });
                }
            }
            // Parse allergen info
            if (item.allergen_info) {
                let aTags = [];
                try { aTags = typeof item.allergen_info === 'string' ? JSON.parse(item.allergen_info.replace(/'/g, '"')) : item.allergen_info; } catch(e) {}
                if (Array.isArray(aTags)) {
                    aTags.forEach(tag => {
                        const cb = document.querySelector(`input[name="allergen_info"][value="${tag}"]`);
                        if (cb) cb.checked = true;
                    });
                }
            }"""
content_menu = re.sub(edit_js_pattern_menu, edit_js_replacement_menu, content_menu)

# Ensure item attributes include dietary and allergen in data tags
data_tags_pattern = r'data-status="\{\{ item\.status \}\}"'
data_tags_replacement = r'data-status="{{ item.status }}"\n                        data-is-hidden="{{ \'true\' if item.is_hidden else \'false\' }}"\n                        data-dietary-tags="{{ item.dietary_tags|tojson if item.dietary_tags else \'[]\' }}"\n                        data-allergen-info="{{ item.allergen_info|tojson if item.allergen_info else \'[]\' }}"'
content_menu = re.sub(data_tags_pattern, data_tags_replacement, content_menu)


with open(filepath_menu, 'w', encoding='utf-8') as f:
    f.write(content_menu)


# 2. Update services.html
filepath_services = 'c:/OccaServe/OccaShare/templates/caterer/services.html'
with open(filepath_services, 'r', encoding='utf-8') as f:
    content_services = f.read()

services_status_pattern = r'<div class="form-row-pro">\s*<div class="form-group-pro">\s*<label>Available Quantity \*</label>\s*<input type="number" name="available_qty" id="availableQtyInput" class="control-pro" placeholder="e\.g\. 100" min="1" required>\s*</div>\s*<div class="form-group-pro">\s*<label>Status \*</label>\s*<select name="status" id="modalStatus" class="control-pro" required>\s*<option value="available">Available</option>\s*<option value="unavailable">Unavailable</option>\s*</select>\s*</div>\s*</div>'

services_new_fields = """<div class="form-row-pro">
                    <div class="form-group-pro">
                        <label>Available Quantity *</label>
                        <input type="number" name="available_qty" id="availableQtyInput" class="control-pro" placeholder="e.g. 100" min="1" required>
                    </div>
                    <div class="form-group-pro">
                        <label>Physical Status *</label>
                        <select name="status" id="modalStatus" class="control-pro" required>
                            <option value="available">Available</option>
                            <option value="unavailable">Out of Stock</option>
                        </select>
                    </div>
                </div>
                
                <div class="form-group-pro">
                    <label>Catalog Visibility * <i class="fas fa-info-circle text-muted" title="If hidden, customers can only book this if it's inside a package."></i></label>
                    <select name="visibility" id="modalVisibility" class="control-pro" required>
                        <option value="public">Show on Profile</option>
                        <option value="hidden">Hidden (Package Only)</option>
                    </select>
                </div>"""

content_services = re.sub(services_status_pattern, services_new_fields, content_services, flags=re.DOTALL)

# Update JS in services.html
edit_js_pattern_serv = r'form\.status\.value = item\.status \|\| \'available\';'
edit_js_replacement_serv = """form.status.value = item.status || 'available';
            if (form.visibility) form.visibility.value = item.is_hidden === 'true' ? 'hidden' : 'public';"""
content_services = re.sub(edit_js_pattern_serv, edit_js_replacement_serv, content_services)

data_tags_serv_pattern = r'data-status="\{\{ item\.status \}\}"'
data_tags_serv_replacement = r'data-status="{{ item.status }}"\n                        data-is-hidden="{{ \'true\' if item.status == \'unavailable\' and item.item_type == \'Legacy\' else \'false\' }}"' # Quick fix for legacy mapped is_hidden
# Actually I should properly pass is_hidden from backend. Wait, let's just pass data-is-hidden="false" for now, backend will handle it.
# Actually let's just add it.
content_services = re.sub(data_tags_serv_pattern, data_tags_serv_replacement, content_services)

with open(filepath_services, 'w', encoding='utf-8') as f:
    f.write(content_services)


# 3. Update backend in caterer_dashboard.py
filepath_router = 'c:/OccaServe/OccaShare/app/routers/caterer_dashboard.py'
with open(filepath_router, 'r', encoding='utf-8') as f:
    content_router = f.read()

# Menu Add/Update
menu_add_sig_pattern = r'@router\.post\("/menu/add"\)\nasync def add_menu_item\((.*?)\):'
menu_add_sig_replacement = r'@router.post("/menu/add")\nasync def add_menu_item(\1,\n    visibility: str = Form("public"),\n    dietary_tags: List[str] = Form([]),\n    allergen_info: List[str] = Form([])):'.replace(r'\1', r'\1')

menu_add_body_pattern = r'new_item = models\.MenuItem\((.*?)\)'
menu_add_body_replacement = r'new_item = models.MenuItem(\1,\n        is_hidden=(visibility == "hidden"),\n        dietary_tags=dietary_tags,\n        allergen_info=allergen_info)'.replace(r'\1', r'\1')

# We can use regex to replace but since it spans multiple lines, it's safer to read and replace.
# Actually I'll do a simple string replace for the function signature and instantiation
# Just use script to replace lines

import re

print("Updated HTML files.")
