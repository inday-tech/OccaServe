import os
import re

file_path = r"c:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Inject window.catererRules
if "window.catererRules = " not in content:
    content = content.replace(
        "window.hubSwitchTab = function(tabId, btn) {",
        "window.catererRules = {{ (caterer.scheduling_rules or {}) | tojson | safe }};\n        window.hubSwitchTab = function(tabId, btn) {"
    )

# 2. Update serviceHtml
if "const pRules = window.catererRules.package_rules" not in content:
    new_service_html = """
            const pRules = window.catererRules.package_rules || {};
            const prepHtml = (pRules.setup_time_hours || pRules.cleanup_time_hours) ? `
                <div style="display:flex;justify-content:space-between;font-size:0.8rem;padding:0.5rem 0;border-bottom:1px solid var(--hub-slate-100);">
                    <span style="color:var(--hub-slate-400);font-weight:700;">REQUIRED PREP TIME</span>
                    <span style="font-weight:800;color:var(--hub-text-dark);">${pRules.setup_time_hours || 0}h Setup / ${pRules.cleanup_time_hours || 0}h Cleanup</span>
                </div>
            ` : '';

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
                    ${prepHtml}
                    ${addGuestHtml}
                    ${overtimeHtml}
                </div>`;
"""

    old_service_html = """
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
                </div>`;"""

    # We need to exact match the whitespace or use regex.
    content = content.replace(old_service_html.strip(), new_service_html.strip())

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched pkg details.")
else:
    print("Already patched.")
