import re
with open(r'C:\OccaServe\OccaShare\app\routers\caterer_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_e = '''            "status": e.status,
            "is_hidden": e.is_hidden,
            "image_url": e.image_url
        })'''
new_e = '''            "status": e.status,
            "is_hidden": e.is_hidden,
            "usage_type": getattr(e, "usage_type", "both"),
            "is_addon": getattr(e, "is_addon", False),
            "addon_price": getattr(e, "addon_price", 0.0),
            "image_url": e.image_url
        })'''
content = content.replace(old_e, new_e)

old_s = '''            "status": s.status,
            "is_hidden": s.is_hidden,
            "image_url": s.image_url
        })'''
new_s = '''            "status": s.status,
            "is_hidden": s.is_hidden,
            "usage_type": getattr(s, "usage_type", "both"),
            "is_addon": getattr(s, "is_addon", False),
            "addon_price": getattr(s, "addon_price", 0.0),
            "image_url": s.image_url
        })'''
content = content.replace(old_s, new_s)

old_m = '''            "is_hidden": m.is_hidden,
            "image_url": m.image_url
        })'''
new_m = '''            "is_hidden": m.is_hidden,
            "usage_type": getattr(m, "usage_type", "both"),
            "is_addon": getattr(m, "is_addon", False),
            "addon_price": getattr(m, "addon_price", 0.0),
            "image_url": m.image_url
        })'''
content = content.replace(old_m, new_m)

with open(r'C:\OccaServe\OccaShare\app\routers\caterer_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
