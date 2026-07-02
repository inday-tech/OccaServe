import re

file_path = r"c:\OccaServe\OccaShare\templates\caterer\packages.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

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

if old_footer in content:
    content = content.replace(old_footer, new_footer)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Footer updated successfully.")
else:
    print("Could not find the old footer.")
