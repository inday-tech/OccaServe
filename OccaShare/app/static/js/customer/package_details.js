/* Customer Package Details Logic */

function calculateTotal() {
    const guests = parseInt(document.getElementById('guest_count').value) || 0;
    const displayGuests = document.getElementById('display-guests');
    if (displayGuests) displayGuests.innerText = guests;

    const baseTotal = guests * basePricePerHead;
    const displayBasePrice = document.getElementById('display-base-price');
    if (displayBasePrice) displayBasePrice.innerText = '₱' + baseTotal.toLocaleString(undefined, { minimumFractionDigits: 2 });

    const addonCheckboxes = document.querySelectorAll('input[name="selected_addons"]:checked');
    const addonContainer = document.getElementById('addon-rows');
    if (addonContainer) addonContainer.innerHTML = '';

    let addonTotal = 0;
    addonCheckboxes.forEach(cb => {
        const price = parseFloat(cb.dataset.price);
        addonTotal += price;

        if (addonContainer) {
            const row = document.createElement('div');
            row.className = 'price-summary-row';
            row.innerHTML = `<span>+ ${cb.closest('.menu-item-card').querySelector('h4').innerText}</span><span>₱${price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>`;
            addonContainer.appendChild(row);
        }
    });

    const grandTotal = baseTotal + addonTotal;
    const resFee = grandTotal * 0.20;

    const displayGrandTotal = document.getElementById('display-grand-total');
    if (displayGrandTotal) displayGrandTotal.innerText = '₱' + grandTotal.toLocaleString(undefined, { minimumFractionDigits: 2 });

    const displayResFee = document.getElementById('display-res-fee');
    if (displayResFee) displayResFee.innerText = '₱' + resFee.toLocaleString(undefined, { minimumFractionDigits: 2 });

    const totalInput = document.getElementById('total_price_input');
    if (totalInput) totalInput.value = grandTotal;

    const resFeeInput = document.getElementById('reservation_fee_input');
    if (resFeeInput) resFeeInput.value = resFee;
}

async function checkAvailability() {
    const dateInput = document.getElementById('event_date');
    if (!dateInput) return;

    const date = dateInput.value;
    const msg = document.getElementById('availability-msg');
    const submitBtn = document.getElementById('submitBtn');

    if (!date) return;

    if (msg) {
        msg.style.display = 'block';
        msg.style.color = 'var(--text-light)';
        msg.innerText = 'Checking availability...';
    }

    try {
        const response = await fetch(`/packages/api/check-availability?caterer_id=${catererId}&date_str=${date}`);
        const data = await response.json();

        if (msg && submitBtn) {
            if (data.available) {
                msg.style.color = '#10b981';
                msg.innerHTML = '<i class="fas fa-check-circle"></i> Date is available!';
                submitBtn.disabled = false;
                submitBtn.style.opacity = '1';
            } else {
                msg.style.color = '#ef4444';
                msg.innerHTML = `<i class="fas fa-times-circle"></i> ${data.reason || 'Not available'}`;
                submitBtn.disabled = true;
                submitBtn.style.opacity = '0.5';
            }
        }
    } catch (error) {
        if (msg) msg.innerText = 'Error checking availability.';
    }
}

// Global variables will be initialized in the template
document.addEventListener('DOMContentLoaded', () => {
    // Initial calculation if elements exist
    if (document.getElementById('guest_count')) {
        calculateTotal();
    }
});
