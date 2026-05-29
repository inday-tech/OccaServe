import re

file_path = r'c:\OccaServe\OccaShare\templates\admin\settings.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace header titles
content = content.replace('Platform Configuration', 'Site Settings')
content = content.replace('Calibrate system behaviors, visual identifiers, and financial parameters.', 'Manage the platform\'s core behaviors, logo, social links, and security.')

# Replace Sidebar Tabs
content = content.replace('System Nodes', 'System Settings')
content = content.replace('General Intelligence', 'General Settings')
content = content.replace('Visual Branding', 'Appearance & Logo')
content = content.replace('Connectivity', 'Social Media Links')
content = content.replace('Operational Shield', 'Maintenance Mode')
content = content.replace('Credential Layer', 'Security & Password')

# Replace Panel Headers & Subtitles
content = content.replace('Core platform identity and standard operational rates.', 'Basic site info and financial rates.')
content = content.replace('Manage the platform\'s public identifiers and browser assets.', 'Manage logos and browser icons.')
content = content.replace('Sync your platform with official social media channels.', 'Connect your platform to official social media channels.')
content = content.replace('Throttle public access during critical system maintenance.', 'Restrict public access during system updates.')
content = content.replace('Update your administrative key to maintain system integrity.', 'Update your admin password securely.')

# Add pagination logic to the Audit list
# First, add a class to audit items
content = content.replace('<div class="audit-item">', '<div class="audit-item pagination-item">')
# Next, add the pagination controls right after the audit-list div ends.
# We will find `<div class="audit-list">...</div>` and inject controls.
content = content.replace(
    '</div>\n                </div>\n            </div>\n\n            <div class="display-footer"',
    '</div>\n                    <div id="audit-pagination" style="display:flex; justify-content:center; gap:0.5rem; margin-top:1.5rem;"></div>\n                </div>\n            </div>\n\n            <div class="display-footer"'
)

# Finally, inject the JS logic at the end of the script block
js_logic = """
    // Pagination Logic for Audit History
    let currentPage = 1;
    const itemsPerPage = 5;

    function renderPagination() {
        const items = document.querySelectorAll('.pagination-item');
        if(items.length === 0) return;
        
        const totalPages = Math.ceil(items.length / itemsPerPage);
        const paginationContainer = document.getElementById('audit-pagination');
        
        if(totalPages <= 1) {
            paginationContainer.style.display = 'none';
            return;
        }

        // Show/hide items
        items.forEach((item, index) => {
            const isVisible = index >= (currentPage - 1) * itemsPerPage && index < currentPage * itemsPerPage;
            item.style.display = isVisible ? 'flex' : 'none';
        });

        // Render buttons
        let buttonsHTML = '';
        for(let i = 1; i <= totalPages; i++) {
            const activeClass = i === currentPage ? 'background: var(--dm-primary); color: white; border: none;' : 'background: white; border: 1px solid var(--dm-border); color: var(--dm-secondary);';
            buttonsHTML += `<button type="button" onclick="goToPage(${i})" style="padding: 0.5rem 1rem; border-radius: 0.5rem; cursor: pointer; font-weight: 600; ${activeClass}">${i}</button>`;
        }
        paginationContainer.innerHTML = buttonsHTML;
    }

    function goToPage(page) {
        currentPage = page;
        renderPagination();
    }

    // Call once on load
    document.addEventListener('DOMContentLoaded', () => {
        renderPagination();
    });
</script>
"""

content = content.replace('</script>', js_logic)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Modifications done.")
