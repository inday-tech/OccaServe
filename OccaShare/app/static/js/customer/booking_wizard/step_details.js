document.addEventListener('DOMContentLoaded', function () {
    const pricePerHead = Number(window.pricePerHead || 0);
    const catererId = Number(window.catererId || 0);
    const minGuests = Number(window.minGuests || 1);
    const leadTime = Number(window.bookingLeadTime || 3);
    const phCities = window.PH_CITIES || [];

    // --- Selectors ---
    const form = document.getElementById('detailsForm');
    const guestInput = document.getElementById('guest_count');
    const guestDisplay = document.getElementById('guest_count_display');
    const dateInput = document.getElementById('event_date');
    const timeInput = document.getElementById('event_time');
    const provinceSelect = document.getElementById('province_select');
    const citySelect = document.getElementById('city_select');
    const barangaySelect = document.getElementById('barangay_select');
    const venueHidden = document.getElementById('venue_address_hidden');
    const eventTypeSelect = document.getElementById('event_type_select');
    const otherEventWrap = document.getElementById('other-event-wrap');
    const otherEventInput = document.getElementById('other_event_type');
    const submitBtn = document.getElementById('submitBtn');

    // --- Dynamic Location Data via PSGC ---
    const PROVINCE_CODES = {
        "Abra": "140100000",
        "Albay": "050500000",
        "Apayao": "148100000",
        "Aurora": "037700000",
        "Bataan": "030800000",
        "Batanes": "020900000",
        "Batangas": "041000000",
        "Benguet": "141100000",
        "Bulacan": "031400000",
        "Cagayan": "021500000",
        "Camarines Norte": "051600000",
        "Camarines Sur": "051700000",
        "Catanduanes": "052000000",
        "Cavite": "042100000",
        "Ifugao": "142700000",
        "Ilocos Norte": "012800000",
        "Ilocos Sur": "012900000",
        "Isabela": "023100000",
        "Kalinga": "143200000",
        "La Union": "013300000",
        "Laguna": "043400000",
        "Marinduque": "174000000",
        "Masbate": "054100000",
        "Metro Manila - 1st District": "133900000",
        "Metro Manila - 2nd District": "137400000",
        "Metro Manila - 3rd District": "137500000",
        "Metro Manila - 4th District": "137600000",
        "Mountain Province": "144400000",
        "Nueva Ecija": "034900000",
        "Nueva Vizcaya": "025000000",
        "Occidental Mindoro": "175100000",
        "Oriental Mindoro": "175200000",
        "Palawan": "175300000",
        "Pampanga": "035400000",
        "Pangasinan": "015500000",
        "Quezon": "045600000",
        "Quirino": "025700000",
        "Rizal": "045800000",
        "Romblon": "175900000",
        "Sorsogon": "056200000",
        "Tarlac": "036900000",
        "Zambales": "037100000"
    };

    let cachedCities = {};
    let cachedBarangays = {};

    // --- 1. Set Min Date based on Lead Time ---
    const minCalendarDate = new Date();
    minCalendarDate.setDate(minCalendarDate.getDate() + leadTime); // Using lead time dynamically
    const minDateString = minCalendarDate.toISOString().split('T')[0];
    if (dateInput) {
        dateInput.setAttribute('min', minDateString);
    }

    // --- 1.5 Format Guest Count ---
    window.formatGuestCount = function (input) {
        let rawValue = input.value.replace(/\D/g, '');
        if (!rawValue) {
            guestInput.value = "";
            input.value = "";
            return;
        }
        let num = parseInt(rawValue, 10);
        if (num > 1000) num = 1000;
        guestInput.value = num;
        input.value = num.toLocaleString();
    };

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
        let total = 0;
        if (window.pricingMode === 'fixed') {
            total = window.basePrice;
        } else {
            total = guests * pricePerHead;
        }

        // Add-ons price
        const checkedAddons = document.querySelectorAll('.menu-item-card.addon input[type="checkbox"]:checked');
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
        if (reservationFeeInput) reservationFeeInput.value = total * 0.3; // 30% reservation
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

    window.handleSelectionRuleLimit = function(checkbox) {
        const group = checkbox.closest('.selection-group');
        const limit = parseInt(group.dataset.limit) || 0;
        const catId = group.dataset.category;
        
        const card = checkbox.closest('.menu-item-card');
        if (checkbox.checked) {
            card.classList.add('selected');
        } else {
            card.classList.remove('selected');
        }

        const checkedBoxes = group.querySelectorAll('input[type="checkbox"]:checked');
        const count = checkedBoxes.length;

        // Update counter UI
        const counterEl = document.getElementById(`counter-${catId}`);
        if (counterEl) {
            counterEl.innerText = `${count} / ${limit} Selected`;
            if (count === limit) {
                counterEl.style.background = '#dcfce7';
                counterEl.style.color = '#166534';
            } else {
                counterEl.style.background = '#ccfbf1';
                counterEl.style.color = '#0f766e';
            }
        }

        // Disable unselected checkboxes if limit is reached
        const allBoxes = group.querySelectorAll('input[type="checkbox"]');
        if (count >= limit) {
            allBoxes.forEach(cb => {
                if (!cb.checked) {
                    cb.disabled = true;
                    cb.closest('.menu-item-card').style.opacity = '0.5';
                    cb.closest('.menu-item-card').style.cursor = 'not-allowed';
                }
            });
        } else {
            allBoxes.forEach(cb => {
                cb.disabled = false;
                cb.closest('.menu-item-card').style.opacity = '1';
                cb.closest('.menu-item-card').style.cursor = 'pointer';
            });
        }
    };

    // --- 3. Check Date Availability ---
    window.checkAvailability = async function () {
        const chip = document.getElementById('availability-chip');
        if (!dateInput || !dateInput.value) return;

        const date = dateInput.value;
        const parts = date.split('-');
        if (parts.length === 3) {
            const selectedDate = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
            const minDate = new Date();
            minDate.setDate(minDate.getDate() + leadTime - 1); // Dynamic lead time constraint
            minDate.setHours(0,0,0,0);
            if (selectedDate <= minDate) {
                chip.style.display = 'none'; // Hide chip since inline validation already flags it
                if (submitBtn) submitBtn.disabled = true;
                return;
            }
        }

        chip.className = 'availability-chip checking';
        chip.style.display = 'inline-flex';
        chip.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking...';

        try {
            const response = await fetch(`/packages/api/check-availability?caterer_id=${catererId}&date_str=${date}`);
            const data = await response.json();

            if (data.available) {
                chip.className = 'availability-chip available';
                chip.innerHTML = '<i class="fas fa-check-circle"></i> Date Available';
                if (submitBtn) submitBtn.disabled = false;
            } else {
                chip.className = 'availability-chip booked';
                chip.innerHTML = '<i class="fas fa-times-circle"></i> Fully Booked';
                if (submitBtn) submitBtn.disabled = true;
            }
        } catch (error) {
            chip.innerHTML = 'Error checking date';
        }
    };

    // --- 4. Other Event Type Toggle ---
    if (eventTypeSelect) {
        eventTypeSelect.addEventListener('change', function () {
            if (this.value === 'Other') {
                otherEventWrap.classList.add('visible');
                otherEventInput.required = true;
                setTimeout(() => otherEventInput.focus(), 100);
            } else {
                otherEventWrap.classList.remove('visible');
                otherEventInput.required = false;
                otherEventInput.value = '';
                document.getElementById('err-other-type').classList.remove('show');
            }
        });
    }

    // --- 5. Cascading Location Choice (PSGC API) ---
    async function populateCities(province, selectedCity = null, selectedBrgy = null) {
        citySelect.innerHTML = '<option value="">-- Select City --</option>';
        barangaySelect.innerHTML = '<option value="">-- Select Barangay --</option>';
        barangaySelect.disabled = true;

        if (PROVINCE_CODES[province]) {
            citySelect.disabled = true;
            try {
                const code = PROVINCE_CODES[province];
                let cities = cachedCities[code];
                if (!cities) {
                    citySelect.innerHTML = '<option value="">Loading...</option>';
                    let url = `https://psgc.gitlab.io/api/provinces/${code}/cities-municipalities/`;
                    if (code.startsWith('13')) {
                        url = `https://psgc.gitlab.io/api/districts/${code}/cities-municipalities/`;
                    }
                    const res = await fetch(url);
                    cities = await res.json();
                    cities.sort((a, b) => a.name.localeCompare(b.name));
                    cachedCities[code] = cities;
                }
                
                citySelect.innerHTML = '<option value="">-- Select City --</option>';
                cities.forEach(city => {
                    const opt = document.createElement('option');
                    opt.value = city.name;
                    opt.textContent = city.name;
                    opt.dataset.code = city.code;
                    if (city.name === selectedCity) opt.selected = true;
                    citySelect.appendChild(opt);
                });
                citySelect.disabled = false;
                
                if (selectedCity) {
                    const matchedCity = cities.find(c => c.name === selectedCity);
                    if (matchedCity) {
                        populateBarangays(matchedCity.code, selectedBrgy);
                    }
                }
            } catch (e) {
                console.error('API Error:', e);
            }
        } else {
            citySelect.disabled = true;
        }
    }

    async function populateBarangays(cityCode, selectedBrgy = null) {
        barangaySelect.innerHTML = '<option value="">-- Select Barangay --</option>';
        if (cityCode) {
            barangaySelect.disabled = true;
            try {
                let brgys = cachedBarangays[cityCode];
                if (!brgys) {
                    barangaySelect.innerHTML = '<option value="">Loading...</option>';
                    const res = await fetch(`https://psgc.gitlab.io/api/cities-municipalities/${cityCode}/barangays/`);
                    brgys = await res.json();
                    brgys.sort((a, b) => a.name.localeCompare(b.name));
                    cachedBarangays[cityCode] = brgys;
                }
                
                barangaySelect.innerHTML = '<option value="">-- Select Barangay --</option>';
                brgys.forEach(b => {
                    const opt = document.createElement('option');
                    opt.value = b.name;
                    opt.textContent = b.name;
                    if (b.name === selectedBrgy) opt.selected = true;
                    barangaySelect.appendChild(opt);
                });
                barangaySelect.disabled = false;
            } catch (e) {
                console.error('API Error:', e);
            }
        } else {
            barangaySelect.disabled = true;
        }
    }

    if (provinceSelect) {
        provinceSelect.addEventListener('change', function () {
            populateCities(this.value);
            updateHiddenVenue();
        });

        citySelect.addEventListener('change', function () {
            const selOpt = this.options[this.selectedIndex];
            const code = selOpt ? selOpt.dataset.code : null;
            populateBarangays(code);
            updateHiddenVenue();
        });

        barangaySelect.addEventListener('change', updateHiddenVenue);
    }

    function updateHiddenVenue() {
        const p = provinceSelect.value;
        const c = citySelect.value;
        const b = barangaySelect.value;
        if (p && c && b) {
            venueHidden.value = `${b}, ${c}, ${p}`;
        } else {
            venueHidden.value = "";
        }
    }

    // --- 5.1 Load Existing Location Data ---
    function loadExistingLocation() {
        const existing = venueHidden.value; // Format: "Barangay, City, Province"
        if (existing && existing.includes(',')) {
            const parts = existing.split(',').map(s => s.trim());
            if (parts.length >= 3) {
                const brgy = parts[0];
                const city = parts[1];
                const prov = parts[2];

                for (let i = 0; i < provinceSelect.options.length; i++) {
                    if (provinceSelect.options[i].value === prov) {
                        provinceSelect.selectedIndex = i;
                        break;
                    }
                }

                populateCities(prov, city, brgy);
            }
        } else if (provinceSelect.value) {
            populateCities(provinceSelect.value);
        }
    }

    // --- 6. Form Validation & Real-time Feedback ---
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
        eventTypeSelect.addEventListener('change', () => {
            validateField(eventTypeSelect, 'err-type', v => v !== '');
            if (eventTypeSelect.value === 'Other') {
                validateField(otherEventInput, 'err-other-type', v => v.trim().length > 0);
            }
        });
    }
    if (otherEventInput) {
        otherEventInput.addEventListener('input', () => {
            if (eventTypeSelect.value === 'Other') validateField(otherEventInput, 'err-other-type', v => v.trim().length > 0);
        });
    }

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

    const validateEventDate = () => {
        if (!dateInput) return true;
        return validateField(dateInput, 'err-date', v => {
            if (!v) return false;
            const parts = v.split('-');
            if(parts.length !== 3) return false;
            const selectedDate = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
            
            const minDate = new Date();
            minDate.setDate(minDate.getDate() + leadTime - 1); // Dynamic lead time constraint
            minDate.setHours(0,0,0,0);
            return selectedDate > minDate;
        }, `Please select a date at least ${leadTime} days in advance.`);
    };
    if (dateInput) {
        dateInput.addEventListener('input', validateEventDate);
        dateInput.addEventListener('change', validateEventDate);
    }

    const validateEventTime = () => {
        if (!timeInput) return true;
        return validateField(timeInput, 'err-time', v => {
            if (!v) return false;
            const parts = v.split(':');
            if (parts.length !== 2) return false;
            const hour = parseInt(parts[0]);
            
            // Standard catering operations: 6:00 AM to 9:00 PM (21:59)
            if (hour < 6 || hour > 21) {
                return false;
            }
            return true;
        }, "Please select a time between 6:00 AM and 9:00 PM.");
    };
    if (timeInput) {
        timeInput.addEventListener('input', validateEventTime);
        timeInput.addEventListener('change', validateEventTime);
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

    if (form) {
        form.addEventListener('submit', function (e) {
            let isValid = true;

            if (eventName) isValid = validateField(eventName, 'err-name', v => v.trim().length > 0) && isValid;
            
            if (eventTypeSelect) {
                isValid = validateField(eventTypeSelect, 'err-type', v => v !== '') && isValid;
                if (eventTypeSelect.value === 'Other') {
                    isValid = validateField(otherEventInput, 'err-other-type', v => v.trim().length > 0) && isValid;
                }
            }

            if (guestDisplay) isValid = validateGuestCount() && isValid;
            if (dateInput) isValid = validateEventDate() && isValid;
            if (timeInput) isValid = validateEventTime() && isValid;
            
            if (provinceSelect) isValid = validateField(provinceSelect, 'err-province', v => v !== '') && isValid;
            if (citySelect) isValid = validateField(citySelect, 'err-city', v => v !== '') && isValid;
            if (barangaySelect) isValid = validateField(barangaySelect, 'err-barangay', v => v !== '') && isValid;

            // Selection Rules Validation
            const selectionGroups = document.querySelectorAll('.selection-group');
            let selectionErrorMsg = '';
            selectionGroups.forEach(group => {
                const limit = parseInt(group.dataset.limit) || 0;
                const cat = group.dataset.category;
                const count = group.querySelectorAll('input[type="checkbox"]:checked').length;
                
                if (count !== limit && limit > 0) {
                    isValid = false;
                    selectionErrorMsg += `• Please select exactly ${limit} item(s) for ${cat.replace(/([A-Z])/g, ' $1').trim()}.\n`;
                    const counterEl = document.getElementById(`counter-${cat}`);
                    if (counterEl) {
                        counterEl.style.background = '#fee2e2';
                        counterEl.style.color = '#b91c1c';
                    }
                }
            });

            if (selectionErrorMsg) {
                alert("Incomplete Menu Setup:\n\n" + selectionErrorMsg);
            }

            if (!isValid) {
                e.preventDefault();
                const firstError = document.querySelector('.field-error.show');
                if (firstError) {
                    firstError.parentElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        });
    }

    // Handle Backend Validation Errors
    const urlParams = new URLSearchParams(window.location.search);
    const bookingError = urlParams.get('booking_error');
    if (bookingError) {
        const errDate = document.getElementById('err-date');
        if (errDate && dateInput) {
            errDate.innerText = decodeURIComponent(bookingError);
            errDate.classList.add('show');
            dateInput.classList.add('error');
            dateInput.scrollIntoView({behavior: 'smooth', block: 'center'});
        }
        
        const url = new URL(window.location.href);
        url.searchParams.delete('booking_error');
        window.history.replaceState({}, document.title, url.pathname + url.search + url.hash);
    }

    // --- 7. Menu Swapping Logic ---
    let activeSlotIndex = null;

    window.openSwapModal = function(category, slotIndex) {
        activeSlotIndex = slotIndex;
        const modal = document.getElementById('swapModal');
        const container = document.getElementById('swapOptionsContainer');
        const title = document.getElementById('modalCategoryTitle');

        title.innerText = `Swap ${category}`;
        container.innerHTML = '<p class="form-subtitle">Loading items...</p>';
        modal.style.display = 'flex';

        // Filter items by category
        const options = window.allMenuItems.filter(i => i.category === category && !i.is_addon);

        if (options.length === 0) {
            container.innerHTML = `<p class="form-subtitle">No other ${category} options available from this caterer.</p>`;
            return;
        }

        container.innerHTML = '';
        options.forEach(item => {
            const card = document.createElement('div');
            card.className = 'swap-option-card';
            card.innerHTML = `
                <div class="soc-info">
                    <span class="soc-name">${item.name}</span>
                    <span class="soc-cat">${item.category}</span>
                </div>
                <button type="button" class="btn-select-swap" onclick="selectSwapItem(${item.id}, '${item.name.replace(/'/g, "\\'")}')">Select</button>
            `;
            card.onclick = () => selectSwapItem(item.id, item.name);
            container.appendChild(card);
        });
    };

    window.closeSwapModal = function() {
        document.getElementById('swapModal').style.display = 'none';
        activeSlotIndex = null;
    };

    window.selectSwapItem = function(itemId, itemName) {
        if (!activeSlotIndex) return;

        const slot = document.getElementById(`slot-${activeSlotIndex}`);
        const input = slot.querySelector('.slot-input');
        const nameSpan = document.getElementById(`name-${activeSlotIndex}`);

        if (input && nameSpan) {
            input.value = itemId;
            nameSpan.innerText = itemName;
            
            // Visual feedback
            slot.style.borderColor = 'var(--wiz-primary)';
            slot.style.background = 'rgba(255, 123, 84, 0.05)';
            setTimeout(() => {
                slot.style.background = 'var(--wiz-slate-50)';
            }, 500);
        }

        closeSwapModal();
    };

    // Close modal on click outside
    window.onclick = function(event) {
        const modal = document.getElementById('swapModal');
        if (event.target == modal) {
            closeSwapModal();
        }
    };

    // Initial run
    updateCalculator();
    loadExistingLocation();
});
