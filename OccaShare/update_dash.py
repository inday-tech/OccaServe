import re

filepath = r'c:\OccaServe\OccaShare\templates\customer\dashboard.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update text language
replacements = {
    "Here's your intelligence summary and booking activity.": "Here is a quick summary of your recent bookings and account activity.",
    "Explore elite partner registry": "Find and book caterers",
    "Monitor your logistic journey": "View your booking status",
    "Manage your financial nodes": "View payments and receipts",
    "Update your identity profile": "Update your personal details",
    "Investment": "Amount Spent",
    "Next Event Spotlight": "Next Upcoming Event",
    "Track Order": "Track Bookings",
    "Account Settings": "Profile Settings"
}

for old, new in replacements.items():
    content = content.replace(old, new)

# 2. Modify stat cards to remove icons and center text
content = re.sub(
    r'<div class="stat-card">[\s\S]*?<div class="stat-body">([\s\S]*?)</div>\s*</div>',
    r'<div class="stat-card" style="display: block; text-align: center; padding: 2rem 1rem;">\n            \1\n        </div>',
    content
)

# 3. Add Recent Messages Panel under Quick Actions
# Find the end of Quick Actions panel
qa_end = content.find('<!-- Quick Actions Hub -->')
if qa_end != -1:
    qa_panel_end = content.find('</div>\n        </div>', qa_end)
    
    if qa_panel_end != -1:
        messages_panel = '''
        <!-- Recent Messages -->
        <div class="panel" style="margin-top: 1.25rem;">
            <div class="panel-header">
                <h3>Recent Messages</h3>
                <a href="/customer/messages" class="panel-link">View Inbox</a>
            </div>
            {% if recent_messages %}
            <div style="padding: 0;">
                {% for msg in recent_messages %}
                <a href="/customer/messages" style="display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.5rem; border-bottom: 1px solid var(--dm-slate-50); text-decoration: none; transition: background 0.2s;">
                    <div style="display: flex; flex-direction: column; gap: 4px; overflow: hidden;">
                        <b style="font-size: 0.85rem; color: var(--text-dark); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ msg.caterer_name }}</b>
                        <span style="font-size: 0.75rem; color: var(--dm-slate-400); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ msg.last_msg_text }}</span>
                    </div>
                    <span style="font-size: 0.7rem; font-weight: 700; color: var(--dm-slate-300); flex-shrink: 0;">{{ msg.last_msg_time }}</span>
                </a>
                {% endfor %}
            </div>
            {% else %}
            <div class="empty-panel" style="padding: 2rem 1.5rem;">
                <p>No recent messages.</p>
            </div>
            {% endif %}
        </div>'''
        
        # Insert messages panel right after Quick Actions panel
        insert_pos = qa_panel_end + len('</div>\n        </div>')
        content = content[:insert_pos] + messages_panel + content[insert_pos:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
