import codecs
import json

with codecs.open('c:\\OccaServe\\OccaShare\\templates\\customer\\caterer_profile_view.html', 'r', 'utf-8') as f:
    content = f.read()

# Add gallery_images to JSON
content = content.replace(
    '        image_url: pkg.image_url,',
    '        image_url: pkg.image_url,\n        gallery_images: pkg.gallery_images ? pkg.gallery_images : [],'
)

# Fix pkg.dishes to exclude order_only
content = content.replace(
    '''        dishes: [{% for item in pkg.menu_items %}{% if item.category not in ['Rentals', 'Services'] %}{{ item.name|tojson }},{% endif %}{% endfor %}].filter(Boolean),''',
    '''        dishes: [{% for item in pkg.menu_items %}{% if item.category not in ['Rentals', 'Services'] and item.usage_type != 'order_only' %}{{ item.name|tojson }},{% endif %}{% endfor %}].filter(Boolean),'''
)

# Rename 'Included Menu Options' dynamically
new_dish_html = '''            if (pkg.dishes && pkg.dishes.length > 0) {
                const titleText = (pkg.selection_rules && Object.keys(pkg.selection_rules).length > 0) ? "Available Menu Choices" : "Included Menu Options";
                dishHtml += `
                <div style="margin-bottom:1.25rem;">
                    <h4 style="font-size:0.72rem;font-weight:800;color:var(--hub-slate-400);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.75rem;">
                        <i class="fas fa-list" style="color:var(--hub-primary);margin-right:6px;"></i>${titleText}
                    </h4>
                    <div style="display:flex;flex-wrap:wrap;gap:6px;">
                        ${pkg.dishes.map(d => `<span style="background:#fff;color:var(--hub-text-dark);padding:4px 12px;border-radius:100px;font-size:0.72rem;font-weight:600;border:1px solid var(--hub-slate-200);">${d}</span>`).join('')}
                    </div>
                </div>`;
            }'''

content = content.replace(
    '''            if (pkg.dishes && pkg.dishes.length > 0) {
                dishHtml += `
                <div style="margin-bottom:1.25rem;">
                    <h4 style="font-size:0.72rem;font-weight:800;color:var(--hub-slate-400);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.75rem;">
                        <i class="fas fa-list" style="color:var(--hub-primary);margin-right:6px;"></i>Included Menu Options
                    </h4>
                    <div style="display:flex;flex-wrap:wrap;gap:6px;">
                        ${pkg.dishes.map(d => `<span style="background:#fff;color:var(--hub-text-dark);padding:4px 12px;border-radius:100px;font-size:0.72rem;font-weight:600;border:1px solid var(--hub-slate-200);">${d}</span>`).join('')}
                    </div>
                </div>`;
            }''',
    new_dish_html
)

with codecs.open('c:\\OccaServe\\OccaShare\\templates\\customer\\caterer_profile_view.html', 'w', 'utf-8') as f:
    f.write(content)
print('Done!')
