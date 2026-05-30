import re

filepath = r'c:\OccaServe\OccaShare\app\static\css\caterer\notifications.css'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the block that has padding with one that doesn't
new_block = '''/* --- Standardized Enterprise Notification Variables & Scope --- */
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
}'''

content = re.sub(r'/\* --- Standardized Enterprise Notification Variables & Scope ---\*/.*?\}', new_block, content, flags=re.DOTALL)

# Let me use another replace method since regex with dotall can be tricky
