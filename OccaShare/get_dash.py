with open('app/routers/caterer_dashboard.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    start = -1
    for i, line in enumerate(lines):
        if 'def caterer_dashboard(' in line or '@router.get("/caterer/dashboard")' in line or '@router.get("/caterer", ' in line:
            start = i
            break
            
    if start != -1:
        for j in range(start, start+150):
            if j < len(lines):
                print(f'{j+1}: {lines[j].strip()}')
            if 'return templates.TemplateResponse' in lines[j]:
                break
