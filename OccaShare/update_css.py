import re

filepath = r'c:\OccaServe\OccaShare\app\static\css\caterer\notifications.css'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_css = '''/* Caterer Notifications - Premium Redesign v2 */

/* --- Standardized Enterprise Notification Variables & Scope --- */
.notif-page {
    --text-xs: 0.75rem;    
    --text-sm: 0.875rem;    
    --text-base: 1rem;     
    --text-lg: 1.25rem;    
    --text-xl: 1.5rem;     
    --text-2xl: 1.875rem;
    --primary-color: #ff7b54;
    --primary-color-rgb: 255, 123, 84;
    --secondary-color: #1e293b;
    --text-muted: #64748b;
    
    padding: 1.25rem 2.5rem !important;
    width: 100% !important;
    box-sizing: border-box !important;
}

/* Ensure the page header has exact typography for consistency across roles */
.notif-page .page-header h1 {
    font-size: 1.65rem !important;
    font-weight: 800 !important;
    color: #0f172a !important;
    margin: 0 0 0.1rem 0 !important;
    letter-spacing: -0.02em !important;
    font-family: 'Poppins', sans-serif !important;
}

.notif-page .page-header p {
    font-size: 0.85rem !important;
    color: #64748b !important;
    margin: 0 !important;
    font-family: 'Poppins', sans-serif !important;
}

'''

content = content.replace('/* Caterer Notifications - Premium Redesign v2 */', new_css)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated notifications.css')
