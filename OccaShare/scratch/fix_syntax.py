import codecs

file_path = 'c:\\OccaServe\\OccaShare\\app\\routers\\caterers.py'
with codecs.open(file_path, 'r', 'utf-8') as f:
    content = f.read()

# I will just replace the exact faulty line with proper quotes
faulty_line = r"        and m.category not in [\'Rentals\', \'Services\', \'Event Styling\', \'Event Rental\', \'Entertainment\', \'Event Coordination\', \'Food Cart\', \'Equipment Rental\', \'Staffing Services\', \'Packages\']"
correct_line = "        and m.category not in ['Rentals', 'Services', 'Event Styling', 'Event Rental', 'Entertainment', 'Event Coordination', 'Food Cart', 'Equipment Rental', 'Staffing Services', 'Packages']"
content = content.replace(faulty_line, correct_line)

faulty_line2 = r"        and getattr(m, \'usage_type\', \'\') != \'package_only\'"
correct_line2 = "        and getattr(m, 'usage_type', '') != 'package_only'"
content = content.replace(faulty_line2, correct_line2)

with codecs.open(file_path, 'w', 'utf-8') as f:
    f.write(content)
