import os
import re

file_path = r"c:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """                      <div style="font-size: 0.9rem; font-weight: 850; color: #0f172a;">
                          {{ bh.open_time }} - {{ bh.close_time }}
                      </div>"""

replacement = """                      <div style="font-size: 0.9rem; font-weight: 850; color: #0f172a;" id="biz-hours-display">
                          {{ bh.open_time }} - {{ bh.close_time }}
                      </div>
                      <script>
                          document.addEventListener('DOMContentLoaded', () => {
                              const formatTime = (t) => {
                                  if(!t) return '';
                                  let [h, m] = t.split(':');
                                  let hr = parseInt(h);
                                  let ampm = hr >= 12 ? 'PM' : 'AM';
                                  hr = hr % 12 || 12;
                                  return `${hr}:${m} ${ampm}`;
                              };
                              const el = document.getElementById('biz-hours-display');
                              if(el) {
                                  const raw = el.innerText.split('-');
                                  if(raw.length === 2) {
                                      el.innerText = formatTime(raw[0].trim()) + ' - ' + formatTime(raw[1].trim());
                                  }
                              }
                          });
                      </script>"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched business hours on profile to 12-hour format.")
else:
    print("Could not find target on profile")
