import re

filepath = r'c:\OccaServe\OccaShare\templates\caterer\profile.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Shrink h2 container titles
# Replace `text-xs font-bold text-slate-400 uppercase tracking-[0.2em] mb-8`
# with `text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4`
content = re.sub(
    r'text-xs font-bold text-slate-400 uppercase tracking-\[0\.2em\] mb-[68]',
    'text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4',
    content
)
content = content.replace(
    'text-xs font-bold text-slate-400 uppercase tracking-[0.2em] mb-4',
    'text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4'
)
content = content.replace(
    'text-xs font-bold text-slate-400 uppercase tracking-[0.2em] flex items-center',
    'text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center'
)

# 2. Fix the "Book this Package" button visibility
# It's currently:
# <button onclick="promptBookingAuth()" class="w-full py-3 rounded-2xl text-xs font-bold transition-all shadow-sm" style="margin-top:0.5rem;display:flex;align-items:center;justify-content:center;gap:8px;background-color:var(--brand-primary);color:#ffffff;border:1px solid rgba(0,0,0,0.1);">
# Change it to bg-slate-900 text-white to ensure it's ALWAYS visible regardless of theme colors
old_pkg_btn = r'<button onclick="promptBookingAuth\(\)" class="w-full py-3 rounded-2xl text-xs font-bold transition-all shadow-sm" style="margin-top:0\.5rem;display:flex;align-items:center;justify-content:center;gap:8px;background-color:var\(--brand-primary\);color:#ffffff;border:1px solid rgba\(0,0,0,0\.1\);">\s*<i class="fas fa-calendar-check"></i> Book this Package\s*</button>'
new_pkg_btn = """<button onclick="promptBookingAuth()" class="w-full py-3 bg-slate-900 text-white hover:bg-slate-800 rounded-2xl text-xs font-bold transition-all shadow-sm" style="margin-top:0.5rem;display:flex;align-items:center;justify-content:center;gap:8px;">
                <i class="fas fa-calendar-check"></i> Book this Package
            </button>"""
content = re.sub(old_pkg_btn, new_pkg_btn, content)

# 3. Dropdowns for weight/size based prices
old_weight_render = """'<div class="flex flex-col gap-1 w-full items-center mt-auto">' + item.weight_prices.map(wp => `<div class="text-primary font-bold text-[11px]">₱${parseFloat(wp.price).toLocaleString()} <span class="text-[9px] text-slate-400">/${wp.weight_label}</span></div>`).join('') + '</div>'"""
new_weight_render = """`<select class="mt-auto text-[10px] font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 outline-none w-full text-center">` + item.weight_prices.map(wp => `<option value="${wp.price}">₱${parseFloat(wp.price).toLocaleString()} / ${wp.weight_label}</option>`).join('') + `</select>`"""

old_size_render = """'<div class="flex flex-col gap-1 w-full items-center mt-auto">' + item.size_prices.map(sp => `<div class="text-primary font-bold text-[11px]">₱${parseFloat(sp.price).toLocaleString()} <span class="text-[9px] text-slate-400">/${sp.size_name}</span></div>`).join('') + '</div>'"""
new_size_render = """`<select class="mt-auto text-[10px] font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 outline-none w-full text-center">` + item.size_prices.map(sp => `<option value="${sp.price}">₱${parseFloat(sp.price).toLocaleString()} / ${sp.size_name}</option>`).join('') + `</select>`"""

content = content.replace(old_weight_render, new_weight_render)
content = content.replace(old_size_render, new_size_render)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patch 4 applied.")
