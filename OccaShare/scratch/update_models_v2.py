import re

f = r'c:\OccaServe\OccaShare\app\db\models.py'
with open(f, 'r', encoding='utf-8') as file:
    content = file.read()

# For PackageMenuAddon
old_menu = """class PackageMenuAddon(Base):
    __tablename__ = "package_menu_addons"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    menu_item_id = Column(Integer, ForeignKey("menu_items.id", ondelete="CASCADE"))
    price = Column(Float, default=0.0)
    max_quantity = Column(Integer, nullable=True)
    is_enabled = Column(Boolean, default=True)"""

new_menu = """class PackageMenuAddon(Base):
    __tablename__ = "package_menu_addons"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    menu_item_id = Column(Integer, ForeignKey("menu_items.id", ondelete="CASCADE"))
    price = Column(Float, default=0.0)
    selection_type = Column(String, default="single") # 'single' or 'multiple'
    min_quantity = Column(Integer, default=1)
    max_quantity = Column(Integer, nullable=True)
    is_enabled = Column(Boolean, default=True)"""

content = content.replace(old_menu, new_menu)

# For PackageServiceAddon
old_service = """class PackageServiceAddon(Base):
    __tablename__ = "package_service_addons"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"))
    price = Column(Float, default=0.0)
    max_quantity = Column(Integer, nullable=True)
    is_enabled = Column(Boolean, default=True)"""

new_service = """class PackageServiceAddon(Base):
    __tablename__ = "package_service_addons"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"))
    price = Column(Float, default=0.0)
    selection_type = Column(String, default="single") # 'single' or 'manpower'
    min_quantity = Column(Integer, default=1)
    max_quantity = Column(Integer, nullable=True)
    is_enabled = Column(Boolean, default=True)"""

content = content.replace(old_service, new_service)

# For PackageEquipmentAddon
old_equipment = """class PackageEquipmentAddon(Base):
    __tablename__ = "package_equipment_addons"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="CASCADE"))
    price = Column(Float, default=0.0)
    max_quantity = Column(Integer, nullable=True)
    is_enabled = Column(Boolean, default=True)"""

new_equipment = """class PackageEquipmentAddon(Base):
    __tablename__ = "package_equipment_addons"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="CASCADE"))
    price = Column(Float, default=0.0)
    min_quantity = Column(Integer, default=1)
    max_quantity = Column(Integer, nullable=True)
    is_enabled = Column(Boolean, default=True)"""

content = content.replace(old_equipment, new_equipment)

with open(f, 'w', encoding='utf-8') as out:
    out.write(content)
print('Updated models.py')
