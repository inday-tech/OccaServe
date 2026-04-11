document.addEventListener('DOMContentLoaded', function () {
    const menuForm = document.getElementById('menuForm');
    if (!menuForm) return;

    const guestCount = parseInt(menuForm.dataset.guestCount) || 0;
    const initialPackagePrice = parseFloat(menuForm.dataset.packagePrice) || 0;
    
    // Elements
    const basePriceDisplay = document.getElementById('summary-base-price');
    const addonsPriceDisplay = document.getElementById('summary-addons-price');
    const serviceChargeDisplay = document.getElementById('summary-service-charge');
    const totalDisplay = document.getElementById('summary-total');
    const downpaymentDisplay = document.getElementById('summary-downpayment');

    window.updateMenuCalculator = function () {
        let packagePricePerHead = initialPackagePrice;
        
        // 1. If radio buttons exist (package not yet locked), use the selected one
        const selectedPackage = document.querySelector('input[name="package_id"]:checked');
        if (selectedPackage && selectedPackage.type === 'radio') {
            const card = selectedPackage.closest('.package-option-card');
            if (card) {
                const priceText = card.querySelector('.package-option-price').innerText;
                packagePricePerHead = parseFloat(priceText.replace(/[^0-9.]/g, '')) || 0;
            }
        }

        const baseTotal = guestCount * packagePricePerHead;
        
        // 2. Add-ons
        let addonsTotal = 0;
        document.querySelectorAll('input[name="selected_addons"]:checked').forEach(checkbox => {
            addonsTotal += parseFloat(checkbox.dataset.price) || 0;
        });

        // 3. Calculation Logic (Matching step_details.js)
        const subtotalForService = baseTotal + addonsTotal;
        const serviceCharge = Math.round(subtotalForService * 0.085);
        const subtotalWithService = subtotalForService + serviceCharge;
        const vat = Math.round(subtotalWithService * 0.12);
        const total = subtotalWithService + vat;
        const downpayment = Math.round(total * 0.5);

        // Update UI
        basePriceDisplay.innerText = '₱' + baseTotal.toLocaleString();
        addonsPriceDisplay.innerText = '₱' + addonsTotal.toLocaleString();
        serviceChargeDisplay.innerText = '₱' + serviceCharge.toLocaleString();
        totalDisplay.innerText = '₱' + total.toLocaleString();
        downpaymentDisplay.innerText = '₱' + downpayment.toLocaleString();
    };

    // Initial calculation
    updateMenuCalculator();
});
