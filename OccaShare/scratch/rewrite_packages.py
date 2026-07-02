import re

def rewrite_packages_html():
    html_path = r"c:\OccaServe\OccaShare\templates\caterer\packages.html"
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_modal = """<!-- Create/Edit Package Form Modal -->
<div id="packageModal" class="occ-modal-overlay">
    <div class="occ-modal-box sz-lg occ-content-pop" style="max-width: 900px;">
        <div class="occ-modal-header glass-header">
            <div>
                <h3 id="packageModalTitle" class="occ-modal-title" style="color: white;">Create New Package</h3>
                <div class="occ-modal-subtitle" style="color: rgba(255, 255, 255, 0.85);">Build your package offerings exactly how you sell them.</div>
            </div>
            <button type="button" onclick="window.closePackageModal()" class="occ-modal-close" style="color: white; opacity: 0.8;"><i class="fas fa-times"></i></button>
        </div>
        
        <form id="packageForm" method="POST" enctype="multipart/form-data" style="display: flex; flex-direction: column; flex: 1; min-height: 0;">
            <div class="occ-modal-body" style="padding: 0; display: flex; flex-direction: row; flex: 1; overflow: hidden; min-height: 0;">
                <!-- Left Sidebar Stepper -->
                <div class="pkg-wizard-sidebar">
                    <div id="step-btn-basic" class="pkg-step-side active" onclick="window.switchPackageTab(this, 'basic')">
                        <div class="step-icon-side"><i class="fas fa-info-circle"></i></div>
                        <div class="step-text-side">
                            <span class="step-title-side">1. Basic Info</span>
                        </div>
                    </div>
                    <div id="step-btn-inclusions" class="pkg-step-side" onclick="window.switchPackageTab(this, 'inclusions')">
                        <div class="step-icon-side"><i class="fas fa-box-open"></i></div>
                        <div class="step-text-side">
                            <span class="step-title-side">2. Inclusions</span>
                        </div>
                    </div>
                    <div id="step-btn-menu" class="pkg-step-side" onclick="window.switchPackageTab(this, 'menu')">
                        <div class="step-icon-side"><i class="fas fa-utensils"></i></div>
                        <div class="step-text-side">
                            <span class="step-title-side">3. Menu Selection</span>
                        </div>
                    </div>
                    <div id="step-btn-addons" class="pkg-step-side" onclick="window.switchPackageTab(this, 'addons')">
                        <div class="step-icon-side"><i class="fas fa-plus-circle"></i></div>
                        <div class="step-text-side">
                            <span class="step-title-side">4. Optional Add-ons</span>
                        </div>
                    </div>
                    <div id="step-btn-pricing" class="pkg-step-side" onclick="window.switchPackageTab(this, 'pricing')">
                        <div class="step-icon-side"><i class="fas fa-tag"></i></div>
                        <div class="step-text-side">
                            <span class="step-title-side">5. Pricing</span>
                        </div>
                    </div>
                    <div id="step-btn-booking" class="pkg-step-side" onclick="window.switchPackageTab(this, 'booking')">
                        <div class="step-icon-side"><i class="fas fa-calendar-alt"></i></div>
                        <div class="step-text-side">
                            <span class="step-title-side">6. Booking Rules</span>
                        </div>
                    </div>
                    <div id="step-btn-review" class="pkg-step-side" onclick="window.switchPackageTab(this, 'review')">
                        <div class="step-icon-side"><i class="fas fa-check-double"></i></div>
                        <div class="step-text-side">
                            <span class="step-title-side">7. Review & Publish</span>
                        </div>
                    </div>
                 
                    <div class="sidebar-progress-wrapper" style="margin-top: auto; padding-top: 1rem;">
                         <div style="font-size: 10px; font-weight: 800; color: #94a3b8; margin-bottom: 8px; text-transform: uppercase;">Completion</div>
                         <div style="width: 100%; height: 6px; background: #e2e8f0; border-radius: var(--border-radius, 4px); overflow: hidden;">
                             <div id="pkgWizardProgress" style="width: 14%; height: 100%; background: var(--primary-color); transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);"></div>
                         </div>
                    </div>
                </div>

                <!-- Right Content Area -->
                <div class="pkg-wizard-content">
                    
                    <!-- STEP 1: BASIC INFO -->
                    <div id="tab-basic" class="tab-pane-pro active">
                        <div class="form-group-pro">
                            <label>Package Name *</label>
                            <input type="text" name="name" class="control-pro" placeholder="e.g. Wedding Gold Package" required>
                        </div>
                        
                        <div class="form-row-pro">
                            <div class="form-group-pro" style="flex: 1;">
                                <label>Category *</label>
                                <select name="service_type" class="control-pro" required>
                                    <option value="Wedding">Wedding</option>
                                    <option value="Birthday">Birthday</option>
                                    <option value="Debut">Debut</option>
                                    <option value="Christening">Christening</option>
                                    <option value="Corporate">Corporate</option>
                                    <option value="Funeral">Funeral</option>
                                    <option value="Anniversary">Anniversary</option>
                                    <option value="Kiddie Party">Kiddie Party</option>
                                    <option value="Fiesta">Fiesta</option>
                                    <option value="General">Others</option>
                                </select>
                            </div>
                            <div class="form-group-pro" style="flex: 1;">
                                <label>Package Type *</label>
                                <select name="pricing_mode" class="control-pro" onchange="window.togglePricingMode(this.value)" required>
                                    <option value="per_pax">Per Pax (Guest Based)</option>
                                    <option value="fixed">Fixed Package (Event Based)</option>
                                </select>
                            </div>
                        </div>

                        <div class="form-row-pro" id="capacityRow">
                            <div class="form-group-pro capacity-per-pax" style="flex: 1;">
                                <label>Minimum Guests *</label>
                                <input type="number" name="min_guests" class="control-pro" min="1" value="50">
                            </div>
                            <div class="form-group-pro capacity-per-pax" style="flex: 1;">
                                <label>Maximum Guests (Optional)</label>
                                <input type="number" name="max_guests" class="control-pro" placeholder="No Limit">
                            </div>
                            
                            <div class="form-group-pro capacity-fixed" style="display: none; flex: 1;">
                                <label>Good For (Optional)</label>
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <input type="number" name="base_pax" class="control-pro" placeholder="e.g. 50">
                                    <span style="font-size: 13px; font-weight: 700; color: #64748b;">Guests</span>
                                </div>
                            </div>
                        </div>

                        <div class="form-group-pro">
                            <label>Short Description (Optional)</label>
                            <textarea name="description" class="control-pro" rows="2" placeholder="Perfect for intimate weddings with buffet setup and professional service."></textarea>
                        </div>

                        <div class="form-group-pro">
                            <label>Cover Photo</label>
                            <div style="display: flex; gap: 1.5rem; align-items: flex-start;">
                                <div class="photo-upload-zone" onclick="document.getElementById('pkgImageInput').click()" style="width: 120px; height: 120px; border: 2px dashed #e2e8f0; border-radius: var(--border-radius); display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; background: #f8fafc; transition: all 0.2s;">
                                    <i class="fas fa-camera" style="font-size: 1.5rem; color: #94a3b8; margin-bottom: 0.5rem;"></i>
                                    <span style="font-size: 10px; font-weight: 800; color: #94a3b8; text-transform: uppercase;">Upload</span>
                                    <input type="file" name="image" id="pkgImageInput" accept="image/*" style="display: none;" onchange="window.previewPackageImage(this)">
                                </div>
                                <div id="pkgImagePreviewContainer" style="flex: 1; height: 120px; border-radius: var(--border-radius); overflow: hidden; background: #f1f5f9; display: flex; align-items: center; justify-content: center; border: 1px solid #e2e8f0;">
                                    <img id="pkgImagePreview" src="" style="width: 100%; height: 100%; object-fit: cover; display: none;">
                                    <div id="previewPlaceholder" style="color: #cbd5e1; display: flex; flex-direction: column; align-items: center;">
                                        <i class="fas fa-image" style="font-size: 2rem; margin-bottom: 0.5rem;"></i>
                                        <span style="font-size: 11px; font-weight: 700;">No photo selected</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- STEP 2: INCLUSIONS -->
                    <div id="tab-inclusions" class="tab-pane-pro">
                        <div class="form-group-pro">
                            <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 1.5rem; line-height: 1.5;">Select everything included in the package except food. These items are pulled from your <strong>Equipment & Services</strong> catalog.</p>
                            
                            <!-- Services -->
                            <div style="margin-bottom: 1.5rem;">
                                <label style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem; margin-bottom: 1rem;">
                                    <span style="font-size: 1rem; color: #1e293b;"><i class="fas fa-concierge-bell text-brand" style="margin-right: 8px;"></i> Included Services</span>
                                </label>
                                <div class="menu-grid-scroll inclusions-grid" id="inc-services-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 1rem;">
                                    <!-- Populated via JS -->
                                </div>
                            </div>

                            <!-- Equipment -->
                            <div style="margin-bottom: 1.5rem;">
                                <label style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem; margin-bottom: 1rem;">
                                    <span style="font-size: 1rem; color: #1e293b;"><i class="fas fa-chair text-brand" style="margin-right: 8px;"></i> Included Equipment</span>
                                </label>
                                <div class="menu-grid-scroll inclusions-grid" id="inc-equipment-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 1rem;">
                                    <!-- Populated via JS -->
                                </div>
                            </div>
                            
                            <!-- Styling & Freebies can also be populated if you categorize them as such in your library -->
                        </div>
                    </div>

                    <!-- STEP 3: MENU SELECTION -->
                    <div id="tab-menu" class="tab-pane-pro">
                        <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 1.5rem; line-height: 1.5;">Select the food items available for this package. Set limits if you want customers to choose (e.g. choose 2 from 5 available main courses).</p>
                        
                        <div style="background:var(--color-neutral-50); border:1px solid var(--color-neutral-200); border-radius:var(--border-radius); padding:var(--space-md);">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:var(--space-md);">
                                <label style="margin:0;">Menu Options</label>
                                <div style="display: flex; gap: 0.5rem; align-items: center;">
                                    <label class="btn-secondary-pro" style="display:flex; align-items:center; gap:0.5rem; cursor:pointer; padding: 0.3rem 0.6rem; font-size: 0.7rem; margin:0;">
                                        <input type="checkbox" onchange="window.toggleAllInContainer(this, '#pkgMenuLibraryContainer')" style="margin:0; width: 14px; height: 14px; cursor: pointer;"> Select All
                                    </label>
                                    <div style="position:relative; width:160px; margin-left: 0.5rem;">
                                        <i class="fas fa-search" style="position:absolute; left:var(--space-sm); top:50%; transform:translateY(-50%); font-size:10px; color:var(--color-neutral-400);"></i>
                                        <input type="text" id="pkgMenuLibrarySearch" placeholder="Quick search..." onkeyup="filterPkgMenuLibrary()" class="control-pro" style="height:32px; padding-left:2rem; font-size:11px;">
                                    </div>
                                </div>
                            </div>
                            <div id="pkgMenuLibraryContainer" class="menu-grid-scroll">
                            </div>
                        </div>

                        <div style="margin-top: 1rem; background:#f8fafc; border:1px solid var(--primary-color); border-radius:var(--border-radius); padding:1.5rem; position: relative; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.02);">
                            <div style="position: absolute; top: 0; left: 0; width: 4px; height: 100%; background: var(--primary-color);"></div>
                            <label style="color: var(--primary-color); margin-bottom: 0.5rem; display: block; font-size: 1.1rem; font-weight: 800;"><i class="fas fa-list-ol" style="margin-right: 8px;"></i> Customer Selection Rules</label>
                            <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 1.25rem; font-weight: 500;">Set how many items a customer can choose per category. (e.g. Choose 2 Main Courses). If you don't enter a limit, the customer gets all selected items in that category.</p>
                            
                            <div id="selectionRulesContainer" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;">
                                <!-- Rules will be built dynamically here via JS -->
                            </div>
                            <input type="hidden" name="selection_rules" id="selectionRulesHidden">
                        </div>
                    </div>
                    
                    <!-- STEP 4: OPTIONAL ADD-ONS -->
                    <div id="tab-addons" class="tab-pane-pro">
                        <div class="form-group-pro">
                            <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 1rem;">Offer optional upgrades that are NOT included in the base package (e.g. Lechon, Chocolate Fountain, Photo Booth).</p>
                            <div style="background:var(--color-neutral-50); border-radius:var(--border-radius); padding:var(--space-md); border:1px solid var(--color-neutral-200); margin-bottom:var(--space-md); max-height:350px; overflow-y:auto;">
                                <div class="menu-grid-scroll" id="addonsGrid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 1rem;">
                                    <!-- Will be populated dynamically by JS -->
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- STEP 5: PRICING -->
                    <div id="tab-pricing" class="tab-pane-pro">
                        <div class="pricing-overview-card" style="background: #fff; border: 1px solid #e2e8f0; padding: 2rem; border-radius: var(--border-radius); margin-bottom: 1.5rem; text-align: center;">
                            <h4 style="font-size: 1.2rem; font-weight: 800; color: #1e293b; margin-bottom: 0.5rem;">Selling Price</h4>
                            <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 2rem;">Set the final selling price for this package.</p>
                            
                            <div class="form-row-pro" style="display: flex; justify-content: center;">
                                <div class="form-group-pro" style="max-width: 300px; width: 100%;">
                                    <label id="lblPricingMain" style="font-size: 11px; text-transform: uppercase;">Price Per Guest (₱) *</label>
                                    <input type="text" name="price_per_head" id="pkgManualPriceInput" class="control-pro js-format-comma" style="height: 60px; font-size: 1.5rem; font-weight: 900; text-align: center; color: var(--primary-color);" placeholder="0.00" required maxlength="10">
                                </div>
                            </div>
                            
                            <div id="estStartingPriceContainer" style="margin-top: 1.5rem; padding: 1rem; background: #f8fafc; border-radius: 8px; border: 1px dashed #cbd5e1;">
                                <span style="font-size: 0.85rem; color: #64748b; font-weight: 600;">Estimated Starting Price</span>
                                <div id="estStartingPriceValue" style="font-size: 1.25rem; font-weight: 800; color: #1e293b; margin-top: 0.25rem;">₱0.00</div>
                                <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;" id="estStartingPriceCalc">(Based on Minimum Guests)</div>
                            </div>
                            
                            <!-- No hidden cost inputs needed -->
                        </div>
                    </div>

                    <!-- STEP 6: BOOKING RULES -->
                    <div id="tab-booking" class="tab-pane-pro">
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
                            <div class="form-group-pro" style="flex: 1;">
                                <label>Booking Lead Time (Days) *</label>
                                <input type="number" name="booking_lead_time" class="control-pro" min="1" value="7" required>
                                <small style="display:block; font-size:10px; color:#64748b; margin-top:4px;">Must book at least X days before the event.</small>
                            </div>
                        </div>
                        
                        <div class="form-group-pro">
                            <label>Cancellation Policy (Optional)</label>
                            <textarea name="policies_cancellation" id="pkgCancellationPolicy" class="control-pro" rows="2" placeholder="e.g. 50% refund if cancelled 2 weeks prior..."></textarea>
                        </div>
                        
                        <div class="form-group-pro">
                            <label>Internal Notes (Visible only to you)</label>
                            <textarea name="policies_internal" id="pkgInternalNotes" class="control-pro" rows="2" placeholder="Notes about vendor coordination..."></textarea>
                        </div>
                    </div>

                    <!-- STEP 7: REVIEW & PUBLISH -->
                    <div id="tab-review" class="tab-pane-pro">
                        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: var(--border-radius); padding: 1.5rem;">
                            <h4 style="font-size: 1.1rem; font-weight: 800; color: #1e293b; margin-bottom: 1rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem;"><i class="fas fa-clipboard-check text-green-500 mr-2"></i> Package Summary</h4>
                            
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
                                <div>
                                    <h5 style="font-size: 0.7rem; font-weight: 800; color: #64748b; text-transform: uppercase; margin-bottom: 0.5rem;">Identity</h5>
                                    <p style="font-size: 0.85rem; margin: 0 0 0.25rem;"><strong>Name:</strong> <span id="reviewName"></span></p>
                                    <p style="font-size: 0.85rem; margin: 0 0 0.25rem;"><strong>Category:</strong> <span id="reviewType"></span></p>
                                    <p style="font-size: 0.85rem; margin: 0 0 0.25rem;"><strong>Type:</strong> <span id="reviewPricingMode"></span></p>
                                    <p style="font-size: 0.85rem; margin: 0 0 0.25rem;"><strong>Capacity:</strong> <span id="reviewCapacity"></span></p>
                                </div>
                                <div>
                                    <h5 style="font-size: 0.7rem; font-weight: 800; color: #64748b; text-transform: uppercase; margin-bottom: 0.5rem;">Pricing</h5>
                                    <p style="font-size: 1rem; margin: 0 0 0.25rem; font-weight: 900; color: var(--primary-color);"><span id="reviewPrice"></span></p>
                                </div>
                            </div>

                            <div style="margin-top: 1.5rem;">
                                <h5 style="font-size: 0.7rem; font-weight: 800; color: #64748b; text-transform: uppercase; margin-bottom: 0.5rem;">Inclusions Summary</h5>
                                <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                                    <div style="flex: 1; min-width: 100px; background: white; border: 1px solid #e2e8f0; border-radius: var(--border-radius, 0.5rem); padding: 0.75rem; text-align: center;">
                                        <div style="font-size: 1.5rem; font-weight: 900; color: #1e293b;" id="reviewDishesCount">0</div>
                                        <div style="font-size: 0.7rem; font-weight: 800; color: #94a3b8; text-transform: uppercase;">Menu Items</div>
                                    </div>
                                    <div style="flex: 1; min-width: 100px; background: white; border: 1px solid #e2e8f0; border-radius: var(--border-radius, 0.5rem); padding: 0.75rem; text-align: center;">
                                        <div style="font-size: 1.5rem; font-weight: 900; color: #1e293b;" id="reviewServicesCount">0</div>
                                        <div style="font-size: 0.7rem; font-weight: 800; color: #94a3b8; text-transform: uppercase;">Equip / Svcs</div>
                                    </div>
                                    <div style="flex: 1; min-width: 100px; background: white; border: 1px solid #e2e8f0; border-radius: var(--border-radius, 0.5rem); padding: 0.75rem; text-align: center;">
                                        <div style="font-size: 1.5rem; font-weight: 900; color: #1e293b;" id="reviewAddonsCount">0</div>
                                        <div style="font-size: 0.7rem; font-weight: 800; color: #94a3b8; text-transform: uppercase;">Add-ons</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="occ-modal-footer" id="pkgWizardFooter" style="padding: 1.25rem 2rem; background: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
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
            </div>
        </form>
    </div>
</div>
"""

    # We need to replace everything from `<!-- Create/Edit Package Form Modal -->` 
    # to the `{% endblock %}` (excluding the endblock).
    start_tag = "<!-- Create/Edit Package Form Modal -->"
    end_tag = "{% endblock %}"
    
    start_idx = content.find(start_tag)
    end_idx = content.find(end_tag, start_idx)
    
    if start_idx != -1 and end_idx != -1:
        new_content = content[:start_idx] + new_modal + "\n" + content[end_idx:]
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("HTML successfully replaced.")
    else:
        print("Could not find tags in HTML.")

rewrite_packages_html()
