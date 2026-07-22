import os
from bs4 import BeautifulSoup

html_path = r"c:\OccaServe\OccaShare\templates\caterer\packages.html"
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Find sidebar and replace its contents
sidebar = soup.find("div", class_="pkg-wizard-sidebar")
if sidebar:
    sidebar.clear()
    new_sidebar_html = """
                    <div id="step-btn-basic" class="pkg-step-side active" onclick="window.switchPackageTab(this, 'basic')">
                        <div class="step-icon-side"><i class="fas fa-info-circle"></i></div>
                        <div class="step-text-side"><span class="step-title-side">1. Basic Info & Pricing</span></div>
                    </div>
                    <div id="step-btn-components" class="pkg-step-side" onclick="window.switchPackageTab(this, 'components')">
                        <div class="step-icon-side"><i class="fas fa-cogs"></i></div>
                        <div class="step-text-side"><span class="step-title-side">2. Components</span></div>
                    </div>
                    <div id="step-btn-food" class="pkg-step-side" onclick="window.switchPackageTab(this, 'food')" style="display: none;">
                        <div class="step-icon-side"><i class="fas fa-utensils"></i></div>
                        <div class="step-text-side"><span class="step-title-side">3. Food Selection</span></div>
                    </div>
                    <div id="step-btn-services" class="pkg-step-side" onclick="window.switchPackageTab(this, 'services')" style="display: none;">
                        <div class="step-icon-side"><i class="fas fa-concierge-bell"></i></div>
                        <div class="step-text-side"><span class="step-title-side">4. Services</span></div>
                    </div>
                    <div id="step-btn-equipment" class="pkg-step-side" onclick="window.switchPackageTab(this, 'equipment')" style="display: none;">
                        <div class="step-icon-side"><i class="fas fa-chair"></i></div>
                        <div class="step-text-side"><span class="step-title-side">5. Equipment</span></div>
                    </div>
                    <div id="step-btn-addons" class="pkg-step-side" onclick="window.switchPackageTab(this, 'addons')">
                        <div class="step-icon-side"><i class="fas fa-plus-circle"></i></div>
                        <div class="step-text-side"><span class="step-title-side">6. Optional Add-ons</span></div>
                    </div>
                    <div id="step-btn-review" class="pkg-step-side" onclick="window.switchPackageTab(this, 'review')">
                        <div class="step-icon-side"><i class="fas fa-check-double"></i></div>
                        <div class="step-text-side"><span class="step-title-side">7. Review & Publish</span></div>
                    </div>
                 
                    <div class="sidebar-progress-wrapper" style="margin-top: auto; padding-top: 1rem;">
                         <div style="font-size: 10px; font-weight: 800; color: #94a3b8; margin-bottom: 8px; text-transform: uppercase;">Completion</div>
                         <div style="width: 100%; height: 6px; background: #e2e8f0; border-radius: var(--border-radius, 4px); overflow: hidden;">
                             <div id="pkgWizardProgress" style="width: 14%; height: 100%; background: var(--primary-color); transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);"></div>
                         </div>
                    </div>
    """
    sidebar.append(BeautifulSoup(new_sidebar_html, "html.parser"))

# Content Area
content_area = soup.find("div", class_="pkg-wizard-content")
if content_area:
    # We will restructure the tabs inside
    tabs = {t.get("id"): t for t in content_area.find_all("div", class_="tab-pane-pro")}
    
    # 1. Modify tab-basic (Combine basic, pricing, booking rules)
    basic_tab = tabs.get("tab-basic")
    pricing_tab = tabs.get("tab-pricing")
    booking_tab = tabs.get("tab-booking")
    
    if basic_tab and pricing_tab and booking_tab:
        # Move pricing fields to basic_tab
        # Just before the Cover Photo form-group, insert pricing mode UI
        cover_photo_group = basic_tab.find(lambda tag: tag.name == "div" and tag.get("class") == ["form-group-pro"] and tag.find("label") and "Cover Photo" in tag.find("label").text)
        
        pricing_html = """
                        <div class="pricing-overview-card" style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 1.5rem; border-radius: var(--border-radius); margin-bottom: 1.5rem;">
                            <h4 style="font-size: 1.1rem; font-weight: 800; color: #1e293b; margin-bottom: 1rem;"><i class="fas fa-tag"></i> Pricing Details</h4>
                            <div class="form-row-pro">
                                <div class="form-group-pro" style="flex: 1;">
                                    <label id="lblPricingMain">Price Per Guest (₱) *</label>
                                    <input type="text" name="price_per_head" id="pkgManualPriceInput" class="control-pro js-format-comma" style="font-size: 1.25rem; font-weight: 900; color: var(--primary-color);" placeholder="0.00" required maxlength="10">
                                </div>
                                <div class="form-group-pro" style="flex: 1;">
                                    <label>Reservation Fee (₱)</label>
                                    <input type="number" name="reservation_fee" class="control-pro" placeholder="Optional fixed amount" min="0">
                                </div>
                            </div>
                        </div>
                        <div class="form-row-pro">
                            <div class="form-group-pro" style="flex: 1;">
                                <label>Package Availability</label>
                                <select name="status" class="control-pro">
                                    <option value="active">Available (Published)</option>
                                    <option value="seasonal">Seasonal</option>
                                    <option value="inactive">Unavailable (Hidden)</option>
                                    <option value="draft">Draft</option>
                                </select>
                            </div>
                        </div>
        """
        if cover_photo_group:
            cover_photo_group.insert_before(BeautifulSoup(pricing_html, "html.parser"))
            
        # Delete old pricing and booking tabs
        pricing_tab.extract()
        booking_tab.extract()
        
    # 2. Add tab-components
    components_html = """
                    <!-- STEP 2: COMPONENTS -->
                    <div id="tab-components" class="tab-pane-pro">
                        <h4 style="font-size: 1.2rem; font-weight: 800; color: #1e293b; margin-bottom: 0.5rem;">Package Components</h4>
                        <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 1.5rem;">Enable the components that are included in this package.</p>
                        
                        <div style="display: flex; flex-direction: column; gap: 1rem;">
                            <!-- Food Toggle -->
                            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 0.75rem; padding: 1.25rem; display: flex; align-items: center; justify-content: space-between;">
                                <div style="display: flex; align-items: center; gap: 1rem;">
                                    <div style="width: 48px; height: 48px; background: #f0fdf4; color: #22c55e; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.25rem;">
                                        <i class="fas fa-utensils"></i>
                                    </div>
                                    <div>
                                        <h5 style="margin: 0; font-size: 1rem; font-weight: 800;">Include Food Menu</h5>
                                        <div style="font-size: 0.8rem; color: #64748b;">Allow customers to select dishes or set a fixed menu.</div>
                                    </div>
                                </div>
                                <label class="occ-switch">
                                    <input type="checkbox" id="toggle-food" onchange="window.togglePackageComponent('food', this.checked)">
                                    <span class="slider round"></span>
                                </label>
                            </div>

                            <!-- Services Toggle -->
                            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 0.75rem; padding: 1.25rem; display: flex; align-items: center; justify-content: space-between;">
                                <div style="display: flex; align-items: center; gap: 1rem;">
                                    <div style="width: 48px; height: 48px; background: #eff6ff; color: #3b82f6; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.25rem;">
                                        <i class="fas fa-concierge-bell"></i>
                                    </div>
                                    <div>
                                        <h5 style="margin: 0; font-size: 1rem; font-weight: 800;">Include Services</h5>
                                        <div style="font-size: 0.8rem; color: #64748b;">Waiters, buffet setup, coordinators, etc.</div>
                                    </div>
                                </div>
                                <label class="occ-switch">
                                    <input type="checkbox" id="toggle-services" onchange="window.togglePackageComponent('services', this.checked)">
                                    <span class="slider round"></span>
                                </label>
                            </div>

                            <!-- Equipment Toggle -->
                            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 0.75rem; padding: 1.25rem; display: flex; align-items: center; justify-content: space-between;">
                                <div style="display: flex; align-items: center; gap: 1rem;">
                                    <div style="width: 48px; height: 48px; background: #fef2f2; color: #ef4444; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.25rem;">
                                        <i class="fas fa-chair"></i>
                                    </div>
                                    <div>
                                        <h5 style="margin: 0; font-size: 1rem; font-weight: 800;">Include Equipment</h5>
                                        <div style="font-size: 0.8rem; color: #64748b;">Tables, chairs, tents, chafing dishes, etc.</div>
                                    </div>
                                </div>
                                <label class="occ-switch">
                                    <input type="checkbox" id="toggle-equipment" onchange="window.togglePackageComponent('equipment', this.checked)">
                                    <span class="slider round"></span>
                                </label>
                            </div>
                        </div>
                    </div>
    """
    
    # 3. Rename tab-menu to tab-food, add selection mode
    food_tab = tabs.get("tab-menu")
    if food_tab:
        food_tab["id"] = "tab-food"
        food_tab_mode_html = """
                        <div style="background: white; border: 1px solid #e2e8f0; border-radius: var(--border-radius); padding: 1rem; margin-bottom: 1.5rem; display: flex; gap: 1.5rem;">
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; margin: 0;">
                                <input type="radio" name="food_selection_mode" value="customer" checked onchange="window.toggleFoodMode(this.value)">
                                <span style="font-weight: 700; color: #1e293b;">Customer Selection (Pool)</span>
                            </label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; margin: 0;">
                                <input type="radio" name="food_selection_mode" value="fixed" onchange="window.toggleFoodMode(this.value)">
                                <span style="font-weight: 700; color: #1e293b;">Fixed Menu</span>
                            </label>
                        </div>
        """
        food_tab.insert(0, BeautifulSoup(food_tab_mode_html, "html.parser"))
        
    # 4. Split tab-inclusions into tab-services and tab-equipment
    inclusions_tab = tabs.get("tab-inclusions")
    if inclusions_tab:
        services_html = """
                    <!-- STEP 4: SERVICES -->
                    <div id="tab-services" class="tab-pane-pro">
                        <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 1.5rem;">Select the services included in this package.</p>
                        <div style="margin-bottom: 1.5rem;">
                            <label style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem; margin-bottom: 1rem;">
                                <span style="font-size: 1rem; color: #1e293b;"><i class="fas fa-concierge-bell text-brand" style="margin-right: 8px;"></i> Included Services</span>
                                <div style="position:relative; width:160px;">
                                    <i class="fas fa-search" style="position:absolute; left:var(--space-sm); top:50%; transform:translateY(-50%); font-size:10px; color:var(--color-neutral-400);"></i>
                                    <input type="text" id="pkgServicesSearch" placeholder="Quick search..." onkeyup="window.filterServices()" class="control-pro" style="height:32px; padding-left:2rem; font-size:11px;">
                                </div>
                            </label>
                            <div class="menu-grid-scroll inclusions-grid" id="inc-services-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 1rem;">
                                <!-- Populated via JS -->
                            </div>
                        </div>
                    </div>
        """
        equipment_html = """
                    <!-- STEP 5: EQUIPMENT -->
                    <div id="tab-equipment" class="tab-pane-pro">
                        <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 1.5rem;">Select the equipment included in this package.</p>
                        <div style="margin-bottom: 1.5rem;">
                            <label style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem; margin-bottom: 1rem;">
                                <span style="font-size: 1rem; color: #1e293b;"><i class="fas fa-chair text-brand" style="margin-right: 8px;"></i> Included Equipment</span>
                                <div style="position:relative; width:160px;">
                                    <i class="fas fa-search" style="position:absolute; left:var(--space-sm); top:50%; transform:translateY(-50%); font-size:10px; color:var(--color-neutral-400);"></i>
                                    <input type="text" id="pkgEquipmentSearch" placeholder="Quick search..." onkeyup="window.filterEquipment()" class="control-pro" style="height:32px; padding-left:2rem; font-size:11px;">
                                </div>
                            </label>
                            <div class="menu-grid-scroll inclusions-grid" id="inc-equipment-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 1rem;">
                                <!-- Populated via JS -->
                            </div>
                        </div>
                    </div>
        """
        inclusions_tab.insert_after(BeautifulSoup(services_html, "html.parser"))
        inclusions_tab.insert_after(BeautifulSoup(equipment_html, "html.parser"))
        
        basic_tab.insert_after(BeautifulSoup(components_html, "html.parser"))
        inclusions_tab.extract() # Remove old inclusions tab

with open(r"c:\OccaServe\OccaShare\scratch\packages_modified.html", "w", encoding="utf-8") as f:
    f.write(str(soup))
