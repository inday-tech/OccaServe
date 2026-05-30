import re

def fix(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Step 1: Remove all {% block modals %}
    content = content.replace('{% block modals %}', '')
    
    # Step 2: Temporarily hide known endblocks we want to keep
    # We want to keep title, extra_css, extra_js
    content = re.sub(r'({% block title %}.*?{% endblock %})', lambda m: m.group(1).replace('{% endblock %}', '__TITLE_END__'), content, flags=re.DOTALL)
    content = re.sub(r'({% block extra_css %}.*?{% endblock %})', lambda m: m.group(1).replace('{% endblock %}', '__CSS_END__'), content, flags=re.DOTALL)
    content = re.sub(r'({% block extra_js %}.*?{% endblock %})', lambda m: m.group(1).replace('{% endblock %}', '__JS_END__'), content, flags=re.DOTALL)
    
    # Now all remaining {% endblock %} belong to content or are duplicates. Remove them all.
    content = re.sub(r'\{%\s*endblock\s*%\}', '', content)
    
    # Put the proper endblock and block modals before Contract View Modal or Balance Upload Modal
    # The first modal is usually <!-- Contract View Modal --> or <!-- Contract Modal --> or <!-- Balance Upload Modal -->
    content = re.sub(r'(<!-- (Contract View|Contract|Balance Upload|Re-upload Downpayment) Modal -->)', r'{% endblock %}\n\n{% block modals %}\n\1', content, count=1)
    
    # Restore the hidden endblocks
    content = content.replace('__TITLE_END__', '{% endblock %}')
    content = content.replace('__CSS_END__', '{% endblock %}')
    content = content.replace('__JS_END__', '{% endblock %}')
    
    # Step 3: Add {% endblock %} before {% block extra_js %}
    content = content.replace('{% block extra_js %}', '{% endblock %}\n\n{% block extra_js %}')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

fix(r'c:\OccaServe\OccaShare\templates\customer\booking_manage.html')
fix(r'c:\OccaServe\OccaShare\templates\customer\booking_manage_package.html')
print('Fixed layout blocks!')
