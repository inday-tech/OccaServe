document.addEventListener('DOMContentLoaded', function () {
    const guestInput = document.getElementById('guest_count');
    const addonCheckboxes = document.querySelectorAll('input[name="selected_addons"]');
    
    const pricePerHead = window.pricePerHead || 0;

    // --- 1. Event Type Toggle ---
    const eventTypeSelect = document.getElementById('event_type_select');
    const otherEventTypeWrap = document.getElementById('other-event-wrap');
    const otherEventTypeInput = document.getElementById('other_event_type');

    if (eventTypeSelect) {
        eventTypeSelect.addEventListener('change', function () {
            if (this.value === 'Other') {
                otherEventTypeWrap.classList.add('visible');
                otherEventTypeInput.required = true;
            } else {
                otherEventTypeWrap.classList.remove('visible');
                otherEventTypeInput.required = false;
                otherEventTypeInput.value = '';
            }
        });
    }

    // --- 2. Update Calculator ---
    window.updateCalculator = function () {
        const calcGuests = document.getElementById('calc-guests');
        const calcAddonsCount = document.getElementById('calc-addons-count');
        const calcAddonsTotal = document.getElementById('calc-addons-total');
        const calcTotal = document.getElementById('calc-grand-total');
        const totalPriceInput = document.getElementById('total_price_input');
        const reservationFeeInput = document.getElementById('reservation_fee_input');

        if (!guestInput || !calcGuests || !calcTotal) return;

        const guests = parseInt(guestInput.value) || 0;
        calcGuests.innerText = guests;

        // Base package price
        let total = guests * pricePerHead;

        // Add-ons price
        const checkedAddons = document.querySelectorAll('input[name="selected_addons"]:checked');
        let addonsTotal = 0;
        checkedAddons.forEach(cb => {
            const price = parseFloat(cb.getAttribute('data-price')) || 0;
            addonsTotal += price;
        });

        if (calcAddonsCount) calcAddonsCount.innerText = checkedAddons.length;
        if (calcAddonsTotal) calcAddonsTotal.innerText = '+₱' + addonsTotal.toLocaleString(undefined, { minimumFractionDigits: 2 });
        
        total += addonsTotal;

        calcTotal.innerText = '₱' + total.toLocaleString(undefined, { minimumFractionDigits: 2 });

        if (totalPriceInput) totalPriceInput.value = total;
        if (reservationFeeInput) reservationFeeInput.value = (total * 0.3).toFixed(2); // 30% reservation
    };

    window.handleMenuCardToggle = function(checkbox) {
        const card = checkbox.closest('.menu-item-card');
        if (checkbox.checked) {
            card.classList.add('selected');
        } else {
            card.classList.remove('selected');
        }
        updateCalculator();
    };

    // Initialize calculator
    updateCalculator();

    // --- 3. Check Date Availability ---
    window.checkAvailability = async function () {
        const dateInput = document.getElementById('event_date');
        const chip = document.getElementById('availability-chip');
        if (!dateInput || !dateInput.value) return;

        chip.style.display = 'inline-flex';
        chip.className = 'availability-chip checking';
        chip.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking availability...';

        try {
            const response = await fetch(`/caterers/${window.catererId}/check-availability?date=${dateInput.value}`);
            const data = await response.json();

            if (data.available) {
                chip.className = 'availability-chip available';
                chip.innerHTML = '<i class="fas fa-check-circle"></i> Date Available';
            } else {
                chip.className = 'availability-chip booked';
                chip.innerHTML = '<i class="fas fa-times-circle"></i> Date Fully Booked';
            }
        } catch (error) {
            chip.style.display = 'none';
        }
    };

    // --- 4. Location Cascade Logic ---
    const provinceSelect = document.getElementById('province_select');
    const citySelect = document.getElementById('city_select');
    const barangaySelect = document.getElementById('barangay_select');
    const venueAddressHidden = document.getElementById('venue_address_hidden');

    const lagunaData = {
        "Biñan": ["Binan", "Canlalay", "Casile", "De La Paz", "Dila", "Langkiwa", "Loma", "Malaban", "Malamig", "Mamplasan", "Platero", "Poblacion", "San Antonio", "San Jose", "San Vicente", "Santo Tomas", "Soro-soro", "Timbao", "Zapote"],
        "Cabuyao": ["Banay-Banay", "Banlic", "Bigaa", "Butong", "Casile", "Gulod", "Mamatid", "Marinig", "Niugan", "Pittland", "Pulo", "Sala", "San Isidro"],
        "Calamba": ["Bagong Kalsada", "Bañadero", "Barandal", "Batino", "Bubuyan", "Bucal", "Bunggo", "Burol", "Camaligan", "Canlubang", "Halang", "Hornalan", "Laguerta", "La Mesa", "Lawa", "Lecheria", "Lingga", "Looc", "Mabato", "Majada Labas", "Makiling", "Mapagong", "Masili", "Maunong", "Mayapa", "Milagrosa", "Palingon", "Palo-Alto", "Pansol", "Parian", "Prinza", "Punla", "Putho Tuntungin", "Real", "Saimsim", "Sampiruhan", "San Cristobal", "San Jose", "San Juan", "Sirang Lupa", "Sucol", "Turbina", "Ulango"],
        "San Pedro": ["Bagong Silang", "Chrysanthemum", "Cuyab", "Estrella", "Fatima", "G.S.I.S.", "Holiday Hills", "Langgam", "Laram", "Magsaysay", "Maharlika", "Narra", "Nueva", "Pacita I", "Pacita II", "Poblacion", "Riviera", "Rosario", "Sampaguita", "San Antonio", "San Lorenzo Christian", "San Roque", "San Vicente", "Santa Elena", "Santo Niño", "United Bayanihan", "United Better Living", "Victoria"],
        "Santa Rosa": ["Aplaya", "Balibago", "Caingin", "Dila", "Ditas", "Don Jose", "Ibaba", "Kanluran", "Labas", "Macabling", "Malitlit", "Market Area", "Pooc", "Pulong Santa Cruz", "Santo Domingo", "Sinalhan", "Tagapo"]
    };

    function populateCities() {
        if (!citySelect) return;
        citySelect.innerHTML = '<option value="">-- Select City --</option>';
        Object.keys(lagunaData).sort().forEach(city => {
            const opt = document.createElement('option');
            opt.value = city;
            opt.textContent = city;
            citySelect.appendChild(opt);
        });
        citySelect.disabled = false;
        barangaySelect.disabled = true;
    }

    if (citySelect) {
        citySelect.addEventListener('change', function () {
            const city = this.value;
            barangaySelect.innerHTML = '<option value="">-- Select Barangay --</option>';
            if (city && lagunaData[city]) {
                lagunaData[city].forEach(brgy => {
                    const opt = document.createElement('option');
                    opt.value = brgy;
                    opt.textContent = brgy;
                    barangaySelect.appendChild(opt);
                });
                barangaySelect.disabled = false;
            } else {
                barangaySelect.disabled = true;
            }
            updateHiddenAddress();
        });
    }

    if (provinceSelect) {
        provinceSelect.addEventListener('change', function() {
            if (this.value === 'Laguna') populateCities();
            updateHiddenAddress();
        });
        // Initial if Laguna selected
        if (provinceSelect.value === 'Laguna') populateCities();
    }

    if (barangaySelect) {
        barangaySelect.addEventListener('change', updateHiddenAddress);
    }

    function updateHiddenAddress() {
        if (!venueAddressHidden) return;
        const p = provinceSelect.value;
        const c = citySelect.value;
        const b = barangaySelect.value;
        if (p && c && b) {
            venueAddressHidden.value = `${b}, ${c}, ${p}`;
        }
    }

    // --- 5. Initial Calculations ---
    updateCalculator();
});
