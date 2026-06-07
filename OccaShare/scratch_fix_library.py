with open(r'c:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = '''                        {% set cat_metadata = {
                            'Main Course': {'img': 'https://images.unsplash.com/photo-1544025162-d76694265947?q=80&w=400', 'desc': 'Hearty and savory central dishes.'},
                            'Rentals': {'img': 'https://images.unsplash.com/photo-1519167758481-83f550bb49b3?q=80&w=400', 'desc': 'Premium equipment & table setups.'},
                            'Appetizer': {'img': 'https://images.unsplash.com/photo-1541529086526-db283c563270?q=80&w=400', 'desc': 'Delightful starters to awaken palates.'},
                            'Dessert': {'img': 'https://images.unsplash.com/photo-1551024601-bec78aea704b?q=80&w=400', 'desc': 'Sweet and decadent treats.'},
                            'Beverage': {'img': 'https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?q=80&w=400', 'desc': 'Refreshing drinks for everyone.'},
                            'Services': {'img': 'https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?q=80&w=400', 'desc': 'Professional event staffing.'}
                        } %}
                        {% for cat in categories %}
                        {% set cat_items = active_menu | selectattr('category', 'equalto', cat) | list %}
                        {% set c_meta = cat_metadata.get(cat, {}) %}
                        {% set first_img = cat_items[0].image_url if cat_items[0].image_url else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=400' %}
                        {% set display_img = c_meta.get('img') if c_meta.get('img') else first_img %}
                        <div class="cat-card" onclick="window.openCategoryModal('{{ cat|e }}')">
                            <img src="{{ display_img }}" class="cat-card-img" alt="{{ cat }}" loading="lazy">
                            <div class="cat-card-body">
                                <span class="cat-card-name">{{ cat }}</span>
                                <span class="cat-card-desc" style="font-size: 0.75rem; color: #64748b; margin-top: 2px; display: block; line-height: 1.3;">{{ c_meta.get('desc', 'Explore our curated selection.') }}</span>
                                <span class="cat-card-count" style="margin-top: 6px; display: inline-block;">{{ cat_items|length }} item{{ 's' if cat_items|length != 1 else '' }}</span>
                            </div>
                            <div class="cat-card-footer">
                                <span>Browse {{ 'Items' if cat in ['Rentals', 'Services'] else 'Dishes' }}</span>
                                <i class="fas fa-chevron-right" style="font-size: 0.65rem;"></i>
                            </div>
                        </div>'''

target = '''                        {% for cat in categories %}
                        {% set cat_items = active_menu | selectattr('category', 'equalto', cat) | list %}
                        {% set first_img = cat_items[0].image_url if cat_items[0].image_url else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=400' %}
                        <div class="cat-card" onclick="window.openCategoryModal('{{ cat|e }}')">
                            <img src="{{ first_img }}" class="cat-card-img" alt="{{ cat }}" loading="lazy">
                            <div class="cat-card-body">
                                <span class="cat-card-name">{{ cat }}</span>
                                <span class="cat-card-count">{{ cat_items|length }} dish{{ 'es' if cat_items|length != 1 else '' }}</span>
                            </div>
                            <div class="cat-card-footer">
                                <span>Browse dishes</span>
                                <i class="fas fa-chevron-right" style="font-size: 0.65rem;"></i>
                            </div>
                        </div>'''

content = content.replace('\r\n', '\n')
target = target.replace('\r\n', '\n')
content = content.replace(target, replacement)

with open(r'c:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'w', encoding='utf-8') as f:
    f.write(content)
