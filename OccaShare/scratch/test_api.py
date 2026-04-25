import requests

base_url = "http://localhost:8000" # Adjust if necessary
cookies = {"access_token": "Bearer YOUR_TOKEN_HERE"} # I don't have a token

def test_details(pkg_id):
    url = f"{base_url}/caterer/packages/{pkg_id}/details"
    try:
        # Since I don't have a token, I'll just check if the route exists or if it returns 401/403
        # If it returns 500, then we have a bug.
        resp = requests.get(url)
        print(f"Status: {resp.status_code}")
        print(f"Content: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

# I'll just check the code again.
