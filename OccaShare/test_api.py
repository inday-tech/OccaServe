from fastapi.testclient import TestClient
from app.main import app
from app import models
from app.database import SessionLocal

def get_caterer_user():
    db = SessionLocal()
    user = db.query(models.User).filter(models.User.role == 'caterer').first()
    db.close()
    return user

user = get_caterer_user()
if not user:
    print("No caterer found")
    exit()

client = TestClient(app)

# Override the dependency to simulate logged in caterer
from app.routers.auth import caterer_only
app.dependency_overrides[caterer_only] = lambda: user

response = client.get("/caterer/api/dashboard-overview?timeframe=month")
print("STATUS:", response.status_code)
if response.status_code != 200:
    print(response.text)
else:
    print("SUCCESS")
