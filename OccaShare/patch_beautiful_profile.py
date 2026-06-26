import os
content = """{% set active_page = 'marketplace' %}
{% extends "customer/layout.html" %}

{% block title %}{{ caterer.business_name }} - Caterer Hub{% endblock %}

{% block extra_css %}
<style>
    /* =====================================================
       CATERER HUB - MODERN RESPONSIVE CSS
       ===================================================== */
    :root {
        --hub-primary: #FF7B54;
        --hub-primary-hover: #e06541;
        --hub-bg: #f8fafc;
        --hub-card-bg: #ffffff;
        --hub-border: #e2e8f0;
        --hub-text: #334155;
        --hub-heading: #0f172a;
        --hub-radius: 16px;
        --hub-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    }

    .hub-container {
        font-family: 'Inter', 'Poppins', sans-serif;
        max-width: 1200px;
        margin: 0 auto;
        padding: 2rem 1rem;
        background-color: var(--hub-bg);
        color: var(--hub-text);
    }

    /* Hero Banner */
    .hero-banner {
        position: relative;
        height: 320px;
        border-radius: var(--hub-radius);
        overflow: hidden;
        margin-bottom: 2rem;
        box-shadow: var(--hub-shadow);
        background: #1e293b;
    }
    
    .hero-banner img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        opacity: 0.7;
    }
    
    .hero-content {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 3rem 2rem 2rem;
        background: linear-gradient(to top, rgba(15, 23, 42, 0.9) 0%, transparent 100%);
        display: flex;
        align-items: flex-end;
        gap: 1.5rem;
    }
    
    .hero-logo {
        width: 90px;
        height: 90px;
        border-radius: 50%;
        border: 4px solid white;
        background: white;
        object-fit: cover;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
    
    .hero-info h1 {
        color: white;
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0 0 0.5rem 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }
    
    .hero-tags {
        display: flex;
        gap: 0.8rem;
        flex-wrap: wrap;
    }
    
    .badge {
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(8px);
        color: white;
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 0.4rem;
        border: 1px solid rgba(255,255,255,0.3);
    }
    
    .badge.verified {
        background: #10b981;
        border-color: #10b981;
    }

    /* Tabs */
    .tabs-nav {
        display: flex;
        gap: 1rem;
        border-bottom: 2px solid var(--hub-border);
        margin-bottom: 2rem;
        overflow-x: auto;
        scrollbar-width: none;
    }
    
    .tabs-nav::-webkit-scrollbar { display: none; }
    
    .tab-btn {
        background: transparent;
        border: none;
        padding: 1rem 1.5rem;
        font-size: 1rem;
        font-weight: 600;
        color: var(--hub-text);
        cursor: pointer;
        position: relative;
        transition: color 0.3s ease;
        white-space: nowrap;
    }
    
    .tab-btn:hover {
        color: var(--hub-primary);
    }
    
    .tab-btn.active {
        color: var(--hub-primary);
    }
    
    .tab-btn.active::after {
        content: '';
        position: absolute;
        bottom: -2px;
        left: 0;
        right: 0;
        height: 3px;
        background: var(--hub-primary);
        border-radius: 3px 3px 0 0;
    }
    
    .tab-pane {
        display: none;
        animation: fadeIn 0.4s ease;
    }
    
    .tab-pane.active {
        display: block;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Cards & Grids */
    .section-card {
        background: var(--hub-card-bg);
        border-radius: var(--hub-radius);
        padding: 2rem;
        box-shadow: var(--hub-shadow);
        margin-bottom: 2rem;
    }
    
    .section-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: var(--hub-heading);
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .grid-3 {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 1.5rem;
    }
    
    /* Stats */
    .stats-row {
        display: flex;
        gap: 1.5rem;
        margin-top: 1.5rem;
        flex-wrap: wrap;
    }
    
    .stat-box {
        background: var(--hub-bg);
        padding: 1.5rem;
        border-radius: 12px;
        flex: 1;
        min-width: 140px;
        text-align: center;
        border: 1px solid var(--hub-border);
    }
    
    .stat-box i {
        font-size: 1.8rem;
        color: var(--hub-primary);
        margin-bottom: 0.8rem;
    }
    
    .stat-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: var(--hub-heading);
        margin-bottom: 0.2rem;
    }
    
    .stat-label {
        font-size: 0.85rem;
        color: var(--hub-text);
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    
    /* Package Card */
    .pkg-card {
        background: white;
        border: 1px solid var(--hub-border);
        border-radius: var(--hub-radius);
        overflow: hidden;
        transition: transform 0.2s, box-shadow 0.2s;
        display: flex;
        flex-direction: column;
    }
    
    .pkg-card:hover {
        transform: translateY(-5px);
        box-shadow: var(--hub-shadow);
    }
    
    .pkg-img {
        height: 180px;
        width: 100%;
        object-fit: cover;
    }
    
    .pkg-body {
        padding: 1.5rem;
        display: flex;
        flex-direction: column;
        flex: 1;
    }
    
    .pkg-type {
        font-size: 0.75rem;
        font-weight: 700;
        color: var(--hub-primary);
        text-transform: uppercase;
        margin-bottom: 0.5rem;
        letter-spacing: 1px;
    }
    
    .pkg-name {
        font-size: 1.2rem;
        font-weight: 700;
        color: var(--hub-heading);
        margin-bottom: 0.5rem;
    }
    
    .pkg-price {
        font-size: 1.4rem;
        font-weight: 800;
        color: var(--hub-heading);
        margin-bottom: 1rem;
    }
    
    .pkg-price span {
        font-size: 0.85rem;
        color: var(--hub-text);
        font-weight: 500;
    }
    
    .pkg-btn {
        margin-top: auto;
        background: var(--hub-primary);
        color: white;
        border: none;
        padding: 0.8rem;
        border-radius: 8px;
        font-weight: 600;
        text-align: center;
        text-decoration: none;
        cursor: pointer;
        transition: background 0.2s;
        display: block;
    }
    
    .pkg-btn:hover {
        background: var(--hub-primary-hover);
        color: white;
    }
    
    .pkg-btn-outline {
        background: transparent;
        color: var(--hub-text);
        border: 1px solid var(--hub-border);
        margin-bottom: 0.5rem;
    }
    
    .pkg-btn-outline:hover {
        background: var(--hub-bg);
        color: var(--hub-heading);
    }

    /* Category Item Cards */
    .category-card {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem;
        border: 1px solid var(--hub-border);
        border-radius: 12px;
        background: white;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .category-card:hover {
        border-color: var(--hub-primary);
        box-shadow: 0 4px 12px rgba(255, 123, 84, 0.1);
    }
    
    .category-img {
        width: 60px;
        height: 60px;
        border-radius: 8px;
        object-fit: cover;
        background: var(--hub-bg);
    }
    
    .category-info h3 {
        margin: 0 0 0.25rem 0;
        font-size: 1rem;
        color: var(--hub-heading);
    }
    
    .category-info p {
        margin: 0;
        font-size: 0.8rem;
        color: var(--hub-text);
    }
    
    /* Portfolio Grid */
    .portfolio-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 1rem;
    }
    
    .portfolio-item {
        position: relative;
        aspect-ratio: 4/3;
        border-radius: 12px;
        overflow: hidden;
        cursor: pointer;
        background: var(--hub-bg);
    }
    
    .portfolio-item img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.5s ease;
    }
    
    .portfolio-item:hover img {
        transform: scale(1.05);
    }
    
    .portfolio-overlay {
        position: absolute;
        inset: 0;
        background: linear-gradient(to top, rgba(0,0,0,0.8), transparent);
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        padding: 1.25rem;
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    
    .portfolio-item:hover .portfolio-overlay {
        opacity: 1;
    }
    
    .portfolio-title {
        color: white;
        font-weight: 700;
        font-size: 1.1rem;
        margin-bottom: 0.2rem;
    }
    
    .portfolio-meta {
        color: rgba(255,255,255,0.8);
        font-size: 0.8rem;
    }

    /* Responsive */
    @media (max-width: 768px) {
        .hero-banner { height: 350px; }
        .hero-content { flex-direction: column; align-items: center; text-align: center; padding: 2rem 1rem; }
        .hero-tags { justify-content: center; }
        .tabs-nav { padding-bottom: 0.5rem; }
    }
    
    /* Modals */
    .modal-overlay {
        position: fixed; inset: 0; background: rgba(15,23,42,0.8); z-index: 9999;
        display: none; align-items: center; justify-content: center; backdrop-filter: blur(4px);
    }
    .modal-box {
        background: white; border-radius: 16px; width: 90%; max-width: 600px;
        max-height: 90vh; overflow-y: auto; padding: 2rem; position: relative;
    }
    .modal-close {
        position: absolute; top: 1rem; right: 1rem; background: var(--hub-bg);
        border: none; width: 36px; height: 36px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        cursor: pointer; color: var(--hub-text);
    }
</style>
{% endblock %}

{% block content %}
<div class="hub-container">

    <!-- HERO BANNER -->
    <div class="hero-banner">
        <img src="{{ caterer.cover_image_url if caterer.cover_image_url else 'https://images.unsplash.com/photo-1555244162-803834f70033?q=80&w=1200' }}" alt="Cover">
        <div class="hero-content">
            <img src="{{ caterer.logo_url if caterer.logo_url else '/static/images/default_caterer_logo.png' }}" alt="Logo" class="hero-logo">
            <div class="hero-info">
                <h1>{{ caterer.business_name }}</h1>
                <div class="hero-tags">
                    {% if caterer.verification_status == 'Verified' %}
                    <span class="badge verified"><i class="fas fa-check-circle"></i> Verified Business</span>
                    {% endif %}
                    <span class="badge"><i class="fas fa-map-marker-alt"></i> {{ caterer.city or 'Philippines' }}</span>
                    {% if caterer.rating %}
                    <span class="badge"><i class="fas fa-star" style="color: #fbbf24;"></i> {{ "%.1f"|format(caterer.rating) }} ({{ caterer.reviews|length }} Reviews)</span>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>

    <!-- TABS NAVIGATION -->
    <div class="tabs-nav">
        <button class="tab-btn active" onclick="switchTab('overview', this)">Overview</button>
        <button class="tab-btn" onclick="switchTab('menu', this)">Menu & Packages</button>
        <button class="tab-btn" onclick="switchTab('portfolio', this)">Event Portfolio</button>
        <button class="tab-btn" onclick="switchTab('policies', this)">Policies</button>
    </div>

    <!-- TAB 1: OVERVIEW -->
    <div id="tab-overview" class="tab-pane active">
        <div class="section-card">
            <h2 class="section-title"><i class="fas fa-store"></i> About Us</h2>
            <p style="line-height: 1.7; font-size: 1.05rem;">
                {{ caterer.description or 'We provide excellent catering services for all types of events, ensuring delicious food and great service for your special day.' }}
            </p>
            
            <div class="stats-row">
                <div class="stat-box">
                    <i class="far fa-calendar-alt"></i>
                    <div class="stat-value">{{ caterer.years_of_operation or '1+' }}</div>
                    <div class="stat-label">Years Active</div>
                </div>
                <div class="stat-box">
                    <i class="fas fa-utensils"></i>
                    <div class="stat-value">{{ active_menu|length }}</div>
                    <div class="stat-label">Food Options</div>
                </div>
                <div class="stat-box">
                    <i class="fas fa-truck"></i>
                    <div class="stat-value">{{ active_inventory|length }}</div>
                    <div class="stat-label">Event Rentals</div>
                </div>
            </div>
        </div>
        
        {% if public_portfolios %}
        <div class="section-card">
            <h2 class="section-title"><i class="fas fa-camera"></i> Recent Events</h2>
            <div class="portfolio-grid">
                {% for p in public_portfolios[:4] %}
                {% set cover = p.images | selectattr('is_cover', 'equalto', True) | first %}
                <div class="portfolio-item" onclick="switchTab('portfolio', document.querySelectorAll('.tab-btn')[2])">
                    <img src="{{ cover.image_url if cover else (p.images[0].image_url if p.images else '/static/images/default-portfolio.jpg') }}" alt="Event">
                    <div class="portfolio-overlay">
                        <div class="portfolio-title">{{ p.title }}</div>
                        <div class="portfolio-meta">{{ p.event_type }}</div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
    </div>

    <!-- TAB 2: MENU & PACKAGES -->
    <div id="tab-menu" class="tab-pane">
        
        <!-- Packages -->
        {% if packages %}
        <div class="section-card">
            <h2 class="section-title"><i class="fas fa-box-open"></i> Catering Packages</h2>
            <p style="margin-bottom: 1.5rem; color: var(--hub-text);">Ready-made bundles to make your event planning easier.</p>
            <div class="grid-3">
                {% for pkg in packages %}
                <div class="pkg-card">
                    <img src="{{ pkg.image_url if pkg.image_url else 'https://images.unsplash.com/photo-1555244162-803834f70033?q=80&w=400' }}" class="pkg-img" alt="Package">
                    <div class="pkg-body">
                        <span class="pkg-type">{{ pkg.service_type or 'Standard Package' }}</span>
                        <h3 class="pkg-name">{{ pkg.name }}</h3>
                        
                        <div class="pkg-price">
                            {% if pkg.price_per_head %}
                            ,{{ "{:,.2f}".format(pkg.price_per_head) }} <span>/person</span>
                            {% elif pkg.price_unit == 'per_guest' %}
                            ,{{ "{:,.2f}".format(pkg.price if pkg.price else 0) }} <span>/person</span>
                            {% else %}
                            ,{{ "{:,.2f}".format(pkg.price if pkg.price else 0) }} <span>total</span>
                            {% endif %}
                        </div>
                        
                        <button type="button" class="pkg-btn pkg-btn-outline" onclick="openPkgDetails('{{ pkg.id }}')">
                            View What's Included
                        </button>
                        <a href="/bookings/start/{{ caterer.id }}?package_id={{ pkg.id }}" class="pkg-btn">
                            Book This Package
                        </a>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <!-- Food Menu -->
        <div class="section-card">
            <h2 class="section-title"><i class="fas fa-concierge-bell"></i> Food Menu</h2>
            <p style="margin-bottom: 1.5rem; color: var(--hub-text);">Browse our wide selection of dishes.</p>
            
            {% set menu_categories = [] %}
            {% for item in active_menu %}
                {% if item.category and item.category not in menu_categories %}
                    {% set _ = menu_categories.append(item.category) %}
                {% endif %}
            {% endfor %}
            
            {% if menu_categories %}
            <div class="grid-3">
                {% for cat in menu_categories %}
                {% set cat_items = active_menu | selectattr('category', 'equalto', cat) | list %}
                {% set display_img = namespace(url='') %}
                {% for item in cat_items %}
                    {% if item.image_url and not display_img.url %}
                        {% set display_img.url = item.image_url %}
                    {% endif %}
                {% endfor %}
                
                <div class="category-card" onclick="openCategoryModal('{{ cat|e }}', 'menu')">
                    <img src="{{ display_img.url if display_img.url else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=150' }}" class="category-img" alt="{{ cat }}">
                    <div class="category-info">
                        <h3>{{ cat }}</h3>
                        <p>{{ cat_items|length }} dishes available</p>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <p>No menu items published yet.</p>
            {% endif %}
        </div>
        
        <!-- Rentals & Services -->
        <div class="section-card">
            <h2 class="section-title"><i class="fas fa-chair"></i> Event Rentals & Services</h2>
            <p style="margin-bottom: 1.5rem; color: var(--hub-text);">Add tables, chairs, waiters, and more to your event.</p>
            
            {% set inv_categories = [] %}
            {% for item in active_inventory %}
                {% set cat_name = item.category if item.category else ('Equipment' if item.equipment_type else 'Service') %}
                {% if cat_name not in inv_categories %}
                    {% set _ = inv_categories.append(cat_name) %}
                {% endif %}
            {% endfor %}
            
            {% if inv_categories %}
            <div class="grid-3">
                {% for cat in inv_categories %}
                {% set cat_items = [] %}
                {% for item in active_inventory %}
                    {% set item_cat = item.category if item.category else ('Equipment' if item.equipment_type else 'Service') %}
                    {% if item_cat == cat %}
                        {% set _ = cat_items.append(item) %}
                    {% endif %}
                {% endfor %}
                
                {% set display_img = namespace(url='') %}
                {% for item in cat_items %}
                    {% if item.image_url and not display_img.url %}
                        {% set display_img.url = item.image_url %}
                    {% endif %}
                {% endfor %}
                
                <div class="category-card" onclick="openCategoryModal('{{ cat|e }}', 'inventory')">
                    <img src="{{ display_img.url if display_img.url else 'https://images.unsplash.com/photo-1519167758481-83f550bb49b3?q=80&w=150' }}" class="category-img" alt="{{ cat }}">
                    <div class="category-info">
                        <h3>{{ cat }}</h3>
                        <p>{{ cat_items|length }} options available</p>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <p>No rentals or services published yet.</p>
            {% endif %}
        </div>
    </div>

    <!-- TAB 3: PORTFOLIO -->
    <div id="tab-portfolio" class="tab-pane">
        <div class="section-card">
            <h2 class="section-title"><i class="fas fa-images"></i> Event Portfolio</h2>
            <p style="margin-bottom: 1.5rem; color: var(--hub-text);">See our previous successful events.</p>
            
            {% if public_portfolios %}
            <div class="portfolio-grid">
                {% for p in public_portfolios %}
                {% set cover = p.images | selectattr('is_cover', 'equalto', True) | first %}
                <div class="portfolio-item" onclick="openPortfolioViewModal({{ p.id }})">
                    <img src="{{ cover.image_url if cover else (p.images[0].image_url if p.images else '/static/images/default-portfolio.jpg') }}" alt="{{ p.title }}">
                    <div class="portfolio-overlay">
                        <div class="portfolio-title">{{ p.title }}</div>
                        <div class="portfolio-meta"><i class="fas fa-map-marker-alt"></i> {{ p.location or 'Local Venue' }}</div>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <p>No portfolio items uploaded yet.</p>
            {% endif %}
        </div>
    </div>

    <!-- TAB 4: POLICIES -->
    <div id="tab-policies" class="tab-pane">
        <div class="section-card">
            <h2 class="section-title"><i class="fas fa-file-contract"></i> Booking Policies</h2>
            
            <div style="display: flex; flex-direction: column; gap: 1rem; margin-top: 1.5rem;">
                <div style="padding: 1.5rem; background: var(--hub-bg); border-radius: 12px; border-left: 4px solid var(--hub-primary);">
                    <h3 style="margin:0 0 0.5rem; font-size: 1.1rem; color: var(--hub-heading);">Reservation Fee</h3>
                    <p style="margin:0; font-size: 0.95rem;">
                        A <strong>{{ caterer.default_reservation_value }}{{ '%' if caterer.default_reservation_type == 'percentage' else ' PHP' }}</strong> 
                        reservation fee is required to confirm your booking.
                    </p>
                </div>
                
                <div style="padding: 1.5rem; background: var(--hub-bg); border-radius: 12px; border-left: 4px solid #3b82f6;">
                    <h3 style="margin:0 0 0.5rem; font-size: 1.1rem; color: var(--hub-heading);">Advance Booking Required</h3>
                    <p style="margin:0; font-size: 0.95rem;">
                        Please book at least <strong>{{ caterer.default_booking_lead_time or 7 }} days</strong> before your event date.
                    </p>
                </div>
                
                {% if caterer.policies %}
                <div style="padding: 1.5rem; background: var(--hub-bg); border-radius: 12px; border-left: 4px solid #8b5cf6;">
                    <h3 style="margin:0 0 0.5rem; font-size: 1.1rem; color: var(--hub-heading);">Caterer Notes</h3>
                    <p style="margin:0; font-size: 0.95rem; white-space: pre-wrap;">{{ caterer.policies }}</p>
                </div>
                {% endif %}
            </div>
        </div>
    </div>

</div>

<!-- DATA SCRIPT & MODALS INITIALIZATION -->
<script>
    // Tab Switching Logic
    function switchTab(tabId, btnElement) {
        // Hide all tabs
        document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
        // Deactivate all buttons
        document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
        
        // Show target tab
        document.getElementById('tab-' + tabId).classList.add('active');
        // Activate target button
        btnElement.classList.add('active');
    }

    // Modal data setup for packages
    window.hubPkgs = {
        {% for pkg in packages %}
        "{{ pkg.id }}": {
            name: {{ pkg.name|tojson }},
            description: {{ (pkg.description or 'A complete catering package.')|tojson }},
            price: ",{{ '{:,.2f}'.format(pkg.price_per_head if pkg.price_per_head else (pkg.price or 0)) }}{{ '/pax' if (pkg.price_per_head or pkg.price_unit == 'per_guest') else '' }}",
            inclusions: {{ (pkg.inclusions)|tojson if pkg.inclusions else '[]' }},
            linked_inventory: [
                {% for item in pkg.menu_items %}{% if item.category in ['Rentals', 'Services'] %}{{ item.name|tojson }},{% endif %}{% endfor %}
                {% if pkg.equipment_links %}{% for el in pkg.equipment_links %}{{ el.equipment.name|tojson }},{% endfor %}{% endif %}
                {% if pkg.service_links %}{% for sl in pkg.service_links %}{{ sl.service.name|tojson }},{% endfor %}{% endif %}
            ].filter(Boolean),
            dishes: [{% for item in pkg.menu_items %}{% if item.category not in ['Rentals', 'Services'] %}{{ item.name|tojson }},{% endif %}{% endfor %}].filter(Boolean)
        }{{ ',' if not loop.last }}
        {% endfor %}
    };

    function openPkgDetails(id) {
        const pkg = window.hubPkgs[id];
        if(!pkg) return;
        
        let html = `
            <h2 style="font-size:1.5rem;font-weight:800;color:#0f172a;margin:0 0 0.5rem 0">${pkg.name}</h2>
            <div style="font-size:1.25rem;font-weight:800;color:var(--hub-primary);margin-bottom:1rem">${pkg.price}</div>
            <p style="color:#475569;font-size:0.95rem;margin-bottom:1.5rem;line-height:1.6">${pkg.description}</p>
            
            <h3 style="font-size:1rem;font-weight:700;color:#0f172a;margin-bottom:0.75rem;padding-bottom:0.5rem;border-bottom:1px solid #e2e8f0">What's Included</h3>
            <ul style="list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:0.75rem;">
        `;
        
        // Add Dishes
        if(pkg.dishes && pkg.dishes.length > 0) {
            pkg.dishes.forEach(d => {
                html += `<li style="display:flex;gap:0.75rem;font-size:0.9rem;color:#334155"><i class="fas fa-utensils" style="color:var(--hub-primary);margin-top:4px"></i> Food: ${d}</li>`;
            });
        }
        
        // Add Equipment & Services
        if(pkg.linked_inventory && pkg.linked_inventory.length > 0) {
            pkg.linked_inventory.forEach(i => {
                html += `<li style="display:flex;gap:0.75rem;font-size:0.9rem;color:#334155"><i class="fas fa-check-circle" style="color:#10b981;margin-top:4px"></i> ${i}</li>`;
            });
        }
        
        // Add Legacy Inclusions
        let incList = [];
        try {
            if(Array.isArray(pkg.inclusions)) incList = pkg.inclusions;
            else if (typeof pkg.inclusions === 'object') incList = Object.keys(pkg.inclusions).filter(k => pkg.inclusions[k]);
            else incList = JSON.parse(pkg.inclusions);
        } catch(e) {}
        
        if(Array.isArray(incList) && incList.length > 0) {
            incList.forEach(i => {
                html += `<li style="display:flex;gap:0.75rem;font-size:0.9rem;color:#334155"><i class="fas fa-check" style="color:#10b981;margin-top:4px"></i> ${i}</li>`;
            });
        }
        
        if(pkg.dishes.length === 0 && pkg.linked_inventory.length === 0 && incList.length === 0) {
             html += `<li style="color:#94a3b8;font-size:0.9rem;font-style:italic">No specific inclusions listed.</li>`;
        }
        
        html += `</ul>`;
        
        // Show in a generic modal
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-box">
                <button class="modal-close" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
                ${html}
            </div>
        `;
        document.body.appendChild(modal);
        modal.style.display = 'flex';
    }

    function openCategoryModal(cat, type) {
        alert("Feature 'View Items for " + cat + "' will open a list of items. (To be fully implemented if needed)");
    }

    function openPortfolioViewModal(id) {
        alert("Feature 'View Portfolio Gallery' will open the image viewer.");
    }
</script>
{% endblock %}
"""
with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Saved")
