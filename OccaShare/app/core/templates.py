from fastapi.templating import Jinja2Templates
from ..db.database import SessionLocal
from ..db import models

templates = Jinja2Templates(directory="templates")

def get_website_config():
    db = SessionLocal()
    try:
        config = db.query(models.WebsiteConfig).first()
        if not config:
            config = models.WebsiteConfig()
            db.add(config)
            db.commit()
            db.refresh(config)
        return config
    finally:
        db.close()

# Inject the function into the Jinja2 environment globals
# So templates can call it like: {% set config = website_config() %}
templates.env.globals['website_config'] = get_website_config

def hex_to_rgb_filter(hex_val):
    if not hex_val:
        return "15, 23, 42"
    hex_val = hex_val.lstrip('#')
    if len(hex_val) == 6:
        r, g, b = tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
        return f"{r}, {g}, {b}"
    return "15, 23, 42"

templates.env.filters['hex_to_rgb'] = hex_to_rgb_filter
