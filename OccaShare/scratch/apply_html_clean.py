import re

f = r'c:\OccaServe\OccaShare\templates\caterer\packages.html'
with open(f, 'r', encoding='utf-8') as file:
    content = file.read()

# 1. Update Footer
old_footer = """            <div class="occ-modal-footer" id="pkgWizardFooter" style="padding: 1.25rem 2rem; background: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <button type="button" class="btn-secondary-pro" onclick="window.goToWizardBackStep()" id="btnWizardBack" style="display: none;"><i class="fas fa-arrow-left"></i> Back</button>
                </div>
                <div style="display: flex; gap: 12px;">
                    <button type="button" class="btn-secondary-pro" onclick="window.closePackageModal()">Cancel</button>
                    <button type="button" class="btn-primary-pro" id="btnWizardNext" onclick="window.goToWizardNextStep()">Next Step <i class="fas fa-arrow-right"></i></button>
                    <button type="submit" class="btn-primary-pro" id="pkgSaveBtn" style="display: none;">
                        Publish Package
                    </button>
                </div>
            </div>"""
new_footer = """            <div class="occ-modal-footer" id="pkgWizardFooter" style="padding: 1.25rem 2rem; background: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <button type="button" onclick="window.closePackageModal()" style="background: none; border: none; color: #64748b; font-weight: 700; font-size: 0.85rem; cursor: pointer; padding: 0.5rem 1rem;">Cancel</button>
                </div>
                <div style="display: flex; gap: 12px;">
                    <button type="button" class="btn-secondary-pro" onclick="window.goToWizardBackStep()" id="btnWizardBack" style="display: none;"><i class="fas fa-arrow-left"></i> Back</button>
                    <button type="button" class="btn-primary-pro" id="btnWizardNext" onclick="window.goToWizardNextStep()">Next Step <i class="fas fa-arrow-right"></i></button>
                    <button type="submit" class="btn-primary-pro" id="pkgSaveBtn" style="display: none; background: #22c55e; border-color: #22c55e;">
                        <i class="fas fa-check-circle" style="margin-right: 6px;"></i> Publish Package
                    </button>
                </div>
            </div>"""
content = content.replace(old_footer, new_footer)

# 2. Update Add-ons Tab
old_addons = """                    <!-- STEP 4: OPTIONAL ADD-ONS -->
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
new_addons = """                    <!-- STEP 4: OPTIONAL ADD-ONS -->
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
content = content.replace(old_addons, new_addons)

# 3. Inject Modals safely before the second {% endblock %} (which closes block content)
modal_html = """
<!-- Addon Picker Modal -->
<div id="addonPickerModal" class="occ-modal-overlay" style="z-index: 1060; display: none;">
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
<div id="addonConfigModal" class="occ-modal-overlay" style="z-index: 1070; display: none;">
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
"""
# The safest way is to find `{% block extra_js %}` and insert the modals right before the preceding `{% endblock %}`
# So we split by `{% block extra_js %}`
parts = content.split('{% block extra_js %}')
if len(parts) == 2:
    # Now find the last `{% endblock %}` in parts[0]
    idx = parts[0].rfind('{% endblock %}')
    if idx != -1:
        parts[0] = parts[0][:idx] + modal_html + '\n{% endblock %}\n\n'
    content = parts[0] + '{% block extra_js %}' + parts[1]
    
    with open(f, 'w', encoding='utf-8') as out:
        out.write(content)
    print("Re-applied correctly!")
else:
    print("Error parsing blocks.")
