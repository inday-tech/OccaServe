import codecs

file_path = 'c:\\OccaServe\\OccaShare\\app\\routers\\customer_dashboard.py'
with codecs.open(file_path, 'r', 'utf-8') as f:
    lines = f.readlines()

new_lines = []
skip_next = False
for i, line in enumerate(lines):
    if skip_next:
        skip_next = False
        continue

    if '    # Check for previous relationship' in line:
        new_lines.append('    # Force DB Refresh to prevent stale data\n')
        new_lines.append('    db.refresh(caterer)\n\n')

    if '"nav_page": "caterers"' in line:
        new_lines.append(line)
        new_lines.append('    })\n')
        new_lines.append('    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"\n')
        new_lines.append('    return response\n')
        skip_next = True # skip the next line which is '    })'
        continue
    
    if '    return templates.TemplateResponse("customer/caterer_profile_view.html", {' in line:
        new_lines.append('    response = templates.TemplateResponse("customer/caterer_profile_view.html", {\n')
        continue
        
    new_lines.append(line)

with codecs.open(file_path, 'w', 'utf-8') as f:
    f.writelines(new_lines)
