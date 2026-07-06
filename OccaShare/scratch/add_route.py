import re
with open(r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py', 'r', encoding='utf-8') as f:
    text = f.read()

route = '''
@router.get("/bookings/{booking_id}")
async def redirect_booking_details(booking_id: int):
    return RedirectResponse(url=f"/caterer/bookings?focus={booking_id}", status_code=303)

@router.get("/bookings", response_class=HTMLResponse)
'''

text = text.replace('@router.get("/bookings", response_class=HTMLResponse)', route.strip() + '\n')

with open(r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Added route successfully!')
