import sys

target_file = r"c:\Users\naomi\OneDrive\Documents\occaserve\OccaShare\app\routers\admin.py"

with open(target_file, "r") as f:
    lines = f.readlines()

# Find the last occurrence of 'router = APIRouter' to find the start of a valid block
# Or more simply, find the last block of imports.
latest_start = 0
for i, line in enumerate(lines):
    if line.startswith("from fastapi import APIRouter"):
        latest_start = i

if latest_start > 0:
    cleaned_lines = lines[latest_start:]
    # Remove any trailing git markers at the very end
    if cleaned_lines[-1].startswith(">>>>>>>"):
        cleaned_lines = cleaned_lines[:-1]
    
    with open(target_file, "w") as f:
        f.writelines(cleaned_lines)
    print(f"Cleaned admin.py starting from line {latest_start + 1}")
else:
    print("Could not find start of a valid block")
