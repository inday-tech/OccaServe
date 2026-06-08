import os
import re

modal_html = """
    <!-- Custom Universal Logout Modal -->
    <style>
        .univ-modal-overlay {
            position: fixed; inset: 0; background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(4px); z-index: 99999;
            display: none; align-items: center; justify-content: center; padding: 1rem;
        }
        .univ-modal-overlay.active { display: flex; animation: fadeIn 0.2s ease-out; }
        .univ-modal-card {
            background: #fff; width: 100%; max-width: 450px; border-radius: 1.5rem;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25); overflow: hidden;
            display: flex; flex-direction: column; text-align: center;
        }
    </style>
    <div id="univLogoutModal" class="univ-modal-overlay">
        <div class="univ-modal-card">
            <div style="padding: 3rem 2rem;">
                <div id="univLogoutIconBox" style="width: 80px; height: 80px; background: #fff7ed; color: #f97316; border-radius: 24px; display: flex; align-items: center; justify-content: center; font-size: 2.5rem; margin: 0 auto 1.5rem; box-shadow: 0 10px 15px -3px rgba(249, 115, 22, 0.2);">
                    <i class="fas fa-exclamation-triangle"></i>
                </div>
                <h3 style="font-size: 1.25rem; font-weight: 800; color: #0f172a; margin-bottom: 0.75rem;">Log Out?</h3>
                <p style="font-size: 0.9rem; color: #64748b; font-weight: 500; line-height: 1.6; margin-bottom: 2rem;">Are you sure you want to securely end your session?</p>
                <div style="display: flex; gap: 12px; justify-content: center;">
                    <button type="button" style="background: white; border: 1px solid #e2e8f0; color: #0f172a; font-weight: 700; flex: 1; padding: 0.75rem; border-radius: 12px; cursor: pointer; font-size: 0.9rem;" onclick="closeUnivLogoutModal()">No, Abort</button>
                    <button style="background: #f97316; color: white; border: none; font-weight: 800; flex: 1; padding: 0.75rem; border-radius: 12px; cursor: pointer; font-size: 0.9rem;" onclick="window.location.href='/auth/logout'">Yes, Continue</button>
                </div>
            </div>
        </div>
    </div>
    <script>
        function confirmLogout(e) {
            if(e) e.preventDefault();
            document.getElementById('univLogoutModal').classList.add('active');
        }
        function closeUnivLogoutModal() {
            document.getElementById('univLogoutModal').classList.remove('active');
        }
    </script>
"""

# CUSTOMER LAYOUT
cust_path = 'templates/customer/layout.html'
with open(cust_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove old SweetAlert confirmLogout
swal_regex = re.compile(r'<script>\s*function confirmLogout\(e\).*?</script>', re.DOTALL)
content = swal_regex.sub('', content)

# Inject our new modal before closing body
content = content.replace('</body>', f'{modal_html}\n</body>')

with open(cust_path, 'w', encoding='utf-8') as f:
    f.write(content)

# CATERER LAYOUT
cat_path = 'templates/caterer/layout.html'
with open(cat_path, 'r', encoding='utf-8') as f:
    content = f.read()

# For caterer, they might not have confirmLogout defined, but their links point to /auth/logout
# We need to change the links to use onclick="confirmLogout(event)"
content = content.replace('href="/auth/logout"', 'href="/auth/logout" onclick="confirmLogout(event)"')

# Remove any old confirmLogout if it exists
content = swal_regex.sub('', content)

# Inject new modal
content = content.replace('</body>', f'{modal_html}\n</body>')

with open(cat_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
