import re

html_path = r'c:\OccaServe\OccaShare\templates\caterer\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """<div class="page-header" style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
    <div>
        <h1>Operations Dashboard</h1>
        <p style="color: #64748b;">Welcome back, {{ user.first_name }}! Here's what needs your attention today.</p>
    </div>
</div>

<!-- SECTION 12: Quick Actions -->
<div class="quick-actions">
    <button class="action-btn" onclick="window.location.href='/caterer/bookings?new=walkin'"><i class="fas fa-plus"></i> Walk-in Booking</button>
    <button class="action-btn" onclick="window.location.href='/caterer/packages'"><i class="fas fa-box-open"></i> Add Package</button>
    <button class="action-btn" onclick="window.location.href='/caterer/profile'"><i class="fas fa-user"></i> Profile Settings</button>
</div>"""

replacement = """<div class="page-header" style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
    <div>
        <h1 style="margin: 0; font-size: 1.8rem; color: #0f172a;">Operations Dashboard</h1>
        <p style="color: #64748b; margin: 5px 0 0 0;">Welcome back, {{ user.first_name }}! Here's what needs your attention today.</p>
    </div>

    <!-- SECTION 12: Quick Actions -->
    <div class="quick-actions" style="grid-column: unset; padding-bottom: 0; margin: 0; align-items: center;">
        <button class="action-btn" onclick="window.location.href='/caterer/bookings?new=walkin'"><i class="fas fa-plus"></i> Walk-in Booking</button>
        <button class="action-btn" onclick="window.location.href='/caterer/packages'"><i class="fas fa-box-open"></i> Add Package</button>
        <button class="action-btn" onclick="window.location.href='/caterer/profile'"><i class="fas fa-user"></i> Profile Settings</button>
    </div>
</div>"""

if target in content:
    content = content.replace(target, replacement)
    with open(html_path, 'w', encoding='utf-8') as out:
        out.write(content)
    print("Replaced successfully!")
else:
    print("Target not found.")
