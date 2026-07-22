import re

f = r'c:\OccaServe\OccaShare\templates\caterer\packages.html'
with open(f, 'r', encoding='utf-8') as file:
    content = file.read()

# Let's completely remove all modals from the string
while '<!-- Addon Picker Modal -->' in content:
    start = content.find('<!-- Addon Picker Modal -->')
    end = content.find('{% endblock %}', start)
    if end != -1:
        # remove from start to end (exclusive)
        content = content[:start] + content[end:]
    else:
        break

# now content has `{% endblock %}` for both content and extra_js, but no modals.
# let's just make sure we don't have duplicated {% endblock %} due to previous broken states
content = content.replace('{% endblock %}\n\n{% endblock %}', '{% endblock %}')
content = content.replace('{% endblock %}\n{% endblock %}', '{% endblock %}')
content = content.replace('{% endblock %}    {% endblock %}', '{% endblock %}')

# Let's count endblocks just to be safe
blocks = content.split('{% endblock %}')
if len(blocks) >= 2:
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
    # blocks[0] is the content block body
    # blocks[1] is the extra_js block (up to its endblock)
    # blocks[2] is whatever is after (empty usually)
    
    final_content = blocks[0] + modal_html + '\n{% endblock %}' + '{% endblock %}'.join(blocks[1:])
    with open(f, 'w', encoding='utf-8') as out:
        out.write(final_content)
    print('Cleaned up HTML properly')
else:
    print('Error: not enough endblocks')
