import re

path = 'templates/customer/caterer_profile_view.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add equipment_turnover_hours to Operational Policies
target = """                        <div class="meta-pill" style="background: var(--hub-slate-50); color: var(--hub-slate-600); justify-content: flex-start; padding: 1rem; border: 1px solid var(--hub-slate-100); height: auto;">
                            <div>
                                <div style="font-size: 0.65rem; text-transform: uppercase; opacity: 0.7;"><i class="fas fa-users" style="margin-right: 4px;"></i> Minimum Guests</div>
                                <div style="font-weight: 850; margin-top: 4px;">Services start for groups of {{ caterer.min_pax if caterer.min_pax else 20 }} pax and above.</div>
                            </div>
                        </div>"""
replacement = """                        <div class="meta-pill" style="background: var(--hub-slate-50); color: var(--hub-slate-600); justify-content: flex-start; padding: 1rem; border: 1px solid var(--hub-slate-100); height: auto;">
                            <div>
                                <div style="font-size: 0.65rem; text-transform: uppercase; opacity: 0.7;"><i class="fas fa-users" style="margin-right: 4px;"></i> Minimum Guests</div>
                                <div style="font-weight: 850; margin-top: 4px;">Services start for groups of {{ caterer.min_pax if caterer.min_pax else 20 }} pax and above.</div>
                            </div>
                        </div>
                        <div class="meta-pill" style="background: var(--hub-slate-50); color: var(--hub-slate-600); justify-content: flex-start; padding: 1rem; border: 1px solid var(--hub-slate-100); height: auto;">
                            <div>
                                <div style="font-size: 0.65rem; text-transform: uppercase; opacity: 0.7;"><i class="fas fa-clock" style="margin-right: 4px;"></i> Equipment Turnover Time</div>
                                <div style="font-weight: 850; margin-top: 4px;">Items require a {{ caterer.equipment_turnover_hours if caterer.equipment_turnover_hours is not none else 24 }} hour cleaning buffer before next rental.</div>
                            </div>
                        </div>"""
content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched caterer_profile_view.html!")
