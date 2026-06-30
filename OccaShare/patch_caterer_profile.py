import os

file_path = r"c:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

rules_html = """
              <!-- SCHEDULING & AVAILABILITY STATUS -->
              <div class="elite-sidebar" style="margin-top: 1rem;">
                  <h4 style="font-size: 0.75rem; font-weight: 800; color: var(--hub-slate-400); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem;">
                      Operating Hours & Policies
                  </h4>
                  {% set rules = caterer.scheduling_rules or {} %}
                  {% set bh = rules.get('business_hours', {'open_time': '08:00', 'close_time': '20:00'}) %}
                  {% set fr = rules.get('food_rules', {'lead_time_hours': 24}) %}
                  
                  <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1rem; margin-bottom: 10px;">
                      <div style="font-size: 0.8rem; font-weight: 700; color: #475569; margin-bottom: 8px;">
                          <i class="fas fa-clock" style="margin-right: 5px; color: var(--hub-primary);"></i> Business Hours
                      </div>
                      <div style="font-size: 0.9rem; font-weight: 850; color: #0f172a;">
                          {{ bh.open_time }} - {{ bh.close_time }}
                      </div>
                  </div>

                  <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 1rem;">
                      <div style="font-size: 0.8rem; font-weight: 700; color: #166534; margin-bottom: 8px;">
                          <i class="fas fa-truck-fast" style="margin-right: 5px;"></i> Food Order Lead Time
                      </div>
                      <div style="font-size: 0.9rem; font-weight: 850; color: #14532d;">
                          {{ fr.lead_time_hours }} Hours
                      </div>
                      <div style="font-size: 0.7rem; font-weight: 600; color: #166534; margin-top: 4px;">
                          Advanced booking required.
                      </div>
                  </div>
              </div>
"""

target = """                      {% endif %}
                  </div>
              </div>"""

if "<!-- SCHEDULING & AVAILABILITY STATUS -->" not in content:
    content = content.replace(target, target + "\n" + rules_html)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Added to profile.")
else:
    print("Already added.")
