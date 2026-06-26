import re
with open(r'C:\OccaServe\OccaShare\app\static\js\caterer\packages.js', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

old_calc = '''        let ingCostPerPax = 0;
        for (const [cat, costs] of Object.entries(selectedDishesByCategory)) {
            costs.sort((a, b) => b - a);
            const limit = rules[cat] ? parseInt(rules[cat]) : costs.length;
            const effectiveLimit = Math.min(limit, costs.length);
            for (let i = 0; i < effectiveLimit; i++) {
                ingCostPerPax += costs[i];
            }
        }

        const ingDisplay = document.getElementById('pkgIngredientCostDisplay');
        if (ingDisplay) {
            ingDisplay.innerText = '₱' + ingCostPerPax.toFixed(2) + ' / pax';
            ingDisplay.dataset.cost = ingCostPerPax;
        }
    }

    const ingDisplay = document.getElementById('pkgIngredientCostDisplay');
    const ingCostPerPax = parseFloat(ingDisplay?.dataset?.cost) || 0;'''

new_calc = '''        let ingCostPerPaxVar = 0;
        for (const [cat, costs] of Object.entries(selectedDishesByCategory)) {
            costs.sort((a, b) => b - a);
            const limit = rules[cat] ? parseInt(rules[cat]) : costs.length;
            const effectiveLimit = Math.min(limit, costs.length);
            for (let i = 0; i < effectiveLimit; i++) {
                ingCostPerPaxVar += costs[i];
            }
        }
        
        window._tempIngCostPerPax = ingCostPerPaxVar;
    }

    const ingCostPerPax = window._tempIngCostPerPax || 0;'''

content = content.replace(old_calc, new_calc)

# Replace all occurrences of ₱, ,
content = re.sub(r',|Ã¢â€šÂ±', '₱', content)

with open(r'C:\OccaServe\OccaShare\app\static\js\caterer\packages.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
