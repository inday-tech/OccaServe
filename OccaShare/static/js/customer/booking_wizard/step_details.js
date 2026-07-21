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
        // Add-ons price
        const allAddonCheckboxes = document.querySelectorAll('input[name="selected_addons"], input[name="selected_equipment_addons"], input[name="selected_service_addons"]');
        let addonsTotal = 0;
        let checkedCount = 0;

        allAddonCheckboxes.forEach(cb => {
            if (cb.name === 'selected_service_addons') {
                const card = cb.closest('.menu-item-card');
                const reqLabel = card.querySelector('.staff-req-label');
                const qtyValSpan = card.querySelector('.qty-val');
                const priceSpan = card.querySelector('.mic-price');
                
                let qty = 1;
                const capacityType = cb.getAttribute('data-capacity-type') || 'unit_based';
                const staffRatio = parseInt(cb.getAttribute('data-staff-ratio')) || 0;
                const minStaff = parseInt(cb.getAttribute('data-min-staff')) || 1;
                const basePrice = parseFloat(priceSpan ? priceSpan.getAttribute('data-base-price') : 0) || parseFloat(cb.getAttribute('data-price')) || 0;
                
                if (capacityType === 'staff_based' && staffRatio > 0) {
                    qty = Math.max(minStaff, Math.ceil(guests / staffRatio));
                    if (reqLabel && qtyValSpan) {
                        reqLabel.style.display = 'block';
                        qtyValSpan.innerText = qty;
                    }
                    if (priceSpan) {
                        priceSpan.innerText = '+₱' + (basePrice * qty).toLocaleString(undefined, { minimumFractionDigits: 2 });
                    }
                    cb.setAttribute('data-price', basePrice * qty);
                }
            }

            if (cb.checked) {
                checkedCount++;
                const price = parseFloat(cb.getAttribute('data-price')) || 0;
                addonsTotal += price;
            }
        });

        if (calcAddonsCount) calcAddonsCount.innerText = checkedCount;
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

    // --- 6. Real-time Field Validation ---
    function validateField(input, errorId, validationFn, customErrorText = null) {
        if (!input) return true;
        const errSpan = document.getElementById(errorId);
        const isValid = validationFn(input.value);
        if (isValid) {
            input.classList.remove('error');
            if (errSpan) {
                errSpan.classList.remove('show');
            }
        } else {
            input.classList.add('error');
            if (errSpan) {
                if (customErrorText) errSpan.innerText = customErrorText;
                errSpan.classList.add('show');
            }
        }
        return isValid;
    }

    const eventName = document.getElementById('event_name');
    if (eventName) {
        eventName.addEventListener('input', () => validateField(eventName, 'err-name', v => v.trim().length > 0));
        eventName.addEventListener('change', () => validateField(eventName, 'err-name', v => v.trim().length > 0));
    }

    if (eventTypeSelect) {
        eventTypeSelect.addEventListener('change', () => validateField(eventTypeSelect, 'err-type', v => v !== ''));
    }

    const guestDisplay = document.getElementById('guest_count_display');
    const validateGuestCount = () => {
        if (!guestDisplay) return true;
        const g = parseInt(guestDisplay.value.replace(/,/g, '')) || 0;
        let valid = g >= window.minGuests;
        if (window.maxGuests > 0) valid = valid && g <= window.maxGuests;
        
        let errorText = `Min: ${window.minGuests} pax.`;
        if (window.maxGuests > 0 && g > window.maxGuests) errorText = `Max: ${window.maxGuests} pax.`;
        
        return validateField(guestDisplay, 'err-guests', () => valid, errorText);
    };
    if (guestDisplay) {
        guestDisplay.addEventListener('input', validateGuestCount);
        guestDisplay.addEventListener('change', validateGuestCount);
    }

    const eventDate = document.getElementById('event_date');
    const validateEventDate = () => {
        if (!eventDate) return true;
        return validateField(eventDate, 'err-date', v => {
            if (!v) return false;
            // Parse YYYY-MM-DD locally to avoid timezone shifts
            const parts = v.split('-');
            if(parts.length !== 3) return false;
            const selectedDate = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
            
            const minDate = new Date();
            minDate.setDate(minDate.getDate() + 2); // At least 3 days in advance
            minDate.setHours(0,0,0,0);
            return selectedDate > minDate;
        }, "Please select a date at least 3 days in advance.");
    };
    if (eventDate) {
        eventDate.addEventListener('input', validateEventDate);
        eventDate.addEventListener('change', validateEventDate);
    }

    const eventTime = document.getElementById('event_time');
    if (eventTime) {
        eventTime.addEventListener('input', () => validateField(eventTime, 'err-time', v => v !== ''));
        eventTime.addEventListener('change', () => validateField(eventTime, 'err-time', v => v !== ''));
    }

    if (provinceSelect) {
        provinceSelect.addEventListener('change', () => validateField(provinceSelect, 'err-province', v => v !== ''));
    }
    if (citySelect) {
        citySelect.addEventListener('change', () => validateField(citySelect, 'err-city', v => v !== ''));
    }
    if (barangaySelect) {
        barangaySelect.addEventListener('change', () => validateField(barangaySelect, 'err-barangay', v => v !== ''));
    }

    // Intercept form submit to validate all
    const form = document.getElementById('detailsForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            const results = [];
            if (eventName) results.push(validateField(eventName, 'err-name', v => v.trim().length > 0));
            if (eventTypeSelect) results.push(validateField(eventTypeSelect, 'err-type', v => v !== ''));
            if (eventDate) results.push(validateEventDate());
            if (eventTime) results.push(validateField(eventTime, 'err-time', v => v !== ''));
            if (provinceSelect) results.push(validateField(provinceSelect, 'err-province', v => v !== ''));
            if (citySelect) results.push(validateField(citySelect, 'err-city', v => v !== ''));
            if (barangaySelect) results.push(validateField(barangaySelect, 'err-barangay', v => v !== ''));
            if (guestDisplay) results.push(validateGuestCount());

            const isValid = results.every(r => r === true);

            if (!isValid) {
                e.preventDefault();
                // Scroll to first error
                const firstError = document.querySelector('.form-input.error');
                if (firstError) firstError.scrollIntoView({behavior: 'smooth', block: 'center'});
            }
        });
    }

    // --- 7. Handle Backend Validation Errors ---
    const urlParams = new URLSearchParams(window.location.search);
    const bookingError = urlParams.get('booking_error');
    if (bookingError) {
        const errDate = document.getElementById('err-date');
        const eventDateInput = document.getElementById('event_date');
        if (errDate && eventDateInput) {
            errDate.innerText = decodeURIComponent(bookingError);
            errDate.classList.add('show');
            eventDateInput.classList.add('error');
            eventDateInput.scrollIntoView({behavior: 'smooth', block: 'center'});
        }
        
        // Clean URL so it doesn't show again on refresh
        const url = new URL(window.location.href);
        url.searchParams.delete('booking_error');
        window.history.replaceState({}, document.title, url.pathname + url.search + url.hash);
    }
});
