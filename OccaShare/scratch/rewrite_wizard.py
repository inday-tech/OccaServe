import re
import os

html_path = r"c:\OccaServe\OccaShare\templates\caterer\packages.html"
js_path = r"c:\OccaServe\OccaShare\app\static\js\caterer\packages.js"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# 1. Update Sidebar Navigation
sidebar_replacement = """                <div class="pkg-wizard-sidebar">
                    <div id="step-btn-basic" class="pkg-step-side active" onclick="window.switchPackageTab(this, 'basic')">
                        <div class="step-icon-side"><i class="fas fa-info-circle"></i></div>
                        <div class="step-text-side">
                            <span class="step-title-side">1. Basic Info & Pricing</span>
                        </div>
                    </div>
                    <div id="step-btn-components" class="pkg-step-side" onclick="window.switchPackageTab(this, 'components')">
                        <div class="step-icon-side"><i class="fas fa-cubes"></i></div>
                        <div class="step-text-side">
                            <span class="step-title-side">2. Components</span>
                        </div>
                    </div>
                    <div id="step-btn-food" class="pkg-step-side" onclick="window.switchPackageTab(this, 'food')" style="display: none;">
                        <div class="step-icon-side"><i class="fas fa-utensils"></i></div>
                        <div class="step-text-side">
                            <span class="step-title-side">3. Food Selection</span>
                        </div>
                    </div>
                    <div id="step-btn-services" class="pkg-step-side" onclick="window.switchPackageTab(this, 'services')" style="display: none;">
                        <div class="step-icon-side"><i class="fas fa-concierge-bell"></i></div>
                        <div class="step-text-side">
                            <span class="step-title-side">4. Services</span>
                        </div>
                    </div>
                    <div id="step-btn-equipment" class="pkg-step-side" onclick="window.switchPackageTab(this, 'equipment')" style="display: none;">
                        <div class="step-icon-side"><i class="fas fa-chair"></i></div>
                        <div class="step-text-side">
                            <span class="step-title-side">5. Equipment</span>
                        </div>
                    </div>
                    <div id="step-btn-addons" class="pkg-step-side" onclick="window.switchPackageTab(this, 'addons')">
                        <div class="step-icon-side"><i class="fas fa-plus-circle"></i></div>
                        <div class="step-text-side">
                            <span class="step-title-side">6. Optional Add-ons</span>
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
                </div>"""

# Replace sidebar
html = re.sub(r'<div class="pkg-wizard-sidebar">.*?</div>\s*</div>\s*</div>', sidebar_replacement, html, flags=re.DOTALL)


with open(r"c:\OccaServe\OccaShare\scratch\test_rewrite.html", "w", encoding="utf-8") as f:
    f.write(html)
