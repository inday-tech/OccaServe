import os
import re
import glob

app_dir = r"C:\OccaServe\OccaShare\app"

# Find all python files
py_files = glob.glob(os.path.join(app_dir, "**", "*.py"), recursive=True)
js_files = glob.glob(os.path.join(app_dir, "**", "*.js"), recursive=True)
html_files = glob.glob(os.path.join(app_dir, "**", "*.html"), recursive=True)

all_files = py_files + js_files + html_files

for filepath in all_files:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        original_content = content
        
        # We only do this if we are doing a mass rename, but wait, it might break if MenuItem is used in other contexts.
        # Let's not do mass rename right away.
        pass
        
    except Exception as e:
        pass
