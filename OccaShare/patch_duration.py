import os

file_path = r"c:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace ${pkg.duration} with profile-based duration
# We'll use pRules.max_event_duration or default. 

target_line = '<span style="font-weight:800;color:var(--hub-text-dark);">${pkg.duration}</span>'
replacement_line = '<span style="font-weight:800;color:var(--hub-text-dark);">${pRules.max_event_duration ? pRules.max_event_duration + " hours" : pkg.duration}</span>'

if target_line in content:
    content = content.replace(target_line, replacement_line)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Replaced pkg.duration with profile duration in modal.")
else:
    print("Target line not found or already replaced.")
