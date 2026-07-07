import requests

session = requests.Session()
login_data = {"email": "customer@example.com", "password": "Password123!"} # Default test user
session.post("http://localhost:8000/auth/login", data=login_data)

url = "http://localhost:8000/bookings/step/details"
data = {
    "caterer_id": "1",
    "event_name": "Test Event",
    "event_type": "Wedding",
    "event_date": "2026-10-10",
    "event_time": "14:00",
    "guest_count": "100",
    "province": "Laguna",
    "city": "Santa Cruz",
    "barangay": "Poblacion",
}

response = session.post(url, data=data)
print(f"Status: {response.status_code}")
if response.status_code == 422:
    print(response.json())

