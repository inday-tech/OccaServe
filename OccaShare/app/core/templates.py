from fastapi.templating import Jinja2Templates
from ..db.database import SessionLocal
from ..db import models

templates = Jinja2Templates(directory="templates")

def get_website_config():
    """Returns a plain dict snapshot of website config to avoid SQLAlchemy DetachedInstanceError."""
    db = SessionLocal()
    try:
        config = db.query(models.WebsiteConfig).first()
        if not config:
            config = models.WebsiteConfig()
            db.add(config)
            db.commit()
            db.refresh(config)
        
        # Convert to a plain dict while session is still open
        # This prevents DetachedInstanceError when templates access attributes
        # after the session is closed (which is the #1 cause of disappearing images)
        return {
            "id": config.id,
            "site_name": config.site_name,
            "support_email": config.support_email,
            "seo_description": config.seo_description,
            "logo_url": config.logo_url,
            "favicon_url": config.favicon_url,
            "facebook_link": config.facebook_link,
            "instagram_link": config.instagram_link,
            "twitter_link": config.twitter_link,
            "commission_rate": config.commission_rate,
            "commission_fixed_amount": getattr(config, 'commission_fixed_amount', 20.0),
            "max_file_size_mb": config.max_file_size_mb,
            "maintenance_mode": config.maintenance_mode,
            "maintenance_message": config.maintenance_message
        }
    except Exception as e:
        print(f"[CONFIG ERROR] get_website_config failed: {e}")
        return None
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
