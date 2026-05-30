import re

filepath = r'c:\OccaServe\OccaShare\app\static\js\main.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Let's replace the broken fetchGlobalNotifications function with a working one
correct_func = '''window.fetchGlobalNotifications = async function(isForced = false) {
    try {
        const response = await fetch('/api/notifications?limit=20');
        if (!response.ok) return;
        const data = await response.json();

        // 1. Update UI Badges
        const badge = document.getElementById('nav-notif-badge');
        const dropBadge = document.getElementById('dropdown-notif-badge');
        if (badge) {
            badge.style.display = data.unread_count > 0 ? 'flex' : 'none';
            badge.textContent = data.unread_count > 99 ? '99+' : data.unread_count;
        }
        if (dropBadge) {
            dropBadge.style.display = data.unread_count > 0 ? 'inline-block' : 'none';
            dropBadge.textContent = data.unread_count > 99 ? '99+ NEW' : data.unread_count + ' NEW';
        }

        // 2. Render Dropdown Container
        const container = document.getElementById('headerNotifContainer');
        if (!container) return;

        if (data.notifications.length === 0) {
            container.innerHTML = <div style="text-align: center; padding: 2.5rem 1rem;"><div style="background: #f1f5f9; width: 56px; height: 56px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 12px;"><i class="fas fa-check-double" style="color: #94a3b8; font-size: 1.5rem;"></i></div><p style="margin: 0; font-size: 0.9rem; font-weight: 600; color: #1e293b;">You're all caught up!</p><p style="margin: 4px 0 0; font-size: 0.75rem; color: #64748b;">No new notifications</p></div>;
        } else {
            let htmlString = '';
            const topNotifs = data.notifications.slice(0, 5);
            topNotifs.forEach(notif => {
                const iconMap = {
                    'Booking': { i: 'fa-calendar-check', c: '#10b981', bg: '#d1fae5' },
                    'Payment': { i: 'fa-wallet', c: '#0ea5e9', bg: '#e0f2fe' },
                    'Review': { i: 'fa-star', c: '#f59e0b', bg: '#fef3c7' },
                    'Verification': { i: 'fa-shield-check', c: '#8b5cf6', bg: '#ede9fe' },
                    'Customer': { i: 'fa-user-plus', c: '#ec4899', bg: '#fce7f3' }
                };
                const info = iconMap[notif.type] || { i: 'fa-bell', c: '#64748b', bg: '#f1f5f9' };
                const isUnread = !notif.is_read;
                const timeStr = new Date(notif.created_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
                htmlString += <a href="javascript:void(0)" onclick="handleGlobalNotifClick(, '', )" style="display: flex; gap: 12px; padding: 16px; text-decoration: none; border-bottom: 1px solid #e2e8f0; background: ; transition: all 0.2s; align-items: flex-start; position: relative;"><div style="background: ; color: ; width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 1rem; box-shadow: ;"><i class="fas "></i></div><div style="flex: 1; overflow: hidden; padding-top: 2px;"><p style="margin: 0 0 4px 0; font-size: 0.85rem; color: #0f172a; font-weight: ; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;"></p><p style="margin: 0; font-size: 0.7rem; color: #64748b; font-weight: 600;"><i class="far fa-clock" style="margin-right: 4px;"></i></p></div></a>;
            });
            container.innerHTML = htmlString;
        }

        // 3. Broadcast to Notifications Page if it exists
        if (window.syncLocalNotificationsPage) {
            window.syncLocalNotificationsPage(data.notifications, data.unread_count);
        }
    } catch (err) {
        console.error("Global Notif Error:", err);
    }
}

window.handleGlobalNotifClick = async function(id, link, isUnread) {
    if (isUnread) {
        try {
            await fetch(/api/notifications//read, { method: 'POST' });
            window.fetchGlobalNotifications(true);
        } catch(e) {}
    }
    if (link) window.location.href = link;
}
'''

# Use regex to replace from window.fetchGlobalNotifications to the end of handleGlobalNotifClick
content = re.sub(
    r'window\.fetchGlobalNotifications\s*=\s*async\s*function.*?if\s*\(link\)\s*window\.location\.href\s*=\s*link;\s*\}',
    correct_func,
    content,
    flags=re.DOTALL
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed main.js fetchGlobalNotifications!')
