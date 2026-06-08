import os
import re

file_path = 'templates/customer/booking_wizard/alacarte_checkout.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r"'the Caterer\\'s Number'", '"the Caterer\'s Number"', content)
content = re.sub(r"'the Caterer\\\\'s Number'", '"the Caterer\'s Number"', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
