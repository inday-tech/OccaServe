import sys

file_path = r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if '@router.post("/api/payments/request-payout")' in line and start_idx == -1:
        start_idx = i
    if start_idx != -1 and i > start_idx and 'return {"status": "success", "payout_id": new_payout.id, "amount": total_ready}' in line:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    del lines[start_idx:end_idx+1]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print('Deleted successfully.')
else:
    print(f'Failed. Start: {start_idx}, End: {end_idx}')
