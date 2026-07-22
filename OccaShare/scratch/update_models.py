import re

file_path = r"c:\OccaServe\OccaShare\app\db\models.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """class PackageService(Base):
    __tablename__ = "package_services"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"))
    quantity = Column(Integer, default=1)
    service = relationship("Service", backref="package_links")"""

new_models = """class PackageService(Base):
    __tablename__ = "package_services"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"))
    quantity = Column(Integer, default=1)
    service = relationship("Service", backref="package_links")

class PackageMenuAddon(Base):
    __tablename__ = "package_menu_addons"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    menu_item_id = Column(Integer, ForeignKey("menu_items.id", ondelete="CASCADE"))
    price = Column(Float, default=0.0)
    max_quantity = Column(Integer, nullable=True)
    is_enabled = Column(Boolean, default=True)

class PackageServiceAddon(Base):
    __tablename__ = "package_service_addons"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"))
    price = Column(Float, default=0.0)
    max_quantity = Column(Integer, nullable=True)
    is_enabled = Column(Boolean, default=True)

class PackageEquipmentAddon(Base):
    __tablename__ = "package_equipment_addons"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="CASCADE"))
    price = Column(Float, default=0.0)
    max_quantity = Column(Integer, nullable=True)
    is_enabled = Column(Boolean, default=True)"""

if target in content:
    content = content.replace(target, new_models)
    
    # Also add relationships to CateringPackage
    cat_target = """    service_links = relationship("PackageService", cascade="all, delete-orphan", backref="package")"""
    cat_new = """    service_links = relationship("PackageService", cascade="all, delete-orphan", backref="package")
    
    menu_addons = relationship("PackageMenuAddon", cascade="all, delete-orphan", backref="package")
    service_addons = relationship("PackageServiceAddon", cascade="all, delete-orphan", backref="package")
    equipment_addons = relationship("PackageEquipmentAddon", cascade="all, delete-orphan", backref="package")"""
    
    content = content.replace(cat_target, cat_new)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Models added successfully.")
else:
    print("Target not found in models.py")
