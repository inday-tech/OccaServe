function updateCalculator(guests, upgradeFee, addonPrice) {
    let addonsTotal = addonPrice; // flat addon price? No, wait!
    // Wait, let's look at step_details.js for addon calculations
    // checkedAddons.forEach(cb => { const price = parseFloat(cb.getAttribute('data-price')) || 0; addonsTotal += price; });
    // It does NOT multiply addonsTotal by guests!
    
    let upgradesTotal = upgradeFee * guests;
    
    let extraCharges = addonsTotal + upgradesTotal;
    return extraCharges;
}
console.log(updateCalculator(50, 25, 1250)); // If they had 1250 addon, it would be 2500.
