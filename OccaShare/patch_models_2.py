import re
with open(r'C:\OccaServe\OccaShare\app\db\models.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_pe = '''class PackageEquipment(Base):
    __tablename__ = "package_equipment"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="CASCADE"))
    quantity = Column(Integer, default=1)'''
new_pe = '''class PackageEquipment(Base):
    __tablename__ = "package_equipment"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="CASCADE"))
    quantity = Column(Integer, default=1)
    equipment = relationship("Equipment", backref="package_links")'''
content = content.replace(old_pe, new_pe)

old_ps = '''class PackageService(Base):
    __tablename__ = "package_services"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"))
    quantity = Column(Integer, default=1)'''
new_ps = '''class PackageService(Base):
    __tablename__ = "package_services"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"))
    quantity = Column(Integer, default=1)
    service = relationship("Service", backref="package_links")'''
content = content.replace(old_ps, new_ps)

with open(r'C:\OccaServe\OccaShare\app\db\models.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done patching models.py")
