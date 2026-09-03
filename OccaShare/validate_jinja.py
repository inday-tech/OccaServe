from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('templates'))
try:
    env.get_template('caterer/calendar.html')
    print("OK: Jinja2 template parses correctly")
except Exception as e:
    print(f"ERROR: {e}")
