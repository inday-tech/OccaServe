import re

filepath = r'c:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the new tabs structure
new_tabs_content = """            <!-- PACKAGES TAB -->
            <div id="hub-tab-packages" class="tab-content">
                {% if packages %}
                <div class="intel-card" style="padding: 1.75rem;">
                    <h2 class="section-title">Ready-to-Book Packages</h2>
                    <div class="pkg-grid">
                        {% for pkg in packages %}
                        <div class="elite-item-card pkg-item">
                            <div class="ei-img-box">
                                <img src="{{ pkg.image_url if pkg.image_url else 'https://images.unsplash.com/photo-1555244162-803834f70033?q=80&w=400' }}" onerror="this.src='https://images.unsplash.com/photo-1555244162-803834f70033?q=80&w=400'" class="ei-img">
                            </div>
                            <div class="ei-body">
                                <span class="ei-cat">{{ pkg.service_type or 'General' }}</span>
                                <span class="ei-name">{{ pkg.name }}</span>
                                {% if pkg.pricing_mode == 'fixed' or pkg.price_unit == 'total' %}
                                <span class="ei-price">₱{{ "{:,.2f}".format(pkg.price if pkg.price else (pkg.price_per_head if pkg.price_per_head else 0)) }}<span style="font-size:0.65rem;font-weight:600;color:var(--hub-slate-400)"> total</span></span>
                                {% else %}
                                <span class="ei-price">₱{{ "{:,.2f}".format(pkg.price_per_head if pkg.price_per_head else (pkg.price if pkg.price else 0)) }}<span style="font-size:0.65rem;font-weight:600;color:var(--hub-slate-400)">/pax</span></span>
                                {% endif %}
                                <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px; flex-wrap: wrap;">
                                    {% if pkg.min_guests %}
                                    <span style="font-size:0.65rem;background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;border-radius:4px;padding:2px 6px;font-weight:800;">
                                        <i class="fas fa-users" style="margin-right:2px;"></i> Min {{ pkg.min_guests }}{% if pkg.max_guests %} - Max {{ pkg.max_guests }}{% endif %} pax
                                    </span>
                                    {% endif %}
                                    {% if pkg.service_duration %}
                                    <span style="font-size:0.65rem;background:#f5f3ff;color:#6d28d9;border:1px solid #ddd6fe;border-radius:4px;padding:2px 6px;font-weight:800;">
                                        <i class="fas fa-clock" style="margin-right:2px;"></i> {{ pkg.service_duration }} hrs
                                    </span>
                                    {% endif %}
                                </div>
                                {% if pkg.dishes and pkg.dishes|length > 0 %}
                                <div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:0.5rem; max-height:45px; overflow:hidden;">
                                    {% for dish in pkg.dishes[:3] %}
                                    <span style="font-size:0.65rem; background:var(--hub-slate-50); color:var(--hub-slate-600); padding:2px 8px; border-radius:100px; border:1px solid var(--hub-slate-100); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:100%;">{{ dish }}</span>
                                    {% endfor %}
                                    {% if pkg.dishes|length > 3 %}
                                    <span style="font-size:0.65rem; background:var(--hub-slate-100); color:var(--hub-slate-600); padding:2px 8px; border-radius:100px; font-weight:700;">+{{ pkg.dishes|length - 3 }}</span>
                                    {% endif %}
                                </div>
                                {% endif %}
                                <div style="display:flex;gap:0.5rem;margin-top:auto;padding-top:1rem;flex-direction:column;">
                                    <button type="button" onclick='window.openPkgDetails("{{ pkg.id }}")' class="btn-elite-sm">
                                        <i class="fas fa-list-check"></i> View Inclusions
                                    </button>
                                    {% if caterer_unavailable %}
                                    <span class="btn-hub-main" style="font-size:0.78rem;padding:0.7rem;text-align:center;opacity:0.5;cursor:not-allowed;justify-content:center;">
                                        <i class="fas fa-ban"></i> Unavailable
                                    </span>
                                    {% else %}
                                    <a href="/bookings/start/{{ caterer.id }}?package_id={{ pkg.id }}" class="btn-hub-main" style="font-size:0.78rem;padding:0.7rem;text-decoration:none;text-align:center;">
                                        <i class="fas fa-calendar-plus"></i> Select Package
                                    </a>
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                {% else %}
                <div class="intel-card" style="padding: 1.75rem;">
                    <p style="color: var(--hub-slate-400); font-size: 0.9rem;">No packages available yet.</p>
                </div>
                {% endif %}
            </div> <!-- Closes hub-tab-packages -->

            <!-- MENU TAB -->
            <div id="hub-tab-menu" class="tab-content">
                <div class="intel-card" style="padding: 1.75rem;">
                    <h2 class="section-title">Food Menu</h2>
                    
                    {% if active_menu %}
                    {% set categories = [] %}
                    {% for item in active_menu %}
                        {% if item.category and item.category not in categories %}
                            {% set _ = categories.append(item.category) %}
                        {% endif %}
                    {% endfor %}
                    
                    <!-- Inline Category Filter (Foodpanda Style) -->
                    <div class="category-hub" id="menu-category-filter">
                        <button class="category-chip active" onclick="filterMenu('all', this)">All Dishes</button>
                        {% for cat in categories %}
                        <button class="category-chip" onclick="filterMenu('{{ cat }}', this)">{{ cat }}</button>
                        {% endfor %}
                    </div>

                    <div class="dish-grid" id="menu-dish-grid">
                        {% for item in active_menu %}
                        {% set item_price = item.price or 0 %}
                        {% if item.variants and item.variants|length > 0 %}
                            {% set available_vars = item.variants | selectattr('status', 'equalto', 'available') | list %}
                            {% if available_vars %}
                                {% set item_price = available_vars[0].price %}
                            {% else %}
                                {% set item_price = item.variants[0].price %}
                            {% endif %}
                        {% elif item.pricing_type == 'weight_based' and item.weight_prices %}
                            {% set item_price = item.weight_prices[0].price %}
                        {% elif item.pricing_type == 'size_based' and item.size_prices %}
                            {% set item_price = item.size_prices[0].price %}
                        {% endif %}

                        <div class="elite-item-card menu-item-display" data-category="{{ item.category }}">
                            <div class="ei-img-box">
                                <img src="{{ item.image_url if item.image_url else 'https://ui-avatars.com/api/?name=' ~ (item.name|urlencode) ~ '&background=f1f5f9&color=FF7B54' }}" class="ei-img">
                            </div>
                            <div class="ei-body" style="padding: 1rem;">
                                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                                    <span class="ei-cat">{{ item.category }}</span>
                                    {% if item.average_rating and item.average_rating > 0 %}
                                    <span style="font-size:0.65rem; font-weight:800; color:#b45309; background:rgba(245, 158, 11, 0.1); padding:2px 6px; border-radius:100px;">
                                        <i class="fas fa-star"></i> {{ "%.1f"|format(item.average_rating) }} ({{ item.review_count }})
                                    </span>
                                    {% endif %}
                                </div>
                                <span class="ei-name" style="min-height: auto; margin-top: 4px;">{{ item.name }}</span>
                                <span class="ei-price" style="font-size: 1rem; margin-top: 4px;">₱{{ "{:,.2f}".format(item_price) }}</span>
                                
                                {% if item.serving_size or item.serving_capacity %}
                                <div style="font-size:0.7rem; color:var(--hub-slate-500); margin-top:4px;">
                                    <i class="fas fa-user-friends"></i> {{ item.serving_capacity if item.serving_capacity else item.serving_size }}
                                </div>
                                {% endif %}
                                
                                {% if item.description %}
                                <p style="font-size:0.75rem; color:var(--hub-slate-500); margin-top:8px; line-height:1.4; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">
                                    {{ item.description }}
                                </p>
                                {% endif %}
                                
                                <button type="button" onclick="window.openDishDetails({{ item.id }})" class="btn-elite-sm" style="margin-top:auto;">
                                    View Details
                                </button>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                    {% else %}
                    <p style="color: var(--hub-slate-400); font-size: 0.9rem;">No dishes available yet.</p>
                    {% endif %}
                </div>
            </div> <!-- Closes hub-tab-menu -->

            <!-- SERVICES TAB -->
            <div id="hub-tab-services" class="tab-content">
                <div class="intel-card" style="padding: 1.75rem;">
                    <h2 class="section-title">Event Services</h2>
                    
                    {% set services = [] %}
                    {% for item in active_inventory %}
                        {% if not item.equipment_type %}
                            {% set _ = services.append(item) %}
                        {% endif %}
                    {% endfor %}
                    
                    {% if services %}
                    <div class="dish-grid">
                        {% for item in services %}
                        <div class="elite-item-card">
                            <div class="ei-img-box">
                                <img src="{{ item.image_url if item.image_url else 'https://ui-avatars.com/api/?name=' ~ (item.name|urlencode) ~ '&background=f1f5f9&color=3b82f6' }}" class="ei-img">
                            </div>
                            <div class="ei-body" style="padding: 1rem;">
                                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                                    <span class="ei-cat">{{ item.category or 'Service' }}</span>
                                    {% if item.average_rating and item.average_rating > 0 %}
                                    <span style="font-size:0.65rem; font-weight:800; color:#b45309; background:rgba(245, 158, 11, 0.1); padding:2px 6px; border-radius:100px;">
                                        <i class="fas fa-star"></i> {{ "%.1f"|format(item.average_rating) }} ({{ item.review_count }})
                                    </span>
                                    {% endif %}
                                </div>
                                <span class="ei-name" style="min-height: auto; margin-top: 4px;">{{ item.name }}</span>
                                <span class="ei-price" style="font-size: 1rem; margin-top: 4px;">₱{{ "{:,.2f}".format(item.display_price or 0) }}</span>
                                
                                <button type="button" onclick="window.openInventoryModal('{{ item.category or 'Service' }}')" class="btn-elite-sm" style="margin-top:auto;">
                                    View Details
                                </button>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                    {% else %}
                    <p style="color: var(--hub-slate-400); font-size: 0.9rem;">No services available.</p>
                    {% endif %}
                </div>
            </div> <!-- Closes hub-tab-services -->

            <!-- EQUIPMENT TAB -->
            <div id="hub-tab-equipment" class="tab-content">
                <div class="intel-card" style="padding: 1.75rem;">
                    <h2 class="section-title">Equipment Rentals</h2>
                    
                    {% set equipment = [] %}
                    {% for item in active_inventory %}
                        {% if item.equipment_type %}
                            {% set _ = equipment.append(item) %}
                        {% endif %}
                    {% endfor %}
                    
                    {% if equipment %}
                    <div class="dish-grid">
                        {% for item in equipment %}
                        <div class="elite-item-card">
                            <div class="ei-img-box">
                                <img src="{{ item.image_url if item.image_url else 'https://ui-avatars.com/api/?name=' ~ (item.name|urlencode) ~ '&background=f1f5f9&color=10b981' }}" class="ei-img">
                            </div>
                            <div class="ei-body" style="padding: 1rem;">
                                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                                    <span class="ei-cat">{{ item.category or 'Equipment' }}</span>
                                    {% if item.average_rating and item.average_rating > 0 %}
                                    <span style="font-size:0.65rem; font-weight:800; color:#b45309; background:rgba(245, 158, 11, 0.1); padding:2px 6px; border-radius:100px;">
                                        <i class="fas fa-star"></i> {{ "%.1f"|format(item.average_rating) }} ({{ item.review_count }})
                                    </span>
                                    {% endif %}
                                </div>
                                <span class="ei-name" style="min-height: auto; margin-top: 4px;">{{ item.name }}</span>
                                <span class="ei-price" style="font-size: 1rem; margin-top: 4px;">₱{{ "{:,.2f}".format(item.display_price or 0) }}</span>
                                
                                <button type="button" onclick="window.openInventoryModal('{{ item.category or 'Equipment' }}')" class="btn-elite-sm" style="margin-top:auto;">
                                    View Details
                                </button>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                    {% else %}
                    <p style="color: var(--hub-slate-400); font-size: 0.9rem;">No equipment rentals available.</p>
                    {% endif %}
                </div>
            </div> <!-- Closes hub-tab-equipment -->
"""

# Now we need to isolate the old block and replace it.
# The old block starts at <!-- MENU & PACKAGES TAB --> and ends at <!-- Closes hub-tab-menu -->

pattern = re.compile(r'<!-- MENU & PACKAGES TAB -->.*?</div> <!-- Closes hub-tab-menu -->', re.DOTALL)
new_content = pattern.sub(new_tabs_content, content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Successfully replaced tabs!")
