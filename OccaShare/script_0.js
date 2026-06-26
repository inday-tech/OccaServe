
        // GLOBAL HUB ENGINE (Priority Execution)
        window.hubSwitchTab = function(tabId, btn) {
            console.log('Hub: Switching to', tabId);
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            const target = document.getElementById(tabId);
            if (target) target.classList.add('active');
            if (btn) btn.classList.add('active');
        };

        window.filterMenu = function(cat, btn) {
            document.querySelectorAll('.category-chip').forEach(c => c.classList.remove('active'));
            if (btn) btn.classList.add('active');
            document.querySelectorAll('.menu-item-node').forEach(item => {
                if (cat === 'all' || item.dataset.category === cat) {
                    item.style.display = 'flex';
                } else {
                    item.style.display = 'none';
                }
            });
        };

        window.openPkgDetails = function(id) {
            const pkg = window.hubPkgs ? window.hubPkgs[String(id)] : null;
            if (!pkg) return;

            // Parse inclusions list
            let incList = [];
            try {
                if (pkg.inclusions) {
                    if (Array.isArray(pkg.inclusions)) {
                        // Array of strings — use as-is
                        incList = pkg.inclusions.filter(Boolean);
                    } else if (typeof pkg.inclusions === 'string') {
                        try {
                            const p = JSON.parse(pkg.inclusions);
                            if (Array.isArray(p)) incList = p.filter(Boolean);
                            else if (typeof p === 'object' && p !== null)
                                incList = Object.keys(p).filter(k => p[k] === true || p[k] === 1);
                            else incList = [String(p)];
                        }
                        catch(e) { incList = pkg.inclusions.split(',').map(s => s.trim()).filter(Boolean); }
                    } else if (typeof pkg.inclusions === 'object' && pkg.inclusions !== null) {
                        // JSONB object {"Tables": true, "Chairs": true} — extract enabled keys only
                        incList = Object.keys(pkg.inclusions).filter(k => pkg.inclusions[k] === true || pkg.inclusions[k] === 1);
                    }
                }
            } catch (err) {
                console.error("Error parsing inclusions:", err);
            }
            // Combine legacy inclusions with new linked inventory
            if (pkg.linked_inventory && Array.isArray(pkg.linked_inventory)) {
                pkg.linked_inventory.forEach(item => {
                    if (item && !incList.includes(item)) incList.push(item);
                });
            }

            // Section 1: Service Details
            const paxLabel = pkg.price_unit === 'per_guest' ? '/pax' : ' total';
            const addGuestHtml = pkg.additional_guest_price > 0
                ? `<div style="display:flex;justify-content:space-between;font-size:0.8rem;padding:0.5rem 0;border-bottom:1px solid var(--hub-slate-100);">
                     <span style="color:var(--hub-slate-400);font-weight:700;">EXTRA PAX</span>
                     <span style="font-weight:800;color:var(--hub-text-dark);">₱${pkg.additional_guest_price.toLocaleString('en-PH',{minimumFractionDigits:2})}/person</span>
                   </div>` : '';
            const overtimeHtml = pkg.overtime_fee > 0
                ? `<div style="display:flex;justify-content:space-between;font-size:0.8rem;padding:0.5rem 0;">
                     <span style="color:var(--hub-slate-400);font-weight:700;">OVERTIME</span>
                     <span style="font-weight:800;color:var(--hub-text-dark);">₱${pkg.overtime_fee.toLocaleString('en-PH',{minimumFractionDigits:2})}/hr</span>
                   </div>` : '';

            const serviceHtml = `
                <div style="background:var(--hub-slate-50);border-radius:12px;padding:1rem;border:1px solid var(--hub-slate-100);margin-bottom:1.25rem;">
                    <div style="display:flex;justify-content:space-between;font-size:0.8rem;padding:0.5rem 0;border-bottom:1px solid var(--hub-slate-100);">
                        <span style="color:var(--hub-slate-400);font-weight:700;">GUEST COUNT</span>
                        <span style="font-weight:800;color:var(--hub-text-dark);">
                            ${pkg.min_guests > 0 ? 'Min. '+pkg.min_guests : '—'}${pkg.max_guests > 0 ? ' · Max. '+pkg.max_guests : ''} pax
                        </span>
                    </div>
                    <div style="display:flex;justify-content:space-between;font-size:0.8rem;padding:0.5rem 0;border-bottom:1px solid var(--hub-slate-100);">
                        <span style="color:var(--hub-slate-400);font-weight:700;">SERVICE DURATION</span>
                        <span style="font-weight:800;color:var(--hub-text-dark);">${pkg.duration}</span>
                    </div>
                    ${addGuestHtml}
                    ${overtimeHtml}
                </div>`;

            // Section 2: Equipment & Inclusions
            const incHtml = incList.length > 0 ? `
                <div style="margin-bottom:1.25rem;">
                    <h4 style="font-size:0.72rem;font-weight:800;color:var(--hub-slate-400);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.75rem;">
                        <i class="fas fa-box-open" style="color:var(--hub-primary);margin-right:6px;"></i>Equipment & Services Included
                    </h4>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
                        ${incList.map(inc => `
                            <div style="font-size:0.75rem;color:var(--hub-slate-600);background:#fff;padding:8px 10px;border-radius:8px;border:1px solid var(--hub-slate-100);display:flex;align-items:center;gap:6px;">
                                <i class="fas fa-check-circle" style="color:#10b981;flex-shrink:0;"></i>${inc}
                            </div>`).join('')}
                    </div>
                </div>` : '';

            // Section 3: Included Dishes
            const dishHtml = (pkg.dishes && pkg.dishes.length > 0) ? `
                <div style="margin-bottom:1.25rem;">
                    <h4 style="font-size:0.72rem;font-weight:800;color:var(--hub-slate-400);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.75rem;">
                        <i class="fas fa-utensils" style="color:var(--hub-primary);margin-right:6px;"></i>Dishes Included
                    </h4>
                    <div style="display:flex;flex-wrap:wrap;gap:6px;">
                        ${pkg.dishes.map(d => `<span style="background:var(--hub-slate-50);color:var(--hub-slate-600);padding:4px 12px;border-radius:100px;font-size:0.72rem;font-weight:700;border:1px solid var(--hub-slate-200);">${d}</span>`).join('')}
                    </div>
                </div>` : '';

            const contentHtml = `
                <div style="margin-bottom:1.25rem;">
                    <div style="font-size:0.7rem;font-weight:800;color:var(--hub-primary);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.25rem;">Package Details</div>
                    <h2 style="font-size:1.3rem;font-weight:900;color:var(--hub-text-dark);margin-bottom:0.25rem;">${pkg.name}</h2>
                    <div style="font-size:1.5rem;font-weight:900;color:var(--hub-primary);">${pkg.price}</div>
                </div>
                ${pkg.desc ? `<p style="font-size:0.85rem;color:var(--hub-slate-600);line-height:1.65;margin-bottom:1.25rem;">${pkg.desc}</p>` : ''}
                ${serviceHtml}
                ${incHtml}
                ${dishHtml}
                ${window.catererAvailable
                    ? `<a href="/bookings/start/{{ caterer.id }}?package_id=${id}" class="btn-hub-main" style="margin-top:0.5rem;display:flex;text-align:center;text-decoration:none;"><i class="fas fa-calendar-check"></i> Select this Package</a>`
                    : `<div class="btn-hub-main" style="margin-top:0.5rem;opacity:0.5;cursor:not-allowed;justify-content:center;"><i class="fas fa-ban"></i> Caterer Unavailable</div>`
                }`;

            document.getElementById('pkg-content').innerHTML = contentHtml;
            document.getElementById('pkg-modal').classList.add('active');
        };

        window.closePkgModal = function() { document.getElementById('pkg-modal').classList.remove('active'); };
        
        window.openMessageModal = function() { 
            console.log('Hub: Opening Message Modal');
            document.getElementById('message-modal').classList.add('active'); 
        };
        window.closeMessageModal = function() { document.getElementById('message-modal').classList.remove('active'); };

        window.sendHubMessage = async function(e, recipientId) {
            e.preventDefault();
            console.log('Hub: Sending message');
            const body = document.getElementById('hub-msg-body').value;
            const btn = document.getElementById('hub-send-btn');
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
            try {
                const resp = await fetch('/messages/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ recipient_id: recipientId, content: body })
                });
                if (resp.ok) {
                    alert('Message sent successfully!');
                    window.closeMessageModal();
                    document.getElementById('hub-msg-body').value = '';
                } else { alert('Failed to send message.'); }
            } catch (err) { alert('An error occurred.'); } 
            finally { btn.disabled = false; btn.innerHTML = 'Send Direct Message'; }
        };

    