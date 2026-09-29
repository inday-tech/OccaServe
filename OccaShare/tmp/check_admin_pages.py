"""Temporary diagnostic: hit admin pages/APIs with an overridden admin dependency."""
import os
import re
import sys

BASE = r"c:\Users\naomi\OneDrive\Documents\occaserve1\OccaShare"
sys.path.insert(0, BASE)
os.chdir(BASE)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.routers import admin as admin_router  # noqa: E402
from app.db import database, models  # noqa: E402

db = database.SessionLocal()
admin_user = db.query(models.User).filter(models.User.role == "admin").first()
print("admin user:", admin_user.id, admin_user.email)

app.dependency_overrides[admin_router.admin_only] = lambda: admin_user
client = TestClient(app)

for url in ["/admin/customers", "/admin/bookings", "/admin/reports", "/admin/caterers"]:
    r = client.get(url)
    rows = len(re.findall(r"class=\"cust-row\"", r.text))
    print(f"{url} -> {r.status_code} bytes={len(r.text)} rows={rows}")

r = client.get("/admin/api/bookings/138/details")
print("/admin/api/bookings/138/details ->", r.status_code, r.text[:300])

r = client.get("/admin/api/caterers/6/documents")
print("/admin/api/caterers/6/documents ->", r.status_code, r.text[:400])

# ---- Reports KPI extraction ----
r = client.get("/admin/reports")
html = r.text
kpis = re.findall(r"<h4>(.*?)</h4>\s*<span class=\"kpi-value\">(.*?)</span>", html, re.S)
for name, val in kpis:
    print("REPORT KPI:", name.strip(), "=", " ".join(val.split()))

# ---- Customers page KPI extraction + first rows ----
r = client.get("/admin/customers")
html = r.text
kpis = re.findall(r"<h4>(.*?)</h4>\s*<span class=\"kpi-value\">(.*?)</span>", html, re.S)
for name, val in kpis:
    print("CUSTOMER KPI:", name.strip(), "=", " ".join(val.split()))
print("CUSTOMER labels:", sorted(set(re.findall(r"(PENDING KYC|ACTIVE|SUSPENDED|FLAGGED)", html))))

# ---- Bookings page KPI extraction ----
r = client.get("/admin/bookings")
html = r.text
kpis = re.findall(r"<h4>(.*?)</h4>\s*<span class=\"kpi-value\">(.*?)</span>", html, re.S)
for name, val in kpis:
    print("BOOKING KPI:", name.strip(), "=", " ".join(val.split()))

# ---- Customer audit API for a freshly listed (unverified) customer ----
db2 = database.SessionLocal()
unverified = db2.query(models.User).filter(
    models.User.role == "customer", models.User.is_verified == False
).first()
if unverified:
    r = client.get(f"/admin/api/customers/{unverified.id}/audit")
    print("customer audit", unverified.id, "->", r.status_code, r.text[:200])
    r = client.get(f"/admin/verify/{unverified.id}")
    print("verify page ->", r.status_code, len(r.text))
