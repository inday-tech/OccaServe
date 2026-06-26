import re
with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''            window.updateCartUI();
        // ── toggleInventoryModalItem ─────────────────────────────────────────'''

new_code = '''            window.updateCartUI();
        };
        // ── toggleInventoryModalItem ─────────────────────────────────────────'''

content = content.replace(old_code, new_code)

with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed JS syntax error")
