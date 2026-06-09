import re

with open(r"c:\Users\naomi\OneDrive\Documents\occaserve1\OccaShare\app\static\js\customer\booking_wizard\step_kyc.js", "r", encoding="utf-8") as f:
    content = f.read()

# Let's count open/close braces
open_braces = content.count("{")
close_braces = content.count("}")
open_parens = content.count("(")
close_parens = content.count(")")

print(f"Braces: open={open_braces}, close={close_braces}, diff={open_braces - close_braces}")
print(f"Parens: open={open_parens}, close={close_parens}, diff={open_parens - close_parens}")
