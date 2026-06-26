import re

with open('c:/OccaServe/OccaShare/app/db/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r'is_archived = Column\(Boolean, default=False\)\n\s*created_at = Column\(DateTime\(timezone=True\), server_default=func.now\(\)\)',
    'is_archived = Column(Boolean, default=False)\n    usage_type = Column(String, default="both") # \'package_only\', \'order_only\', \'both\'\n    created_at = Column(DateTime(timezone=True), server_default=func.now())',
    content
)

with open('c:/OccaServe/OccaShare/app/db/models.py', 'w', encoding='utf-8') as f:
    f.write(content)
