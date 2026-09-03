import re

with open('templates/caterer/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

js_replacement = '''
            events: '/caterer/api/events',
            eventDidMount: function(info) {
                // Ensure the main element acts as a dot and inherits the background color
                if (info.el.querySelector('.fc-event-main')) {
                    info.el.querySelector('.fc-event-main').style.backgroundColor = info.event.backgroundColor || 'var(--primary-color)';
                }
            },
            dateClick: function(info) {
'''

content = re.sub(
    r"events:\s*'/caterer/api/events',[\s\S]*?dateClick:\s*function\(info\)\s*\{",
    js_replacement.strip() + ' {',
    content
)

with open('templates/caterer/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Added eventDidMount")
