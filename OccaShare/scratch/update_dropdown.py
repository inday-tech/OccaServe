import codecs

file_path = 'c:\\OccaServe\\OccaShare\\templates\\customer\\item_details_page.html'
with codecs.open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_html = """                    <div class="variant-grid">
                        {% for variant in item.variants %}
                            {% if variant.status != 'hidden' %}
                                <label class="variant-label {% if variant.status == 'unavailable' %}unavailable{% endif %}">
                                    <input type="radio" name="variant_selection" value="{{ variant.id }}" data-price="{{ variant.price }}" data-name="{{ variant.variant_name }}" {% if variant.status == 'unavailable' %}disabled{% endif %} onchange="updateCalculations()">
                                    <div class="variant-card">
                                        <div class="variant-name">{{ variant.variant_name }}</div>
                                        <div class="variant-price">₱{{ "{:,.0f}".format(variant.price) }}</div>
                                        {% if variant.serving_capacity %}
                                            <div class="variant-serving">{{ variant.serving_capacity }}</div>
                                        {% endif %}
                                    </div>
                                </label>
                            {% endif %}
                        {% endfor %}
                    </div>"""

new_html = """                    <div class="variant-dropdown-container">
                        <select name="variant_selection" class="control-pro variant-dropdown" id="variant-select" onchange="updateCalculations()" style="width: 100%; padding: 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 0.95rem; font-weight: 500; color: #0f172a; cursor: pointer; appearance: auto;">
                            <option value="" disabled selected>-- Select an Option --</option>
                            {% for variant in item.variants %}
                                {% if variant.status != 'hidden' %}
                                    <option value="{{ variant.id }}" data-price="{{ variant.price }}" data-name="{{ variant.variant_name }}" {% if variant.status == 'unavailable' %}disabled{% endif %}>
                                        {{ variant.variant_name }} - ₱{{ "{:,.0f}".format(variant.price) }} {% if variant.serving_capacity %}({{ variant.serving_capacity }}){% endif %} {% if variant.status == 'unavailable' %}[Unavailable]{% endif %}
                                    </option>
                                {% endif %}
                            {% endfor %}
                        </select>
                    </div>"""

content = content.replace(old_html, new_html)

# Now, need to update JS updateCalculations() to read from the dropdown instead of radio inputs
js_old = """    if (HAS_VARIANTS) {
        const selected = document.querySelector('input[name="variant_selection"]:checked');
        if (!selected) {
            priceDisplay.innerHTML = `<span style="font-size: 0.9rem; color: #64748b;">Select an option above</span>`;
            document.getElementById('subtotal-display').innerText = '₱0';
            btn.disabled = true;
            return;
        }
        basePrice = parseFloat(selected.dataset.price) || 0;
        priceDisplay.innerHTML = `₱${basePrice.toLocaleString()}`;
    }"""

js_new = """    if (HAS_VARIANTS) {
        const select = document.getElementById('variant-select');
        const selectedOption = select.options[select.selectedIndex];
        
        if (!selectedOption || !selectedOption.value) {
            priceDisplay.innerHTML = `<span style="font-size: 0.9rem; color: #64748b;">Select an option above</span>`;
            document.getElementById('subtotal-display').innerText = '₱0';
            btn.disabled = true;
            return;
        }
        basePrice = parseFloat(selectedOption.dataset.price) || 0;
        priceDisplay.innerHTML = `₱${basePrice.toLocaleString()}`;
    }"""
content = content.replace(js_old, js_new)

# Update addToCart() function to use the dropdown
js_cart_old = """        if (HAS_VARIANTS) {
            const selected = document.querySelector('input[name="variant_selection"]:checked');
            if (!selected) {
                alert("Please select a size/variant.");
                return;
            }
            variantId = selected.value;
            variantName = selected.dataset.name;
            basePrice = parseFloat(selected.dataset.price) || 0;
        }"""
        
js_cart_new = """        if (HAS_VARIANTS) {
            const select = document.getElementById('variant-select');
            const selectedOption = select.options[select.selectedIndex];
            if (!selectedOption || !selectedOption.value) {
                alert("Please select a size/variant.");
                return;
            }
            variantId = selectedOption.value;
            variantName = selectedOption.dataset.name;
            basePrice = parseFloat(selectedOption.dataset.price) || 0;
        }"""
content = content.replace(js_cart_old, js_cart_new)


with codecs.open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

