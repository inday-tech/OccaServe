from fastapi.templating import Jinja2Templates
from ..db.database import SessionLocal
from ..db import models

# Initialize Jinja2 templates pointing to the top-level "templates" directory
templates = Jinja2Templates(directory="templates")


def website_config():
    """
    Fetches and returns website configuration (logo, favicon, branding, etc.)
    as a plain dict to avoid SQLAlchemy DetachedInstanceError.
    This is registered as a Jinja2 global so templates can call it directly:
        {% set wconfig = website_config() %}
    """
    db = SessionLocal()
    try:
        config = db.query(models.WebsiteConfig).first()
        if not config:
            # Auto-create a default config row if none exists
            config = models.WebsiteConfig()
            db.add(config)
            db.commit()
            db.refresh(config)

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
            "commission_fixed_amount": config.commission_fixed_amount,
            "max_file_size_mb": config.max_file_size_mb,
            "maintenance_mode": config.maintenance_mode,
            "maintenance_message": config.maintenance_message,
        }
    except Exception as e:
        print(f"[TEMPLATES] website_config() error: {e}")
        return None
    finally:
        db.close()


# Register website_config as a Jinja2 global function so every template
# can call {{ website_config() }} or {% set wconfig = website_config() %}
# without needing it to be explicitly passed in the route context.
templates.env.globals["website_config"] = website_config
