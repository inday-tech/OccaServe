import re

file_path = r"c:\OccaServe\OccaShare\templates\caterer\packages.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# The modals should only exist ONCE, inside the `content` block, right before `{% endblock %}`
# So let's extract the modal HTML
modal_html = """<!-- Addon Picker Modal -->
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
</div>"""

# Remove all occurrences of the modal HTML
while "<!-- Addon Picker Modal -->" in content:
    start_idx = content.find("<!-- Addon Picker Modal -->")
    end_idx = content.find("</div>\n</div>", start_idx) + 13 # rough end of addonConfigModal
    # Actually, it's safer to just split by the exact modal string
    pass

# A safer way to clean the file:
# I know the structure should be:
# ... form ...
# modal_html
# {% endblock %}
# {% block extra_js %}
# <script ... v=28.0></script> ...
# {% endblock %}

# Let's just remove ALL modals first.
content = content.replace(modal_html, "")
# now replace any `{% endblock %}\n{% endblock %}` that might have resulted
content = content.replace("{% endblock %}\n\n{% endblock %}", "{% endblock %}")
content = content.replace("{% endblock %}\n{% endblock %}", "{% endblock %}")

# Now insert it back right before `{% block extra_js %}`
parts = content.split("{% block extra_js %}")
if len(parts) == 2:
    # Ensure there's only one {% endblock %} before {% block extra_js %}
    part0 = parts[0].strip()
    if part0.endswith("{% endblock %}"):
        part0 = part0[:-14].strip() # remove the {% endblock %} temporarily
        
    part0 = part0 + "\n\n" + modal_html + "\n\n{% endblock %}\n\n"
    
    content = part0 + "{% block extra_js %}" + parts[1]
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Fixed duplicates in packages.html")
else:
    print("Error splitting packages.html")
