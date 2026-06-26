import re
with open(r'C:\OccaServe\OccaShare\app\db\models.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    caterer = relationship("CatererProfile", back_populates="packages")
    menu_items = relationship("MenuItem", secondary="package_menus", back_populates="packages")

    bookings = relationship("Booking", back_populates="package")'''

new = '''    caterer = relationship("CatererProfile", back_populates="packages")
    menu_items = relationship("MenuItem", secondary="package_menus", back_populates="packages")
    
    equipment_links = relationship("PackageEquipment", cascade="all, delete-orphan", backref="package")
    service_links = relationship("PackageService", cascade="all, delete-orphan", backref="package")

    bookings = relationship("Booking", back_populates="package")'''
content = content.replace(old, new)

with open(r'C:\OccaServe\OccaShare\app\db\models.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done patching models.py")
