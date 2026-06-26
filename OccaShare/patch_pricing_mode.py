import re
with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix python rendering HTML price
old_price = '''                                {% if pkg.price_unit == 'total' %}
                                <span class="ei-price">₱{{ "{:,.2f}".format(pkg.price if pkg.price else (pkg.price_per_head if pkg.price_per_head else 0)) }}<span style="font-size:0.65rem;font-weight:600;color:var(--hub-slate-400)"> total</span></span>
                                {% else %}
                                <span class="ei-price">₱{{ "{:,.2f}".format(pkg.price_per_head if pkg.price_per_head else (pkg.price if pkg.price else 0)) }}<span style="font-size:0.65rem;font-weight:600;color:var(--hub-slate-400)">/pax</span></span>
                                {% endif %}'''
new_price = '''                                {% if pkg.pricing_mode == 'fixed' or pkg.price_unit == 'total' %}
                                <span class="ei-price">₱{{ "{:,.2f}".format(pkg.price if pkg.price else (pkg.price_per_head if pkg.price_per_head else 0)) }}<span style="font-size:0.65rem;font-weight:600;color:var(--hub-slate-400)"> total</span></span>
                                {% else %}
                                <span class="ei-price">₱{{ "{:,.2f}".format(pkg.price_per_head if pkg.price_per_head else (pkg.price if pkg.price else 0)) }}<span style="font-size:0.65rem;font-weight:600;color:var(--hub-slate-400)">/pax</span></span>
                                {% endif %}'''
content = content.replace(old_price, new_price)

# Fix Javascript rendering price
old_js_price = '''        price: "₱{{ '{:,.2f}'.format(pkg.price if pkg.price else (pkg.price_per_head if pkg.price_per_head else 0)) if pkg.price_unit == 'total' else '{:,.2f}'.format(pkg.price_per_head if pkg.price_per_head else (pkg.price if pkg.price else 0)) }}{{ ' total' if pkg.price_unit == 'total' else '/pax' }}",'''
new_js_price = '''        price: "₱{{ '{:,.2f}'.format(pkg.price if pkg.price else (pkg.price_per_head if pkg.price_per_head else 0)) if (pkg.pricing_mode == 'fixed' or pkg.price_unit == 'total') else '{:,.2f}'.format(pkg.price_per_head if pkg.price_per_head else (pkg.price if pkg.price else 0)) }}{{ ' total' if (pkg.pricing_mode == 'fixed' or pkg.price_unit == 'total') else '/pax' }}",'''
content = content.replace(old_js_price, new_js_price)

with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed package pricing unit check")
