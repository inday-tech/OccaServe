import requests
r = requests.get('http://127.0.0.1:8000/caterer/profile', allow_redirects=False)
print(f'Status: {r.status_code}')
print(f'Location: {r.headers.get("location", "N/A")}')
