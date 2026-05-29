import sys

file_path = r'c:\OccaServe\OccaShare\app\services\notification.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1

for i, line in enumerate(lines):
    if 'async def notify_payout_requested' in line:
        # Step back to include @staticmethod
        if i > 0 and '@staticmethod' in lines[i-1]:
            start_idx = i - 1
        else:
            start_idx = i
        break

if start_idx != -1:
    del lines[start_idx:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print('Deleted legacy payout notification code successfully.')
else:
    print('Pattern not found.')
