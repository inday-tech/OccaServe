import re

filepath = r'c:\OccaServe\OccaShare\templates\caterer\profile.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Inject `variants` into `menuDishes`
old_inject = """                size_prices: [
                    {% for sp in item.size_prices %}
                    { size_name: {{ sp.size_name|tojson }}, price: {{ sp.price|tojson }}, capacity: {{ (sp.capacity or '')|tojson }} }{{ ',' if not loop.last else '' }}
                    {% endfor %}
                ]
            },"""
new_inject = """                size_prices: [
                    {% for sp in item.size_prices %}
                    { size_name: {{ sp.size_name|tojson }}, price: {{ sp.price|tojson }}, capacity: {{ (sp.capacity or '')|tojson }} }{{ ',' if not loop.last else '' }}
                    {% endfor %}
                ],
                variants: [
                    {% for v in item.variants %}
                    { variant_name: {{ v.variant_name|tojson }}, measurement: {{ (v.measurement or '')|tojson }}, price: {{ v.price|tojson }}, serving_capacity: {{ (v.serving_capacity or '')|tojson }}, status: {{ (v.status or 'available')|tojson }} }{{ ',' if not loop.last else '' }}
                    {% endfor %}
                ]
            },"""
if "variants: [" not in content:
    content = content.replace(old_inject, new_inject)

# 2. Update serving size string
old_serving = "item.serving_size === 'Single' ? '1 Pax' : item.serving_size"
new_serving = "item.serving_size === 'Single' ? '1 Pax' : (String(item.serving_size).toLowerCase().includes('pax') ? item.serving_size : item.serving_size + ' Pax')"
content = content.replace(old_serving, new_serving)

# 3. Update the pricing display logic to use `item.variants` and show unavailable status
# In previous patch, we had:
old_dropdown_logic = """                        ${(item.pricing_type === 'weight_based' && item.weight_prices && item.weight_prices.length > 0)
                    ? `<select class="mt-auto text-[10px] font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 outline-none w-full text-center">` + item.weight_prices.map(wp => `<option value="${wp.price}">₱${parseFloat(wp.price).toLocaleString()} / ${wp.weight_label}</option>`).join('') + `</select>`
                    : (item.pricing_type === 'size_based' && item.size_prices && item.size_prices.length > 0)
                        ? `<select class="mt-auto text-[10px] font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 outline-none w-full text-center">` + item.size_prices.map(sp => `<option value="${sp.price}">₱${parseFloat(sp.price).toLocaleString()} / ${sp.size_name}</option>`).join('') + `</select>`
                        : (item.price > 0 ? `<div class="text-primary font-black text-sm bg-primary/5 px-3 py-1 rounded-full border border-primary/10 mt-auto">₱${parseFloat(item.price).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>` : `<div class="text-slate-500 font-bold text-xs bg-slate-100 px-3 py-1 rounded-full mt-auto border border-slate-200">Contact for Price</div>`)
                }"""

new_dropdown_logic = """                        ${(item.variants && item.variants.length > 0)
                    ? `<select class="mt-auto text-[10px] font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 outline-none w-full text-center">` + item.variants.map(v => `<option value="${v.price}" ${v.status !== 'available' ? 'disabled' : ''}>${v.status !== 'available' ? '[UNAVAILABLE] ' : ''}₱${parseFloat(v.price).toLocaleString()} - ${v.variant_name} ${v.measurement ? '('+v.measurement+')' : ''} ${v.serving_capacity ? ' | Good for '+v.serving_capacity : ''}</option>`).join('') + `</select>`
                    : (item.pricing_type === 'weight_based' && item.weight_prices && item.weight_prices.length > 0)
                        ? `<select class="mt-auto text-[10px] font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 outline-none w-full text-center">` + item.weight_prices.map(wp => `<option value="${wp.price}">₱${parseFloat(wp.price).toLocaleString()} / ${wp.weight_label}</option>`).join('') + `</select>`
                        : (item.pricing_type === 'size_based' && item.size_prices && item.size_prices.length > 0)
                            ? `<select class="mt-auto text-[10px] font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 outline-none w-full text-center">` + item.size_prices.map(sp => `<option value="${sp.price}">₱${parseFloat(sp.price).toLocaleString()} / ${sp.size_name} ${sp.capacity ? '(Good for '+sp.capacity+')' : ''}</option>`).join('') + `</select>`
                            : (item.price > 0 ? `<div class="text-primary font-black text-sm bg-primary/5 px-3 py-1 rounded-full border border-primary/10 mt-auto">₱${parseFloat(item.price).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>` : `<div class="text-slate-500 font-bold text-[10px] bg-slate-100 px-3 py-1 rounded-full mt-auto border border-slate-200">Price Varies / TBD</div>`)
                }"""

# A small fail-safe in case exact whitespace doesn't match:
# Instead of full block replace, I'll use regex for the whole block between `${(` and `}` right before `<button onclick="promptBookingAuth()"`
content = re.sub(
    r'\$\{\(item\.pricing_type === \'weight_based\'.*?Contact for Price</div>`\)\s*\}',
    new_dropdown_logic.strip(),
    content,
    flags=re.DOTALL
)


with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patch 5 applied.")
