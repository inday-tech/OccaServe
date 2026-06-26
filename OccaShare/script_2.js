
        window.hubMenuItems = [
            {% for item in active_menu %}
            {
                id: {{ item.id|tojson }},
                name: {{ item.name|tojson }},
                category: {{ (item.category or '')|tojson }},
                price: {{ (item.price or 0)|tojson }},
                image: {{ (item.image_url or '')|tojson }},
                description: {{ (item.description or '')|tojson }},
                serving_size: {{ (item.serving_size or '')|tojson }},
                pricing_unit: {{ (item.pricing_unit or 'per_serving')|tojson }},
                dietary_tags: {{ (item.dietary_tags or [])|tojson }},
                allergen_info: {{ (item.allergen_info or [])|tojson }},
                pricing_type: "{{ item.pricing_type or 'fixed' }}",
                weight_prices: [
                    {% for wp in item.weight_prices %}
                    { weight_label: {{ wp.weight_label|tojson }}, price: {{ wp.price|tojson }} }{{ ',' if not loop.last else '' }}
                    {% endfor %}
                ],
                size_prices: [
                    {% for sp in item.size_prices %}
                    { size_name: {{ sp.size_name|tojson }}, price: {{ sp.price|tojson }}, capacity: {{ (sp.capacity or '')|tojson }} }{{ ',' if not loop.last else '' }}
                    {% endfor %}
                ]
            }{{ ',' if not loop.last else '' }}
            {% endfor %}
        ];

        window.hubInventoryItems = [
            {% for item in active_inventory %}
            {
                id: {{ item.id|tojson }},
                name: {{ item.name|tojson }},
                category: {{ (item.category or '')|tojson }},
                price: {{ (item.rental_price if item.rental_price is defined else item.selling_price)|tojson }},
                image: {{ (item.image_url or '')|tojson }},
                description: {{ (item.description or '')|tojson }},
                pricing_unit: {{ (item.unit_type or 'piece')|tojson }},
                type: "{{ 'Equipment' if item.rental_price is defined else 'Service' }}"
            }{{ ',' if not loop.last else '' }}
            {% endfor %}
        ];

        window.hubPortfolios = {
            {% for p in public_portfolios %}
            "{{ p.id }}": {
                id: {{ p.id|tojson }},
                title: {{ p.title|tojson }},
                event_type: {{ p.event_type|tojson }},
                description: {{ p.description|tojson }},
                location: {{ p.location|tojson }},
                is_featured: {{ p.is_featured|tojson }},
                booking_id: {{ p.booking_id|tojson }},
                highlights: {{ (p.highlights or '')|tojson }},
                images: [
                    {% for img in p.images %}
                    "{{ img.image_url }}"{{ ',' if not loop.last else '' }}
                    {% endfor %}
                ]
            }{{ ',' if not loop.last else '' }}
            {% endfor %}
        };

        let currentPortfolioImages = [];
        let currentImageIndex = 0;

        window.openPortfolioViewModal = function(id) {
            const p = window.hubPortfolios[String(id)];
            if (!p) return;

            document.getElementById('portfolio-view-title').textContent = p.title;
            document.getElementById('portfolio-view-type').textContent = p.event_type;
            document.getElementById('portfolio-view-desc').textContent = p.description;

            // Badges
            let badgesHtml = '';
            if (p.booking_id) {
                badgesHtml += '<span style="background: #10b981; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 800; text-transform: uppercase;"><i class="fas fa-check-circle"></i> Verified Event</span>';
            }
            if (p.is_featured) {
                badgesHtml += '<span style="background: #f59e0b; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 800; text-transform: uppercase;"><i class="fas fa-star"></i> Featured</span>';
            }
            document.getElementById('portfolio-badges-container').innerHTML = badgesHtml;

            // Meta
            let metaHtml = '';
            metaHtml += '<span><i class="far fa-images"></i> ' + p.images.length + ' Photos</span>';
            if (p.location) {
                metaHtml += '<span><i class="fas fa-map-marker-alt"></i> ' + p.location + '</span>';
            }
            document.getElementById('portfolio-meta-container').innerHTML = metaHtml;

            // Highlights
            let highlightsHtml = '';
            if (p.highlights) {
                const tags = p.highlights.split(',').filter(Boolean);
                tags.forEach(t => {
                    highlightsHtml += '<span style="background: var(--hub-slate-100); color: var(--hub-slate-600); padding: 4px 10px; border-radius: 100px; font-size: 0.75rem; font-weight: 600;">' + t.trim() + '</span>';
                });
            }
            document.getElementById('portfolio-highlights').innerHTML = highlightsHtml;

            // Gallery
            currentPortfolioImages = p.images;
            currentImageIndex = 0;
            updatePortfolioImage();

            document.getElementById('portfolio-view-modal').classList.add('active');
            document.body.style.overflow = 'hidden';
        };

        window.closePortfolioViewModal = function() {
            document.getElementById('portfolio-view-modal').classList.remove('active');
            document.body.style.overflow = '';
        };

        function updatePortfolioImage() {
            if (currentPortfolioImages.length === 0) return;
            document.getElementById('portfolio-main-img').src = currentPortfolioImages[currentImageIndex];
            
            // Toggle buttons
            document.getElementById('portfolio-prev-btn').style.display = currentPortfolioImages.length > 1 ? 'block' : 'none';
            document.getElementById('portfolio-next-btn').style.display = currentPortfolioImages.length > 1 ? 'block' : 'none';
        }

        document.getElementById('portfolio-prev-btn').addEventListener('click', function(e) {
            e.stopPropagation();
            if (currentPortfolioImages.length === 0) return;
            currentImageIndex = (currentImageIndex - 1 + currentPortfolioImages.length) % currentPortfolioImages.length;
            updatePortfolioImage();
        });

        document.getElementById('portfolio-next-btn').addEventListener('click', function(e) {
            e.stopPropagation();
            if (currentPortfolioImages.length === 0) return;
            currentImageIndex = (currentImageIndex + 1) % currentPortfolioImages.length;
            updatePortfolioImage();
        });

        window.openCategoryModal = function(cat) {
            const modal = document.getElementById('dish-cat-modal');
            const title = document.getElementById('dish-modal-cat-title');
            const body  = document.getElementById('dish-modal-body');
            const items = window.hubMenuItems.filter(i => i.category === cat);
            title.textContent = cat + ' (' + items.length + ' dish' + (items.length !== 1 ? 'es' : '') + ')';

            const DIET_ICONS = { 'Vegetarian': '🌿', 'Vegan': '🌱', 'Halal': '✡️', 'Gluten-Free': '🌾' };
            const UNIT_MAP = {
                'per_serving': '', 'per_tray': ' / Tray', 'per_bilao': ' / Bilao',
                'per_pax': ' / Pax', 'per_hour': ' / Hr', 'per_unit': ' / Unit', 'per_set': ' / Set',
                'per_kg': ' / Kg', 'whole': ' / Whole'
            };

            body.innerHTML = items.map(item => {
                const img = item.image || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=200';
                const unitSuffix = item.pricing_unit ? (UNIT_MAP[item.pricing_unit] || '') : '';
                let priceDisplay = '';
                if (item.pricing_type === 'weight_based' && item.weight_prices && item.weight_prices.length > 0) {
                    priceDisplay = '<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:2px;">' + item.weight_prices.map(wp => `<span style="font-size:0.75rem;font-weight:800;color:var(--hub-brand);background:var(--hub-brand-light);padding:2px 6px;border-radius:4px;">₱${parseFloat(wp.price).toLocaleString('en-PH', {minimumFractionDigits:0})} <span style="font-size:0.65rem;color:var(--hub-slate-400);">/${wp.weight_label}</span></span>`).join('') + '</div>';
                } else if (item.pricing_type === 'size_based' && item.size_prices && item.size_prices.length > 0) {
                    priceDisplay = '<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:2px;">' + item.size_prices.map(sp => `<span style="font-size:0.75rem;font-weight:800;color:var(--hub-brand);background:var(--hub-brand-light);padding:2px 6px;border-radius:4px;">₱${parseFloat(sp.price).toLocaleString('en-PH', {minimumFractionDigits:0})} <span style="font-size:0.65rem;color:var(--hub-slate-400);">/${sp.size_name}</span></span>`).join('') + '</div>';
                } else {
                    priceDisplay = item.price > 0
                        ? '\u20b1' + parseFloat(item.price).toLocaleString('en-PH', {minimumFractionDigits:2}) + unitSuffix
                        : '<span style="font-size:0.78rem;font-weight:700;color:var(--hub-slate-400);">Included in Package</span>';
                }
                
                const isSelected = window.selectedItems.some(s => String(s.id) === String(item.id) && (s.type ? s.type === 'Menu' : true));

                const dietHtml = (item.dietary_tags && item.dietary_tags.length > 0)
                    ? item.dietary_tags.map(t => `<span style="font-size:0.65rem;background:#f0fdf4;color:#15803d;border:1px solid #bbf7d0;border-radius:100px;padding:2px 8px;font-weight:700;">${DIET_ICONS[t]||''} ${t}</span>`).join('')
                    : '';

                const allergenHtml = (item.allergen_info && item.allergen_info.length > 0)
                    ? `<span style="font-size:0.65rem;background:#fff7ed;color:#c2410c;border:1px solid #fed7aa;border-radius:100px;padding:2px 8px;font-weight:700;">⚠️ Contains: ${item.allergen_info.join(', ')}</span>`
                    : '';

                const servingHtml = item.serving_size
                    ? `<span style="font-size:0.65rem;color:var(--hub-slate-400);font-weight:600;">${item.serving_size}</span>`
                    : '';

                const descHtml = item.description
                    ? `<div style="font-size:0.72rem;color:var(--hub-slate-400);line-height:1.5;margin-top:2px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;">${item.description}</div>`
                    : '';

                const tagsHtml = (dietHtml || allergenHtml || servingHtml)
                    ? `<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:4px;">${servingHtml}${dietHtml}${allergenHtml}</div>`
                    : '';

                return `
                <div class="dish-row" id="dish-row-${item.id}">
                    <img src="${img}" class="dish-row-img" alt="${item.name}" loading="lazy"
                         onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=200'">
                    <div class="dish-row-info">
                        <div class="dish-row-name">${item.name}</div>
                        <div class="dish-row-price">${priceDisplay}</div>
                        ${descHtml}
                        ${tagsHtml}
                    </div>
                    <div class="dish-row-action">
                        <input type="number" class="dish-row-qty" id="mq-${item.id}" value="1" min="1"
                               ${isSelected ? 'disabled' : ''}>
                        <button type="button"
                            class="dish-row-btn ${isSelected ? 'selected' : ''}"
                            id="mbtn-${item.id}"
                            onclick="window.toggleModalItem(${item.id})">
                            ${isSelected ? (cat === 'Rentals' ? 'Rented ✓' : 'Added ✓') : (cat === 'Rentals' ? 'Rent' : 'Add')}
                        </button>
                    </div>
                </div>`;
            }).join('');

            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        };

        window.closeDishModal = function() {
            document.getElementById('dish-cat-modal').classList.remove('active');
            document.body.style.overflow = '';
        };

        window.openInventoryModal = function(cat) {
            const modal = document.getElementById('dish-cat-modal');
            const title = document.getElementById('dish-modal-cat-title');
            const body  = document.getElementById('dish-modal-body');
            const items = window.hubInventoryItems.filter(i => i.category === cat);
            title.textContent = cat + ' (' + items.length + ' item' + (items.length !== 1 ? 's' : '') + ')';

            body.innerHTML = items.map(item => {
                const img = item.image || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=200';
                const unitSuffix = item.pricing_unit ? ' / ' + item.pricing_unit : '';
                const priceDisplay = item.price > 0
                    ? '\u20b1' + parseFloat(item.price).toLocaleString('en-PH', {minimumFractionDigits:2}) + unitSuffix
                    : '<span style="font-size:0.78rem;font-weight:700;color:var(--hub-slate-400);">Contact for Price</span>';
                const isSelected = window.selectedItems.some(s => String(s.id) === String(item.id) && s.type === item.type);

                const descHtml = item.description
                    ? `<div style="font-size:0.72rem;color:var(--hub-slate-400);line-height:1.5;margin-top:2px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;">${item.description}</div>`
                    : '';

                return `
                <div class="dish-row" id="dish-row-${item.id}">
                    <img src="${img}" class="dish-row-img" alt="${item.name}" loading="lazy"
                         onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=200'">
                    <div class="dish-row-info">
                        <div class="dish-row-name">${item.name}</div>
                        <div class="dish-row-price">${priceDisplay}</div>
                        ${descHtml}
                    </div>
                    <div class="dish-row-action">
                        <input type="number" class="dish-row-qty" id="mq-${item.type}-${item.id}" value="1" min="1"
                               ${isSelected ? 'disabled' : ''}>
                        <button type="button"
                            class="dish-row-btn ${isSelected ? 'selected' : ''}"
                            id="mbtn-${item.type}-${item.id}"
                            onclick="window.toggleInventoryModalItem(${item.id}, '${item.type}')">
                            ${isSelected ? (item.type === 'Equipment' ? 'Rented ✓' : 'Added ✓') : (item.type === 'Equipment' ? 'Rent' : 'Add')}
                        </button>
                    </div>
                </div>`;
            }).join('');

            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        };

        // ── toggleModalItem ──────────────────────────────────────────────
        // SAFE: only passes numeric ID, looks up name/price from hubMenuItems
        window.toggleModalItem = function(id) {
            const sid = String(id);
            // Look up the full item object
            const menuItem = window.hubMenuItems
                ? window.hubMenuItems.find(i => String(i.id) === sid)
                : null;

            const idx = window.selectedItems.findIndex(i => String(i.id) === sid);
            const btn = document.getElementById('mbtn-' + sid);
            const qty = document.getElementById('mq-' + sid);
            const qtyVal = qty ? (Math.max(1, parseInt(qty.value) || 1)) : 1;

            if (idx === -1) {
                // Validate: max qty
                if (qtyVal < 1 || qtyVal > 999) {
                    alert('Please enter a valid quantity (1–999).');
                    return;
                }
                window.selectedItems.push({
                    id: sid,
                    type: 'Menu',
                    name: menuItem ? menuItem.name : 'Item #' + sid,
                    price: menuItem ? (parseFloat(menuItem.price) || 0) : 0,
                    qty: qtyVal
                });
                if (btn) { btn.classList.add('selected'); btn.textContent = (menuItem && menuItem.category === 'Rentals') ? 'Rented ✓' : 'Added ✓'; }
                if (qty) qty.disabled = true;
            } else {
                // Toggle off
                window.selectedItems.splice(idx, 1);
                if (btn) { btn.classList.remove('selected'); btn.textContent = (menuItem && menuItem.category === 'Rentals') ? 'Rent' : 'Add'; }
                if (qty) { qty.disabled = false; qty.value = 1; }
            }

            // Force drawer visible with !important
            const drawer = document.querySelector('.order-drawer');
            if (drawer) {
                drawer.style.setProperty(
                    'display',
                    window.selectedItems.length > 0 ? 'block' : 'none',
                    'important'
                );
            }
            window.updateCartUI();
        // ── toggleInventoryModalItem ─────────────────────────────────────────
        window.toggleInventoryModalItem = function(id, type) {
            const sid = String(id);
            const menuItem = window.hubInventoryItems
                ? window.hubInventoryItems.find(i => String(i.id) === sid && i.type === type)
                : null;

            const idx = window.selectedItems.findIndex(i => String(i.id) === sid && i.type === type);
            const btn = document.getElementById(`mbtn-${type}-${sid}`);
            const qty = document.getElementById(`mq-${type}-${sid}`);
            const qtyVal = qty ? (Math.max(1, parseInt(qty.value) || 1)) : 1;

            if (idx === -1) {
                if (qtyVal < 1 || qtyVal > 999) {
                    alert('Please enter a valid quantity (1–999).');
                    return;
                }
                window.selectedItems.push({
                    id: sid,
                    type: type,
                    name: menuItem ? menuItem.name : type + ' #' + sid,
                    price: menuItem ? (parseFloat(menuItem.price) || 0) : 0,
                    qty: qtyVal
                });
                if (btn) { btn.classList.add('selected'); btn.textContent = (type === 'Equipment') ? 'Rented ✓' : 'Added ✓'; }
                if (qty) qty.disabled = true;
            } else {
                window.selectedItems.splice(idx, 1);
                if (btn) { btn.classList.remove('selected'); btn.textContent = (type === 'Equipment') ? 'Rent' : 'Add'; }
                if (qty) { qty.disabled = false; qty.value = 1; }
            }

            const drawer = document.querySelector('.order-drawer');
            if (drawer) {
                drawer.style.setProperty(
                    'display',
                    window.selectedItems.length > 0 ? 'block' : 'none',
                    'important'
                );
            }
            window.updateCartUI();
        };
    