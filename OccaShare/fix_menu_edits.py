import re
with open(r'C:\OccaServe\OccaShare\templates\caterer\menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_1 = '''            toggleCustomCategory();

            form.description.value = item.description || '';
            form.status.value = item.status || 'available';'''
new_1 = '''            toggleCustomCategory();

            form.description.value = item.description || '';
            if (form.cost_price) form.cost_price.value = item.cost_price || '';
            form.status.value = item.status || 'available';'''
content = content.replace(old_1, new_1)

old_2 = '''            togglePricingSection();

            if (window.applyCommaFormatting) {
                window.applyCommaFormatting(document.getElementById('fixed_price_input'));
            }'''
new_2 = '''            togglePricingSection();

            if (window.applyCommaFormatting) {
                if (document.getElementById('cost_price_input')) window.applyCommaFormatting(document.getElementById('cost_price_input'));
                window.applyCommaFormatting(document.getElementById('fixed_price_input'));
            }'''
content = content.replace(old_2, new_2)

old_3 = '''        form.querySelectorAll('.js-format-comma').forEach(i => i.value = i.value.replace(/,/g, ''));
        const data = new FormData(this);
        
        // Handle comma removal correctly for addon_price and fixed_price_input'''
new_3 = '''        form.querySelectorAll('.js-format-comma').forEach(i => i.value = i.value.replace(/,/g, ''));
        const data = new FormData(this);
        
        // Ensure cost_price is sent as a number, even if empty
        const costPriceInput = document.getElementById('cost_price_input');
        if (costPriceInput) {
            data.set('cost_price', parseFloat(costPriceInput.value) || 0);
        }
        
        // Handle comma removal correctly for addon_price and fixed_price_input'''
content = content.replace(old_3, new_3)

with open(r'C:\OccaServe\OccaShare\templates\caterer\menu.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done updating menu.html edits!')
