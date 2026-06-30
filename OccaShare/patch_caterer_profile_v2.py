import os

file_path = r"c:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

rules_html_updated = """
              <!-- SCHEDULING & AVAILABILITY STATUS -->
              <div class="elite-sidebar" style="margin-top: 1rem;">
                  <h4 style="font-size: 0.75rem; font-weight: 800; color: var(--hub-slate-400); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem;">
                      Operating Hours & Policies
                  </h4>
                  {% set rules = caterer.scheduling_rules or {} %}
                  {% set bh = rules.get('business_hours', {'open_time': '08:00', 'close_time': '20:00'}) %}
                  {% set fr = rules.get('food_rules', {'lead_time_hours': 24}) %}
                  {% set er = rules.get('equipment_rules', {'min_rental_hours': 24}) %}
                  {% set sr = rules.get('service_rules', {'min_duration_hours': 3}) %}
                  
                  <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1rem; margin-bottom: 10px;">
                      <div style="font-size: 0.8rem; font-weight: 700; color: #475569; margin-bottom: 8px;">
                          <i class="fas fa-clock" style="margin-right: 5px; color: var(--hub-primary);"></i> Business Hours
                      </div>
                      <div style="font-size: 0.9rem; font-weight: 850; color: #0f172a;">
                          {{ bh.open_time }} - {{ bh.close_time }}
                      </div>
                  </div>

                  <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 1rem; margin-bottom: 10px;">
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

                  <div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: 12px; padding: 1rem;">
                      <div style="font-size: 0.8rem; font-weight: 700; color: #92400e; margin-bottom: 8px;">
                          <i class="fas fa-boxes-stacked" style="margin-right: 5px;"></i> Rentals & Services
                      </div>
                      <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px dashed #fcd34d; padding-bottom:0.5rem; margin-bottom:0.5rem;">
                        <span style="font-size:0.75rem; color:#78350f; font-weight:600;">Min. Rental Duration</span>
                        <span style="font-size:0.8rem; color:#78350f; font-weight:800;">{{ er.min_rental_hours }} hrs</span>
                      </div>
                      <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:0.75rem; color:#78350f; font-weight:600;">Min. Staff Service</span>
                        <span style="font-size:0.8rem; color:#78350f; font-weight:800;">{{ sr.min_duration_hours }} hrs</span>
                      </div>
                  </div>
              </div>
"""

old_rules_html = """
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

content = content.replace(old_rules_html.strip(), rules_html_updated.strip())

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated scheduling rules in profile.")
