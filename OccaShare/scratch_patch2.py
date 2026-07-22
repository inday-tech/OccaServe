import re

filepath = r'c:\OccaServe\OccaShare\templates\caterer\profile.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# For openCategoryShowcase
# Find the mapping inside openCategoryShowcase
# We will inject our new badges into the tags area
# Currently it has:
# ${(item.dietary_tags || []).map(tag => `<span class="text-[8px] font-bold px-2 py-0.5 bg-emerald-50 text-emerald-600 border border-emerald-100 rounded-sm">${tag}</span>`).join('')}
# ${(item.allergen_info || []).map(allergen => `<span class="text-[8px] font-bold px-2 py-0.5 bg-red-50 text-red-600 border border-red-100 rounded-sm">⚠️ ${allergen}</span>`).join('')}

category_badge_injection = """
                            ${(item.dietary_tags || []).map(tag => `<span class="text-[8px] font-bold px-2 py-0.5 bg-emerald-50 text-emerald-600 border border-emerald-100 rounded-sm">${tag}</span>`).join('')}
                            ${(item.allergen_info || []).map(allergen => `<span class="text-[8px] font-bold px-2 py-0.5 bg-red-50 text-red-600 border border-red-100 rounded-sm">⚠️ ${allergen}</span>`).join('')}
                            <span class="text-[8px] font-bold px-2 py-0.5 ${item.status === 'available' ? 'bg-emerald-50 text-emerald-600 border-emerald-100' : 'bg-red-50 text-red-600 border-red-100'} border rounded-sm">${(item.status || 'available').toUpperCase()}</span>
                            ${item.min_order_qty > 1 ? `<span class="text-[8px] font-bold px-2 py-0.5 bg-amber-50 text-amber-600 border border-amber-100 rounded-sm">Min Qty: ${item.min_order_qty}</span>` : ''}
                            ${(catererScheduling && catererScheduling.food_rules && catererScheduling.food_rules.lead_time_hours) ? `<span class="text-[8px] font-bold px-2 py-0.5 bg-blue-50 text-blue-600 border border-blue-100 rounded-sm">Lead: ${catererScheduling.food_rules.lead_time_hours}h</span>` : ''}
"""

content = content.replace(
    "${(item.dietary_tags || []).map(tag => `<span class=\"text-[8px] font-bold px-2 py-0.5 bg-emerald-50 text-emerald-600 border border-emerald-100 rounded-sm\">${tag}</span>`).join('')}\n                            ${(item.allergen_info || []).map(allergen => `<span class=\"text-[8px] font-bold px-2 py-0.5 bg-red-50 text-red-600 border border-red-100 rounded-sm\">⚠️ ${allergen}</span>`).join('')}",
    category_badge_injection.strip()
)

# For openInventoryShowcase
# Current badges:
# ${(item.type === 'Equipment' && item.display_qty) ? `<span class="text-[8px] font-bold px-2 py-0.5 bg-slate-100 text-slate-600 rounded-sm">📦 ${item.display_qty} In Stock</span>` : ''}
# ${item.min_hours ? `<span class="text-[8px] font-bold px-2 py-0.5 bg-slate-100 text-slate-600 rounded-sm">⏱️ Min ${item.min_hours}h</span>` : ''}
# ${item.deposit_pct ? `<span class="text-[8px] font-bold px-2 py-0.5 bg-orange-50 text-orange-600 rounded-sm">🔒 ${item.deposit_pct}% Dep</span>` : ''}

inventory_badge_injection = """
                            ${(item.type === 'Equipment' && item.display_qty) ? `<span class="text-[8px] font-bold px-2 py-0.5 bg-slate-100 text-slate-600 border border-slate-200 rounded-sm">📦 ${item.display_qty} In Stock</span>` : ''}
                            ${item.min_hours ? `<span class="text-[8px] font-bold px-2 py-0.5 bg-slate-100 text-slate-600 border border-slate-200 rounded-sm">⏱️ Min ${item.min_hours}h</span>` : ''}
                            ${item.deposit_pct ? `<span class="text-[8px] font-bold px-2 py-0.5 bg-orange-50 text-orange-600 border border-orange-100 rounded-sm">🔒 ${item.deposit_pct}% Dep</span>` : ''}
                            <span class="text-[8px] font-bold px-2 py-0.5 ${item.status === 'available' ? 'bg-emerald-50 text-emerald-600 border-emerald-100' : 'bg-red-50 text-red-600 border-red-100'} border rounded-sm">${(item.status || 'available').toUpperCase()}</span>
                            ${(item.type === 'Equipment' && catererScheduling && catererScheduling.equipment_rules) ? `<span class="text-[8px] font-bold px-2 py-0.5 bg-blue-50 text-blue-600 border border-blue-100 rounded-sm">Max: ${catererScheduling.equipment_rules.max_rental_hours || 24}h</span>` : ''}
                            ${(item.type === 'Service' && catererScheduling && catererScheduling.service_rules) ? `<span class="text-[8px] font-bold px-2 py-0.5 bg-blue-50 text-blue-600 border border-blue-100 rounded-sm">Max: ${catererScheduling.service_rules.max_duration_hours || 8}h</span>` : ''}
"""

content = content.replace(
    "${(item.type === 'Equipment' && item.display_qty) ? `<span class=\"text-[8px] font-bold px-2 py-0.5 bg-slate-100 text-slate-600 rounded-sm\">📦 ${item.display_qty} In Stock</span>` : ''}\n                            ${item.min_hours ? `<span class=\"text-[8px] font-bold px-2 py-0.5 bg-slate-100 text-slate-600 rounded-sm\">⏱️ Min ${item.min_hours}h</span>` : ''}\n                            ${item.deposit_pct ? `<span class=\"text-[8px] font-bold px-2 py-0.5 bg-orange-50 text-orange-600 rounded-sm\">🔒 ${item.deposit_pct}% Dep</span>` : ''}",
    inventory_badge_injection.strip()
)

# Also fix the opacity classes directly to ensure no elements vanish.
content = content.replace('opacity-0', 'opacity-100')
content = content.replace('group-hover:opacity-100', '')
content = content.replace('group-hover:opacity-0', '')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patch 2 applied.")
