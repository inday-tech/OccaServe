from fastapi.templating import Jinja2Templates
from ..db.database import SessionLocal
from ..db import models
import os
from pathlib import Path
import threading
import time

# Initialize Jinja2 templates pointing to the top-level "templates" directory
templates = Jinja2Templates(directory="templates")
_STATIC_ROOT = (Path(__file__).resolve().parents[1] / "static").resolve()
_WEBSITE_CONFIG_TTL_SECONDS = 10
_website_config_lock = threading.Lock()
_website_config_cache = {"expires_at": 0.0, "value": None}


def static_asset_version(asset_path: str) -> str:
    """Use each asset's file metadata for stable, cache-friendly URLs."""
    target = (_STATIC_ROOT / str(asset_path).lstrip("/\\")).resolve()
    if not target.is_relative_to(_STATIC_ROOT):
        return "0"
    try:
        stat = target.stat()
        return f"{stat.st_mtime_ns:x}-{stat.st_size:x}"
    except OSError:
        return "0"


def website_config():
    """
    Fetches and returns website configuration (logo, favicon, branding, etc.)
    as a plain dict to avoid SQLAlchemy DetachedInstanceError.
    This is registered as a Jinja2 global so templates can call it directly:
        {% set wconfig = website_config() %}
    """
    now = time.monotonic()
    cached = _website_config_cache
    if now < cached["expires_at"]:
        return dict(cached["value"]) if cached["value"] else None

    with _website_config_lock:
        now = time.monotonic()
        cached = _website_config_cache
        if now < cached["expires_at"]:
            return dict(cached["value"]) if cached["value"] else None

        db = SessionLocal()
        try:
            config = db.query(models.WebsiteConfig).first()
            if not config:
                config = models.WebsiteConfig()
                db.add(config)
                db.commit()
                db.refresh(config)

            value = {
                "id": config.id,
                "site_name": config.site_name,
                "support_email": config.support_email,
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
            _website_config_cache.update(
                value=value,
                expires_at=now + _WEBSITE_CONFIG_TTL_SECONDS,
            )
            return dict(value)
        except Exception as e:
            print(f"[TEMPLATES] website_config() error: {e}")
            _website_config_cache.update(value=None, expires_at=now + 2)
            return None
        finally:
            db.close()


def hex_to_rgb(hex_color: str) -> str:
    """
    Converts a CSS hex color string to a comma-separated RGB string.
    Used in caterer/layout.html for CSS custom properties:
        --primary-color-rgb: {{ color | hex_to_rgb }}
    So it can be used as: rgba(var(--primary-color-rgb), 0.2)

    Accepts: '#800000', '800000', '#fff', 'fff'
    Returns: '128, 0, 0'  (on error falls back to '128, 0, 0')
    """
    try:
        hex_color = hex_color.strip().lstrip("#")
        # Expand shorthand: 'fff' -> 'ffffff'
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}"
    except Exception:
        return "128, 0, 0"  # safe fallback (maroon)


# ── Register Jinja2 globals & filters ──────────────────────────────────────
# website_config() callable in every template without explicit route passing
templates.env.globals["website_config"] = website_config
templates.env.globals["static_asset_version"] = static_asset_version

# hex_to_rgb filter: {{ '#800000' | hex_to_rgb }} → '128, 0, 0'
templates.env.filters["hex_to_rgb"] = hex_to_rgb

# Google Maps API Key global function
def google_maps_api_key():
    return os.getenv("GOOGLE_MAPS_API_KEY", "AIzaSyBpFEUgMDrteQk_BIYKSRRID1mhuCEEykY")

templates.env.globals["google_maps_api_key"] = google_maps_api_key

# Trigger template reload and verify changes

