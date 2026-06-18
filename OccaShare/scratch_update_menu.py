import re

filepath = 'c:/OccaServe/OccaShare/templates/caterer/menu.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

modal_pattern = r'<!-- Add/Edit Menu Modal -->.*?<!-- Archive Dish Modal -->'
new_modal = """<!-- Add/Edit Menu Modal -->
<div id="menuModal" class="occ-modal-overlay">
    <div class="occ-modal-box sz-md occ-content-pop">
        <div class="occ-modal-header glass-header">
            <div>
                <h3 id="menuModalTitle" class="occ-modal-title"><i class="fas fa-utensils-alt"></i> Add New Dish</h3>
                <div class="occ-modal-subtitle">Configure your dish details and pricing strategy.</div>
            </div>
            <button onclick="window.closeModal('menuModal')" class="occ-modal-close">
                <i class="fas fa-times"></i>
            </button>
        </div>

        <form id="menuForm" action="/caterer/menu/add" method="POST" enctype="multipart/form-data" novalidate>
            <div class="occ-modal-body compact-body" style="max-height: 70vh; overflow-y: auto;">
                <div id="menuErrorDrawer" class="error-drawer"></div>
                
                <div class="form-group-pro">
                    <label>Dish Name *</label>
                    <input type="text" name="name" class="control-pro" placeholder="e.g. Chicken Cordon Bleu" required minlength="2" maxlength="100">
                    <div class="invalid-feedback"></div>
                </div>

                <div class="form-row-pro">
                    <div class="form-group-pro">
                        <label>Category *</label>
                        <select name="category" id="modalCategory" class="control-pro" required onchange="toggleCustomCategory()">
                            <option value="Chicken">Chicken</option>
                            <option value="Pork">Pork</option>
                            <option value="Beef">Beef</option>
                            <option value="Seafood">Seafood</option>
                            <option value="Vegetable">Vegetable</option>
                            <option value="Pasta">Pasta</option>
                            <option value="Dessert">Dessert</option>
                            <option value="Drinks">Drinks</option>
                            <option value="Other">Others</option>
                        </select>
                        <input type="text" name="custom_category" id="customCategoryInput" class="control-pro" placeholder="Type specific category" style="display: none; margin-top: 10px;">
                    </div>
                    <div class="form-group-pro">
                        <label>Unit Type *</label>
                        <select name="unit_type" id="modalUnitType" class="control-pro" required>
                            <option value="Per Pax">Per Pax</option>
                            <option value="Per Tray">Per Tray</option>
                            <option value="Per Bilao">Per Bilao</option>
                            <option value="Per Order">Per Order</option>
                        </select>
                    </div>
                </div>

                <div class="form-group-pro">
                    <label>Description</label>
                    <textarea name="description" class="control-pro" placeholder="Short description of the dish..." maxlength="500" style="height: 80px;"></textarea>
                </div>

                <div class="form-row-pro">
                    <div class="form-group-pro">
                        <label>Estimated Cost (₱) * <i class="fas fa-info-circle text-muted" title="Internal cost used for profit and ROI computation."></i></label>
                        <input type="text" name="cost_price" id="cost_price_input" class="control-pro js-format-comma" placeholder="0" required inputmode="numeric">
                    </div>
                    <div class="form-group-pro">
                        <label>Selling Price (₱) * <i class="fas fa-info-circle text-muted" title="Price charged to customers."></i></label>
                        <input type="text" name="price" id="price_input" class="control-pro js-format-comma" placeholder="0" required inputmode="numeric">
                    </div>
                </div>
                
                <div class="margin-analytics-pro" id="roiMarginBadge" style="margin-bottom: 20px;">Profit: --</div>

                <div class="form-row-pro">
                    <div class="form-group-pro">
                        <label>Status *</label>
                        <select name="status" id="modalStatus" class="control-pro" required>
                            <option value="available">Available</option>
                            <option value="unavailable">Unavailable</option>
                        </select>
                    </div>
                    <div class="form-group-pro">
                        <!-- Spacer -->
                    </div>
                </div>

                <div class="form-group-pro">
                    <label>Dish Image</label>
                    <div class="photo-dropzone-pro" id="photoDropzone" onclick="document.getElementById('menuImageInput').click()">
                        <i class="fas fa-camera"></i>
                        <span>Upload dish photo</span>
                        <input type="file" name="image" id="menuImageInput" accept="image/*" style="display: none;" onchange="previewImage(event)">
                    </div>
                    <div id="imagePreviewContainer" class="preview-box-pro" style="display: none;">
                        <img id="imagePreview" src="" class="img-preview-pro" alt="Preview">
                        <button type="button" class="btn-remove-img-pro" onclick="removeImage()"><i class="fas fa-times"></i></button>
                    </div>
                </div>
            </div>

            <div class="occ-modal-footer">
                <button type="button" class="btn-secondary-pro" style="min-width:100px;" onclick="window.closeModal('menuModal')">Cancel</button>
                <button type="submit" class="btn-primary-pro" style="padding:0 var(--space-xl);">Save Dish</button>
            </div>
        </form>
    </div>
</div>

<!-- Archive Dish Modal -->"""

content = re.sub(modal_pattern, new_modal, content, flags=re.DOTALL)

js_pattern = r'function switchDishTab\(tabId\) \{.*?function openAddMenuModal\(\) \{'
new_js = """function openAddMenuModal() {"""
content = re.sub(js_pattern, new_js, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated menu.html")
