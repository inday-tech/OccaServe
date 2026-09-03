import re

with open('app/static/js/caterer/bookings.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

replacement = '''
                if (isPayment && !isWalkin) {
                    actionsEl.innerHTML += <button type="button" class="btn-footer-action" onclick="window.requestNewProof()" style="background: white; color: #475569; border: 1px solid #cbd5e1; font-weight: 600;"><i class="fas fa-redo"></i> Request New Proof</button>;
                }
'''

js_content = re.sub(
    r'if\s*\(isPayment\)\s*\{\s*actionsEl\.innerHTML \+\= <button type="button" class="btn-footer-action" onclick="window\.requestNewProof\(\$\{data\.id\}\)"[^>]+><i class="fas fa-redo"><\/i> Request New Proof<\/button>;\s*\}',
    replacement.strip(),
    js_content
)

with open('app/static/js/caterer/bookings.js', 'w', encoding='utf-8') as f:
    f.write(js_content)
print('Fixed walkin request proof button')
