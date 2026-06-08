import os

file_path = 'templates/customer/booking_wizard/alacarte_checkout.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Just replace the offending jinja variables directly
bad_str1 = "'the Caterer\\\\'s Number'"
bad_str2 = "'the Caterer\\'s Number'"

content = content.replace(bad_str1, '"the Caterer\\'s Number"')
content = content.replace(bad_str2, '"the Caterer\\'s Number"')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
