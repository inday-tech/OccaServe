with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    print(f"Total lines: {len(lines)}")
    print("Line 1:", lines[0].strip())
    print("Line 4:", lines[3].strip())  # Should be single-line block title

# Verify calendar div is in content block
with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()
    content_start = content.find('{% block content %}')
    content_end = content.find('{% endblock %}', content_start)
    cal_div_pos = content.find("id='calendar'")
    in_content = content_start < cal_div_pos < content_end
    print(f"Calendar div inside content block: {in_content}")
    
    schedule_modal_pos = content.find('id="addScheduleModal"')
    modal_in_content = content_start < schedule_modal_pos < content_end
    print(f"addScheduleModal inside content block: {modal_in_content}")
