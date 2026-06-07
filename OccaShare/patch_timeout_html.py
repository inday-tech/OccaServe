import os

# 1. Update HTML files
html_targets = [
    'templates/admin/layout.html',
    'templates/customer/layout.html'
]

modal_html = """
    <!-- Inactivity Auto-Logout Modal -->
    <div id="inactivityModal" class="occ-modal-overlay" style="display:none; z-index: 99999;">
        <div class="occ-modal-box sz-sm" style="max-width: 400px; text-align: center; border-radius: 20px;">
            <div class="occ-modal-body" style="padding: 3rem 2rem;">
                <div style="width: 80px; height: 80px; background: #fffbeb; color: #f59e0b; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 2.5rem; margin: 0 auto 1.5rem; box-shadow: 0 10px 20px rgba(245, 158, 11, 0.1);">
                    <i class="fas fa-hourglass-half fa-spin-pulse" style="--fa-animation-duration: 2s;"></i>
                </div>
                <h3 style="font-weight: 900; color: #0f172a; margin-bottom: 0.5rem; letter-spacing: -0.02em; font-size: 1.5rem;">Session Security</h3>
                <p style="font-size: 0.95rem; color: #64748b; margin-bottom: 2rem; line-height: 1.6;">You've been inactive for a while. You'll be logged out in <strong style="color: #ef4444;"><span id="inactivityCountdown">60</span> seconds</strong> to protect your account.</p>
                <button id="stayLoggedInBtn" class="btn-primary" style="width: 100%; height: 50px; border-radius: 12px; font-size: 1rem;">Keep Me Logged In</button>
            </div>
        </div>
    </div>
"""

for path in html_targets:
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace old text with dynamic text
        content = content.replace(
            "You've been inactive for a while. You'll be logged out in 60 seconds.",
            "You've been inactive for a while. You'll be logged out in <strong style=\"color: #ef4444;\"><span id=\"inactivityCountdown\">60</span> seconds</strong> to protect your account."
        )
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

# Add modal to caterer
cat_path = 'templates/caterer/layout.html'
if os.path.exists(cat_path):
    with open(cat_path, 'r', encoding='utf-8') as f:
        c_content = f.read()
    if 'id="inactivityModal"' not in c_content:
        c_content = c_content.replace('</body>', modal_html + '\n</body>')
        with open(cat_path, 'w', encoding='utf-8') as f:
            f.write(c_content)

print("HTML files updated!")
