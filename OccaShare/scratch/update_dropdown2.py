import codecs

file_path = 'c:\\OccaServe\\OccaShare\\templates\\customer\\item_details_page.html'
with codecs.open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_html = """                <div style="margin-top: 0.5rem;">
                    <div style="font-size: 0.95rem; font-weight: 700; color: var(--hub-text-dark); margin-bottom: 0.75rem;">Choose Option</div>
                    <div class="variant-list">
                        {% if item.pricing_type == 'weight_based' and item.weight_prices %}
                            {% for wp in item.weight_prices %}
                                <input type="radio" name="variant" id="var_{{ loop.index }}" class="variant-input" value="{{ wp.weight_label }}|{{ wp.price }}" onchange="updateCalculations()" {% if loop.first %}checked{% endif %}>
                                <label for="var_{{ loop.index }}" class="variant-label">
                                    <div class="variant-info">
                                        <div class="variant-radio"></div>
                                        <span class="variant-name">{{ wp.weight_label }}</span>
                                    </div>
                                    <div class="variant-price-tag">₱{{ "{:,.0f}".format(wp.price) }}</div>
                                </label>
                            {% endfor %}
                        {% elif item.pricing_type == 'size_based' and item.size_prices %}
                            {% for sp in item.size_prices %}
                                <input type="radio" name="variant" id="var_{{ loop.index }}" class="variant-input" value="{{ sp.size_name }}|{{ sp.price }}" onchange="updateCalculations()" {% if loop.first %}checked{% endif %}>
                                <label for="var_{{ loop.index }}" class="variant-label">
                                    <div class="variant-info">
                                        <div class="variant-radio"></div>
                                        <span class="variant-name">{{ sp.size_name }}</span>
                                    </div>
                                    <div class="variant-price-tag">₱{{ "{:,.0f}".format(sp.price) }}</div>
                                </label>
                            {% endfor %}
                        {% endif %}
                    </div>
                </div>"""

new_html = """                <div style="margin-top: 0.5rem;">
                    <div style="font-size: 0.95rem; font-weight: 700; color: var(--hub-text-dark); margin-bottom: 0.75rem;">Choose Option</div>
                    <select name="variant" id="variant-select" class="control-pro" onchange="updateCalculations()" style="width: 100%; padding: 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 0.95rem; font-weight: 600; color: #0f172a; cursor: pointer; appearance: auto; background: white;">
                        {% if item.pricing_type == 'weight_based' and item.weight_prices %}
                            {% for wp in item.weight_prices %}
                                <option value="{{ wp.weight_label }}|{{ wp.price }}">{{ wp.weight_label }} - ₱{{ "{:,.0f}".format(wp.price) }}</option>
                            {% endfor %}
                        {% elif item.pricing_type == 'size_based' and item.size_prices %}
                            {% for sp in item.size_prices %}
                                <option value="{{ sp.size_name }}|{{ sp.price }}">{{ sp.size_name }} - ₱{{ "{:,.0f}".format(sp.price) }}</option>
                            {% endfor %}
                        {% endif %}
                    </select>
                </div>"""

content = content.replace(old_html, new_html)

# Now fix the JavaScript updateCalculations!
old_js = """    function updateCalculations() {
        let basePrice = {{ item.price if item.price else 0 }};
        {% if catalog_type == 'menu' and (item.pricing_type == 'weight_based' or item.pricing_type == 'size_based') %}
            const sel = document.querySelector('input[name="variant"]:checked');
            if (sel) {
                const parts = sel.value.split('|');
                if (parts.length === 2) {
                    basePrice = parseFloat(parts[1]);
                }
            }
        {% elif catalog_type != 'menu' %}
            basePrice = {{ item.display_price if item.display_price else 0 }};
        {% endif %}"""

new_js = """    function updateCalculations() {
        let basePrice = {{ item.price if item.price else 0 }};
        {% if catalog_type == 'menu' and (item.pricing_type == 'weight_based' or item.pricing_type == 'size_based') %}
            const sel = document.getElementById('variant-select');
            if (sel && sel.value) {
                const parts = sel.value.split('|');
                if (parts.length === 2) {
                    basePrice = parseFloat(parts[1]);
                }
            }
        {% elif catalog_type != 'menu' %}
            basePrice = {{ item.display_price if item.display_price else 0 }};
        {% endif %}"""

content = content.replace(old_js, new_js)

# And fix toggleCartItem/addToCart JavaScript
old_cart_js = """        {% if catalog_type == 'menu' %}
            {% if item.pricing_type == 'weight_based' or item.pricing_type == 'size_based' %}
                const sel = document.querySelector('input[name="variant"]:checked');
                if(!sel){ alert("Please select an option."); return; }
                const parts = sel.value.split('|');
                cartItem.variant_name = parts[0];
                cartItem.price = parseFloat(parts[1]);
            {% else %}
                cartItem.price = {{ item.price if item.price else 0 }};
            {% endif %}"""

new_cart_js = """        {% if catalog_type == 'menu' %}
            {% if item.pricing_type == 'weight_based' or item.pricing_type == 'size_based' %}
                const sel = document.getElementById('variant-select');
                if(!sel || !sel.value){ alert("Please select an option."); return; }
                const parts = sel.value.split('|');
                cartItem.variant_name = parts[0];
                cartItem.price = parseFloat(parts[1]);
            {% else %}
                cartItem.price = {{ item.price if item.price else 0 }};
            {% endif %}"""

content = content.replace(old_cart_js, new_cart_js)

with codecs.open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
