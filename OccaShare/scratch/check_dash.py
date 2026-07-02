import re

backend_path = r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py'

with open(backend_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = '''@router.get("")
async def dashboard_overview('''

replacement = '''@router.get("")
async def dashboard_overview('''

print("Checking for dashboard endpoint...")
if target in content:
    print("Found it!")
else:
    print("Not found.")
