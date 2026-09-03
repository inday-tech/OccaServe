import re

with open('app/static/js/caterer/bookings.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

replacement = '''
            } else {
                if (isWalkin) {
                    actionsEl.innerHTML += <div style="padding: 0.65rem 1rem; color: #0369a1; background: #e0f2fe; border: 1px solid #bae6fd; border-radius: 8px; font-size: 0.85rem; font-weight: 600; flex: 1; display: flex; align-items: center; gap: 0.5rem;"><i class="fas fa-cash-register"></i> Awaiting Offline Payment</div>;
                } else {
                    actionsEl.innerHTML += <div style="padding: 0.65rem 1rem; color: #b45309; background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; font-size: 0.85rem; font-weight: 600; flex: 1; display: flex; align-items: center; gap: 0.5rem;"><i class="fas fa-clock"></i> Awaiting Payment Proof from Customer</div>;
                }
            }
'''

js_content = re.sub(
    r'\} else \{\s*actionsEl\.innerHTML \+\= <div style="padding: 0\.65rem 1rem; color: #b45309; background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; font-size: 0\.85rem; font-weight: 600; flex: 1; display: flex; align-items: center; gap: 0\.5rem;"><i class="fas fa-clock"></i> Awaiting Payment Proof from Customer</div>;\s*\}',
    replacement.strip(),
    js_content
)

with open('app/static/js/caterer/bookings.js', 'w', encoding='utf-8') as f:
    f.write(js_content)
print('Fixed walkin awaiting text in bookings.js')
