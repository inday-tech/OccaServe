import re

path = 'app/static/js/customer/alacarte_checkout.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add real-time input event listeners
js_addition = """
    // Real-Time Validation Listeners
    const reqFields = ['full_name', 'contact_number', 'delivery_date', 'delivery_time', 'delivery_address'];
    reqFields.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', function() {
                if (this.value.trim() === '') {
                    showError(id, `err-${id}`);
                } else {
                    clearError(id, `err-${id}`);
                }
            });
            el.addEventListener('change', function() {
                if (this.value.trim() === '') {
                    showError(id, `err-${id}`);
                } else {
                    clearError(id, `err-${id}`);
                }
            });
        }
    });
"""

target = """    // --- NAVIGATION LOGIC ---"""
replacement = js_addition + "\n    // --- NAVIGATION LOGIC ---"
content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched alacarte_checkout.js for real-time validation!")
