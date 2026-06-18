import jinja2

template = jinja2.Template("data-dietary-tags='{{ dietary_tags|tojson if dietary_tags else \"[]\" }}'")
print(template.render(dietary_tags=['Vegan', 'Halal']))
