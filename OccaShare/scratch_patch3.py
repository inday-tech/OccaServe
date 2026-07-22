import re

filepath = r'c:\OccaServe\OccaShare\templates\caterer\profile.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Simple English & Text Size adjustments
content = content.replace('Operation Intel', 'Business Details')
content = content.replace('text-2xl font-black text-slate-800', 'text-xl font-black text-slate-800')
content = content.replace('Culinary Library', 'Menu Selection')
content = content.replace('Visual Portfolio', 'Event Gallery')
content = content.replace('Governance & Terms', 'Policies & Terms')
content = content.replace('Verified Location', 'Location')

# 2. Expert Specialties hover fix
# Remove hover-highlight from tags
content = content.replace(
    'rounded-xl text-[10px] font-black text-brand uppercase tracking-widest flex items-center gap-2 hover-highlight transition-colors',
    'rounded-xl text-[10px] font-black text-brand uppercase tracking-widest flex items-center gap-2 transition-colors'
)
content = content.replace(
    'rounded-xl text-[10px] font-black text-secondary uppercase tracking-widest flex items-center gap-2 hover-highlight transition-colors',
    'rounded-xl text-[10px] font-black text-secondary uppercase tracking-widest flex items-center gap-2 transition-colors'
)

# 3. Menu Item Price and Serving Size Rendering in openCategoryShowcase
# Find the fallback price rendering and replace it
price_render_old = "`<div class=\"text-primary font-black text-sm bg-primary/5 px-3 py-1 rounded-full border border-primary/10 mt-auto\">₱${parseFloat(item.price).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>`"
price_render_new = "(item.price > 0 ? `<div class=\"text-primary font-black text-sm bg-primary/5 px-3 py-1 rounded-full border border-primary/10 mt-auto\">₱${parseFloat(item.price).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>` : `<div class=\"text-slate-500 font-bold text-xs bg-slate-100 px-3 py-1 rounded-full mt-auto border border-slate-200\">Contact for Price</div>`)"
content = content.replace(price_render_old, price_render_new)

# Make sure serving size is shown and clear
serving_size_old = "<i class=\"fas fa-users\"></i> ${item.serving_size}"
serving_size_new = "<i class=\"fas fa-users\"></i> ${item.serving_size === 'Single' ? '1 Pax' : item.serving_size}"
content = content.replace(serving_size_old, serving_size_new)

# 4. Package Modal UI and Sticky X button
old_pkg_modal = """<div class="relative bg-white w-full max-w-3xl max-h-[85vh] overflow-y-auto rounded-3xl shadow-2xl p-8 animate-in zoom-in-95 duration-300 border border-slate-100">
        <button class="absolute top-4 right-4 text-slate-400 hover:text-slate-600" onclick="closePublicPkg()">
            <i class="fas fa-times"></i>
        </button>
        <div id="public-pkg-content"></div>
    </div>"""

new_pkg_modal = """<div class="relative bg-white w-full max-w-3xl max-h-[85vh] flex flex-col rounded-3xl shadow-2xl animate-in zoom-in-95 duration-300 border border-slate-100">
        <button class="absolute top-4 right-4 text-slate-400 hover:text-slate-600 z-10 w-10 h-10 bg-slate-50 rounded-full flex items-center justify-center border border-slate-100 shadow-sm" onclick="closePublicPkg()">
            <i class="fas fa-times text-lg"></i>
        </button>
        <div id="public-pkg-content" class="p-8 overflow-y-auto"></div>
    </div>"""
content = content.replace(old_pkg_modal, new_pkg_modal)

# 5. Package Modal Buttons visibility
old_pkg_btn = """<button onclick="promptBookingAuth()" class="w-full py-3 bg-brand text-white hover:bg-brand/90 rounded-2xl text-xs font-bold transition-all shadow-sm" style="margin-top:0.5rem;display:flex;align-items:center;justify-content:center;gap:8px;">"""
new_pkg_btn = """<button onclick="promptBookingAuth()" class="w-full py-3 rounded-2xl text-xs font-bold transition-all shadow-sm" style="margin-top:0.5rem;display:flex;align-items:center;justify-content:center;gap:8px;background-color:var(--brand-primary);color:#ffffff;border:1px solid rgba(0,0,0,0.1);">"""
content = content.replace(old_pkg_btn, new_pkg_btn)

# Make sure real duration is displayed. The code currently does duration: "{{ pkg.service_duration or 4 }} Hours"
# The string "Hours" might be concatenated in English. I'll change it to hrs.
content = content.replace('duration: "{{ pkg.service_duration or 4 }} Hours"', 'duration: "{{ pkg.service_duration or 4 }} hrs"')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patch 3 applied.")
