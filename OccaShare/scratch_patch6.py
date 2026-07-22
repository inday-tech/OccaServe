import re

filepath = r'c:\OccaServe\OccaShare\templates\caterer\profile.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the map callback to use block body instead of implicit return
old_map_start = """        } else {
            grid.innerHTML = dishes.map(item => `"""
new_map_start = """        } else {
            grid.innerHTML = dishes.map(item => {
                let initialCap = item.serving_size === 'Single' ? '1 Pax' : (String(item.serving_size).toLowerCase().includes('pax') ? item.serving_size : item.serving_size + ' Pax');
                if (item.variants && item.variants.length > 0) {
                    let vc = item.variants[0].serving_capacity;
                    if (vc) initialCap = String(vc).toLowerCase().includes('pax') ? vc : vc + ' Pax';
                } else if (item.size_prices && item.size_prices.length > 0) {
                    let sc = item.size_prices[0].capacity;
                    if (sc) initialCap = String(sc).toLowerCase().includes('pax') ? sc : sc + ' Pax';
                }
                
                return `"""
content = content.replace(old_map_start, new_map_start)

# Add ID to badge and replace initial cap rendering
old_badge = """                        <div class="absolute top-3 right-3">
                            <span class="bg-white/90 backdrop-blur px-2.5 py-1 rounded-full text-[9px] font-black text-primary uppercase tracking-wider shadow-sm">
                                <i class="fas fa-users"></i> ${item.serving_size === 'Single' ? '1 Pax' : (String(item.serving_size).toLowerCase().includes('pax') ? item.serving_size : item.serving_size + ' Pax')}
                            </span>
                        </div>"""
new_badge = """                        <div class="absolute top-3 right-3">
                            <span id="badge-${item.id}" class="bg-white/90 backdrop-blur px-2.5 py-1 rounded-full text-[9px] font-black text-primary uppercase tracking-wider shadow-sm">
                                <i class="fas fa-users"></i> ${initialCap}
                            </span>
                        </div>"""
content = content.replace(old_badge, new_badge)

# Update dropdown logic with onchange and data-capacity
old_dropdown_logic = """                        ${(item.variants && item.variants.length > 0)
                    ? `<select class="mt-auto text-[10px] font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 outline-none w-full text-center">` + item.variants.map(v => `<option value="${v.price}" ${v.status !== 'available' ? 'disabled' : ''}>${v.status !== 'available' ? '[UNAVAILABLE] ' : ''}₱${parseFloat(v.price).toLocaleString()} - ${v.variant_name} ${v.measurement ? '('+v.measurement+')' : ''} ${v.serving_capacity ? ' | Good for '+v.serving_capacity : ''}</option>`).join('') + `</select>`
                    : (item.pricing_type === 'weight_based' && item.weight_prices && item.weight_prices.length > 0)
                        ? `<select class="mt-auto text-[10px] font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 outline-none w-full text-center">` + item.weight_prices.map(wp => `<option value="${wp.price}">₱${parseFloat(wp.price).toLocaleString()} / ${wp.weight_label}</option>`).join('') + `</select>`
                        : (item.pricing_type === 'size_based' && item.size_prices && item.size_prices.length > 0)
                            ? `<select class="mt-auto text-[10px] font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 outline-none w-full text-center">` + item.size_prices.map(sp => `<option value="${sp.price}">₱${parseFloat(sp.price).toLocaleString()} / ${sp.size_name} ${sp.capacity ? '(Good for '+sp.capacity+')' : ''}</option>`).join('') + `</select>`
                            : (item.price > 0 ? `<div class="text-primary font-black text-sm bg-primary/5 px-3 py-1 rounded-full border border-primary/10 mt-auto">₱${parseFloat(item.price).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>` : `<div class="text-slate-500 font-bold text-[10px] bg-slate-100 px-3 py-1 rounded-full mt-auto border border-slate-200">Price Varies / TBD</div>`)
                }"""

new_dropdown_logic = """                        ${(item.variants && item.variants.length > 0)
                    ? `<select onchange="const b = document.getElementById('badge-${item.id}'); if(b) b.innerHTML = '<i class=\\'fas fa-users\\'></i> ' + this.options[this.selectedIndex].getAttribute('data-capacity');" class="mt-auto text-[10px] font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 outline-none w-full text-center">` + item.variants.map(v => { let cap = v.serving_capacity ? (String(v.serving_capacity).toLowerCase().includes('pax') ? v.serving_capacity : v.serving_capacity + ' Pax') : initialCap; return `<option value="${v.price}" data-capacity="${cap}" ${v.status !== 'available' ? 'disabled' : ''}>${v.status !== 'available' ? '[UNAVAILABLE] ' : ''}₱${parseFloat(v.price).toLocaleString()} - ${v.variant_name} ${v.measurement ? '('+v.measurement+')' : ''} ${v.serving_capacity ? ' | Good for '+v.serving_capacity : ''}</option>`; }).join('') + `</select>`
                    : (item.pricing_type === 'weight_based' && item.weight_prices && item.weight_prices.length > 0)
                        ? `<select onchange="const b = document.getElementById('badge-${item.id}'); if(b) b.innerHTML = '<i class=\\'fas fa-users\\'></i> ' + this.options[this.selectedIndex].getAttribute('data-capacity');" class="mt-auto text-[10px] font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 outline-none w-full text-center">` + item.weight_prices.map(wp => `<option value="${wp.price}" data-capacity="${initialCap}">₱${parseFloat(wp.price).toLocaleString()} / ${wp.weight_label}</option>`).join('') + `</select>`
                        : (item.pricing_type === 'size_based' && item.size_prices && item.size_prices.length > 0)
                            ? `<select onchange="const b = document.getElementById('badge-${item.id}'); if(b) b.innerHTML = '<i class=\\'fas fa-users\\'></i> ' + this.options[this.selectedIndex].getAttribute('data-capacity');" class="mt-auto text-[10px] font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 outline-none w-full text-center">` + item.size_prices.map(sp => { let cap = sp.capacity ? (String(sp.capacity).toLowerCase().includes('pax') ? sp.capacity : sp.capacity + ' Pax') : initialCap; return `<option value="${sp.price}" data-capacity="${cap}">₱${parseFloat(sp.price).toLocaleString()} / ${sp.size_name} ${sp.capacity ? '(Good for '+sp.capacity+')' : ''}</option>`; }).join('') + `</select>`
                            : (item.price > 0 ? `<div class="text-primary font-black text-sm bg-primary/5 px-3 py-1 rounded-full border border-primary/10 mt-auto">₱${parseFloat(item.price).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>` : `<div class="text-slate-500 font-bold text-[10px] bg-slate-100 px-3 py-1 rounded-full mt-auto border border-slate-200">Price Varies / TBD</div>`)
                }"""
content = content.replace(old_dropdown_logic, new_dropdown_logic)

# Finalize the map string end: replace `).join('');` with `}).join('');`
# We need to find the specific ending. It's after the closing backtick.
old_end = """                        <button onclick="promptBookingAuth()" class="mt-2 w-full text-[10px] font-bold text-white bg-primary rounded-full py-1.5 transition hover:bg-primary/90 shadow-sm uppercase tracking-widest"><i class="fas ${categoryName === 'Rentals' ? 'fa-box' : (categoryName === 'Services' ? 'fa-calendar-check' : 'fa-cart-plus')}"></i> ${categoryName === 'Rentals' ? 'Rent' : (categoryName === 'Services' ? 'Book' : 'Order')}</button>
                    </div>
                </div>
            `).join('');
        }"""
new_end = """                        <button onclick="promptBookingAuth()" class="mt-2 w-full text-[10px] font-bold text-white bg-primary rounded-full py-1.5 transition hover:bg-primary/90 shadow-sm uppercase tracking-widest"><i class="fas ${categoryName === 'Rentals' ? 'fa-box' : (categoryName === 'Services' ? 'fa-calendar-check' : 'fa-cart-plus')}"></i> ${categoryName === 'Rentals' ? 'Rent' : (categoryName === 'Services' ? 'Book' : 'Order')}</button>
                    </div>
                </div>
            `;
            }).join('');
        }"""
content = content.replace(old_end, new_end)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patch 6 applied.")
