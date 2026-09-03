import re

with open('templates/caterer/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

css_replacement = '''
    /* Style the dots */
    #miniCalendar .fc-daygrid-event-harness { display: inline-block; margin: 0 1px; }
    #miniCalendar .fc-daygrid-event { 
        display: inline-block; 
        background: transparent !important; 
        border: none !important; 
        padding: 0; 
        margin: 0; 
    }
    #miniCalendar .fc-daygrid-event .fc-event-main {
        width: 6px; 
        height: 6px; 
        border-radius: 50%; 
        background-color: var(--primary-color); /* Fallback */
        display: block;
        margin: 0 auto;
    }
    #miniCalendar .fc-daygrid-day-events { 
        display: flex; 
        flex-wrap: wrap; 
        gap: 2px; 
        justify-content: center; 
        margin-top: 2px; 
    }
    #miniCalendar .fc-event-title, #miniCalendar .fc-event-time { display: none !important; }
'''

content = re.sub(r'/\*\s*Style the dots\s*\*/[\s\S]*?(?=</style>)', css_replacement, content)

with open('templates/caterer/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed dot styling")
