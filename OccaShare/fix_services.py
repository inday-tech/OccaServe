import re
with open(r'C:\OccaServe\OccaShare\templates\caterer\services.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_js = '''        const data = new FormData(this);
        data.set('price', sellPrice);
        data.set('cost_price', costPrice);'''

new_js = '''        const data = new FormData(this);
        data.set('price', sellPrice);
        data.set('cost_price', costPrice);
        
        // Ensure addon_price is sent as a valid number, even if empty
        const addonPriceInput = document.getElementById('addonPriceInput');
        if (addonPriceInput) {
            data.set('addon_price', parseFloat(addonPriceInput.value.replace(/,/g, '')) || 0);
        }'''

content = content.replace(old_js, new_js)

with open(r'C:\OccaServe\OccaShare\templates\caterer\services.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
