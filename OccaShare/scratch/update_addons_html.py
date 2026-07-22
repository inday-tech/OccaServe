import re

file_path = r"c:\OccaServe\OccaShare\templates\caterer\packages.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_tab = """                    <!-- STEP 4: OPTIONAL ADD-ONS -->
                    <div id="tab-addons" class="tab-pane-pro">
                        <div class="form-group-pro">
                            <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 1rem;">Offer optional upgrades that are NOT included in the base package (e.g. Lechon, Chocolate Fountain, Photo Booth).</p>
                            <div style="background:var(--color-neutral-50); border-radius:var(--border-radius); padding:var(--space-md); border:1px solid var(--color-neutral-200); margin-bottom:var(--space-md); max-height:350px; overflow-y:auto;">
                                <div class="menu-grid-scroll" id="addonsGrid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 1rem;">
                                    <!-- Will be populated dynamically by JS -->
                                </div>
                            </div>
                        </div>
                    </div>"""

new_tab = """                    <!-- STEP 4: OPTIONAL ADD-ONS -->
                    <div id="tab-addons" class="tab-pane-pro">
                        <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 1.5rem; line-height: 1.5;">Configure optional items that customers can add during package booking. Each add-on is specific to this package.</p>
                        
                        <!-- Menu Addons -->
                        <div style="margin-bottom: 2rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem; margin-bottom: 1rem;">
                                <h5 style="margin:0; font-size: 1rem; color: #1e293b;"><i class="fas fa-utensils text-brand" style="margin-right: 8px;"></i> Menu Add-ons</h5>
                                <button type="button" class="btn-secondary-pro" onclick="window.openAddonPicker('menu')" style="padding: 0.25rem 0.75rem; font-size: 0.75rem;"><i class="fas fa-plus"></i> Add Menu</button>
                            </div>
                            <div id="pkg-addons-menu-list" style="display: flex; flex-direction: column; gap: 0.75rem;">
                                <div class="text-slate-400 text-sm italic">No menu add-ons configured.</div>
                            </div>
                        </div>

                        <!-- Service Addons -->
                        <div style="margin-bottom: 2rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem; margin-bottom: 1rem;">
                                <h5 style="margin:0; font-size: 1rem; color: #1e293b;"><i class="fas fa-concierge-bell text-brand" style="margin-right: 8px;"></i> Service Add-ons</h5>
                                <button type="button" class="btn-secondary-pro" onclick="window.openAddonPicker('service')" style="padding: 0.25rem 0.75rem; font-size: 0.75rem;"><i class="fas fa-plus"></i> Add Service</button>
                            </div>
                            <div id="pkg-addons-service-list" style="display: flex; flex-direction: column; gap: 0.75rem;">
                                <div class="text-slate-400 text-sm italic">No service add-ons configured.</div>
                            </div>
                        </div>

                        <!-- Equipment Addons -->
                        <div style="margin-bottom: 1rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem; margin-bottom: 1rem;">
                                <h5 style="margin:0; font-size: 1rem; color: #1e293b;"><i class="fas fa-chair text-brand" style="margin-right: 8px;"></i> Equipment Add-ons</h5>
                                <button type="button" class="btn-secondary-pro" onclick="window.openAddonPicker('equipment')" style="padding: 0.25rem 0.75rem; font-size: 0.75rem;"><i class="fas fa-plus"></i> Add Equipment</button>
                            </div>
                            <div id="pkg-addons-equipment-list" style="display: flex; flex-direction: column; gap: 0.75rem;">
                                <div class="text-slate-400 text-sm italic">No equipment add-ons configured.</div>
                            </div>
                        </div>

                        <!-- Hidden Inputs for form submission -->
                        <input type="hidden" name="menu_addons" id="hidden_menu_addons" value="[]">
                        <input type="hidden" name="service_addons" id="hidden_service_addons" value="[]">
                        <input type="hidden" name="equipment_addons" id="hidden_equipment_addons" value="[]">
                    </div>"""

if old_tab in content:
    content = content.replace(old_tab, new_tab)
else:
    print("Could not find old addons tab.")


old_modals_end = """{% endblock %}"""
new_modals_end = """<!-- Addon Picker Modal -->
<div id="addonPickerModal" class="occ-modal-overlay" style="z-index: 1060;">
    <div class="occ-modal-box sz-md occ-content-pop">
        <div class="occ-modal-header glass-header">
            <div>
                <h3 class="occ-modal-title" id="addonPickerTitle">Select Items</h3>
            </div>
            <button type="button" onclick="window.closeAddonPicker()" class="occ-modal-close"><i class="fas fa-times"></i></button>
        </div>
        <div class="occ-modal-body" style="padding: 1rem;">
            <div style="position:relative; margin-bottom: 1rem;">
                <i class="fas fa-search" style="position:absolute; left:var(--space-sm); top:50%; transform:translateY(-50%); font-size:12px; color:var(--color-neutral-400);"></i>
                <input type="text" id="addonPickerSearch" placeholder="Search catalog..." onkeyup="window.filterAddonPicker()" class="control-pro" style="padding-left:2rem;">
            </div>
            <div id="addonPickerGrid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 1rem; max-height: 400px; overflow-y: auto; padding: 0.25rem;">
                <!-- Populated dynamically -->
            </div>
        </div>
        <div class="occ-modal-footer" style="padding: 1rem; background: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end; gap: 12px;">
            <button type="button" class="btn-secondary-pro" onclick="window.closeAddonPicker()">Cancel</button>
            <button type="button" class="btn-primary-pro" onclick="window.proceedToAddonConfig()">Configure Selected <i class="fas fa-arrow-right"></i></button>
        </div>
    </div>
</div>

<!-- Addon Config Modal -->
<div id="addonConfigModal" class="occ-modal-overlay" style="z-index: 1070;">
    <div class="occ-modal-box sz-md occ-content-pop">
        <div class="occ-modal-header glass-header">
            <div>
                <h3 class="occ-modal-title">Configure Add-ons</h3>
            </div>
            <button type="button" onclick="window.closeAddonConfig()" class="occ-modal-close"><i class="fas fa-times"></i></button>
        </div>
        <div class="occ-modal-body" style="padding: 1rem; max-height: 60vh; overflow-y: auto;" id="addonConfigFormsContainer">
            <!-- Populated dynamically -->
        </div>
        <div class="occ-modal-footer" style="padding: 1rem; background: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end; gap: 12px;">
            <button type="button" class="btn-secondary-pro" onclick="window.closeAddonConfig()">Cancel</button>
            <button type="button" class="btn-primary-pro" onclick="window.saveAddonConfig()"><i class="fas fa-save"></i> Add to Package</button>
        </div>
    </div>
</div>

{% endblock %}"""

content = content.replace(old_modals_end, new_modals_end)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Packages HTML updated.")
