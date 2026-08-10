document.addEventListener('DOMContentLoaded', function () {
    try {
        const pricePerHead = Number(window.pricePerHead || 0);
    const catererId = Number(window.catererId || 0);
    const minGuests = Number(window.minGuests || 1);
    const leadTime = Number(window.bookingLeadTime || 3);
    const phCities = window.PH_CITIES || [];
    
    let parsedRules = {};
    try {
        parsedRules = typeof window.catererRules === 'string' ? JSON.parse(window.catererRules) : (window.catererRules || {});
    } catch(e) { console.error("Error parsing catererRules", e); }
    window.catererRules = parsedRules;

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
        "Laguna": "043400000"
    };

    let cachedCities = {};
    let cachedBarangays = {};

    // --- 1. Set Min and Max Date based on Lead Time ---
    const getLocalISODate = (date) => {
        const yyyy = date.getFullYear();
        const mm = String(date.getMonth() + 1).padStart(2, '0');
        const dd = String(date.getDate()).padStart(2, '0');
        return `${yyyy}-${mm}-${dd}`;
    };

    const minCalendarDate = new Date();
    minCalendarDate.setDate(minCalendarDate.getDate() + leadTime); // Using lead time dynamically
    const minDateString = getLocalISODate(minCalendarDate);
    
    const maxCalendarDate = new Date();
    maxCalendarDate.setMonth(maxCalendarDate.getMonth() + 7); // Max 7 months in advance
    const maxDateString = getLocalISODate(maxCalendarDate);
    
    if (dateInput) {
        dateInput.setAttribute('min', minDateString);
        dateInput.setAttribute('max', maxDateString);
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
        let basePackageTotal = 0;
        let excessGuestsTotal = 0;

        if (window.pricingMode === 'fixed') {
            basePackageTotal = window.basePrice;
            if (guests > window.minGuests && window.additionalGuestPrice > 0) {
                excessGuestsTotal = (guests - window.minGuests) * window.additionalGuestPrice;
            }
            total = basePackageTotal + excessGuestsTotal;
        } else {
            total = guests * pricePerHead;
        }

        // Add-ons price
        let addonsTotal = 0;
        document.querySelectorAll('input[name="selected_addons"]:checked').forEach(cb => {
            const price = parseFloat(cb.getAttribute('data-price')) || 0;
            addonsTotal += price * guests; // Menu Add-ons are per pax
        });
        document.querySelectorAll('input[name="selected_equipment_addons"]:checked, input[name="selected_service_addons"]:checked').forEach(cb => {
            const price = parseFloat(cb.getAttribute('data-price')) || 0;
            addonsTotal += price; // Equipment and Services are flat fees
        });

        // Upgrades price (Swapped / Premium Items)
        let upgradesTotal = 0;
        document.querySelectorAll('.menu-item-card.selectable input[type="checkbox"]:checked').forEach(cb => {
            const fee = parseFloat(cb.getAttribute('data-upgrade-fee')) || 0;
            upgradesTotal += fee * guests;
        });
        document.querySelectorAll('.slot-input').forEach(input => {
            const fee = parseFloat(input.getAttribute('data-upgrade-fee')) || 0;
            upgradesTotal += fee * guests;
        });

        const addonsCount = document.querySelectorAll('.menu-item-card.addon input[type="checkbox"]:checked').length;
        if (calcAddonsCount) calcAddonsCount.innerText = addonsCount;
        
        const extraCharges = addonsTotal + upgradesTotal;
        if (calcAddonsTotal) calcAddonsTotal.innerText = '+₱' + extraCharges.toLocaleString(undefined, { minimumFractionDigits: 2 });
        
        total += extraCharges;
        total += (window.currentDeliveryFee || 0);

        const calcDeliveryFee = document.getElementById('calc-delivery-fee');
        if (calcDeliveryFee) {
            if (window.deliveryFeeStatus === "manual_quote") {
                calcDeliveryFee.innerText = "TBD (Manual Quote)";
            } else if (window.deliveryFeeStatus === "error" || window.deliveryFeeStatus === "pending") {
                calcDeliveryFee.innerText = "---";
            } else {
                calcDeliveryFee.innerText = '+₱' + (window.currentDeliveryFee || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
            }
        }

        calcTotal.innerText = '₱' + total.toLocaleString(undefined, { minimumFractionDigits: 2 });

        if (totalPriceInput) totalPriceInput.value = total;
        if (reservationFeeInput) reservationFeeInput.value = total * 0.3; // 30% reservation
    };

    window.toggleCardSelection = function(card) {
        // If card is disabled due to limit, do nothing
        if (card.style.cursor === 'not-allowed') return;
        
        const checkbox = card.querySelector('input[type="checkbox"]');
        if (!checkbox) return;
        
        // Only toggle if checkbox is not explicitly disabled (e.g. from limit rules)
        if (checkbox.disabled && !checkbox.checked) return;
        
        checkbox.checked = !checkbox.checked;
        
        if (card.classList.contains('addon')) {
            window.handleMenuCardToggle(checkbox);
        } else {
            window.handleSelectionRuleLimit(checkbox);
        }
    };

    window.handleMenuCardToggle = function(checkbox) {
        const card = checkbox.closest('.menu-item-card');
        const indicator = card.querySelector('.indicator-circle');
        if (checkbox.checked) {
            card.classList.add('selected');
            if (indicator) {
                indicator.classList.add('active');
                indicator.innerHTML = '<i class="fas fa-check"></i>';
            }
        } else {
            card.classList.remove('selected');
            if (indicator) {
                indicator.classList.remove('active');
                indicator.innerHTML = '';
            }
        }
        updateCalculator();
    };

    window.handleSelectionRuleLimit = function(checkbox) {
        const group = checkbox.closest('.selection-group');
        const limit = parseInt(group.dataset.limit) || 0;
        const catId = group.dataset.category;
        
        const card = checkbox.closest('.menu-item-card');
        const indicator = card.querySelector('.indicator-circle');
        if (checkbox.checked) {
            card.classList.add('selected');
            if (indicator) {
                indicator.classList.add('active');
                indicator.innerHTML = '<i class="fas fa-check"></i>';
            }
        } else {
            card.classList.remove('selected');
            if (indicator) {
                indicator.classList.remove('active');
                indicator.innerHTML = '';
            }
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
            
            if (chip) {
                if (selectedDate <= minDate) {
                    chip.style.display = 'none'; // Hide chip since inline validation already flags it
                    if (submitBtn) submitBtn.disabled = true;
                    return;
                }
            }
        }

        chip.className = 'availability-chip checking';
        chip.style.display = 'inline-flex';
        chip.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking...';

        try {
            const response = await fetch(`/packages/api/check-availability?caterer_id=${catererId}&date_str=${date}`);
            if (!response.ok) throw new Error('API failed');
            const data = await response.json();

            if (data.available && chip) {
                chip.className = 'availability-chip available';
                chip.innerHTML = '<i class="fas fa-check-circle"></i> Date Available';
                if (submitBtn) submitBtn.disabled = false;
            } else if (chip) {
                chip.className = 'availability-chip booked';
                chip.innerHTML = '<i class="fas fa-times-circle"></i> Fully Booked';
                if (submitBtn) submitBtn.disabled = true;
            }
        } catch (error) {
            if (chip) chip.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error checking date';
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
        citySelect.innerHTML = '<option value="" disabled selected hidden>-- Select City --</option>';
        barangaySelect.innerHTML = '<option value="" disabled selected hidden>-- Select Barangay --</option>';
        barangaySelect.disabled = true;

        if (PROVINCE_CODES[province]) {
            citySelect.disabled = true;
            try {
                const code = PROVINCE_CODES[province];
                let cities = cachedCities[code];
                if (!cities) {
                    const cityEl = document.getElementById('city_select');
                    if(cityEl.tagName !== 'SELECT') return; // already fallback
                    
                    cityEl.innerHTML = '<option value="" disabled selected hidden>Loading cities...</option>';
                    let url = `https://psgc.gitlab.io/api/provinces/${code}/cities-municipalities/`;
                    if (code === '130000000') {
                        url = `https://psgc.gitlab.io/api/regions/${code}/cities-municipalities/`;
                    }
                    
                    const res = await fetch(url);
                    if (!res.ok) throw new Error('API failed');
                    
                    cities = await res.json();
                    cities.sort((a, b) => a.name.localeCompare(b.name));
                    cachedCities[code] = cities;
                }
                
                const cityEl = document.getElementById('city_select');
                if(cityEl.tagName !== 'SELECT') return;
                
                cityEl.innerHTML = '<option value="" disabled selected hidden>-- Select City --</option>';
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
                console.warn('API Error, keeping dropdowns empty:', e);
                const cityEl = document.getElementById('city_select');
                if(cityEl && cityEl.tagName === 'SELECT') {
                    cityEl.innerHTML = '<option value="" disabled selected hidden>Error Loading</option>';
                    cityEl.disabled = false;
                }
            }
        } else {
            const cityEl = document.getElementById('city_select');
            if(cityEl && cityEl.tagName === 'SELECT') cityEl.disabled = true;
        }
    }

    async function populateBarangays(cityCode, selectedBrgy = null) {
        const brgyEl = document.getElementById('barangay_select');
        if(!brgyEl) return;
        if(brgyEl.tagName !== 'SELECT') return;
        
        brgyEl.innerHTML = '<option value="" disabled selected hidden>-- Select Barangay --</option>';
        if (cityCode) {
            brgyEl.disabled = true;
            try {
                let brgys = cachedBarangays[cityCode];
                if (!brgys) {
                    brgyEl.innerHTML = '<option value="" disabled selected hidden>Loading barangays...</option>';
                    
                    const res = await fetch(`https://psgc.gitlab.io/api/cities-municipalities/${cityCode}/barangays/`);
                    if (!res.ok) throw new Error('API failed');
                    
                    brgys = await res.json();
                    brgys.sort((a, b) => a.name.localeCompare(b.name));
                    cachedBarangays[cityCode] = brgys;
                }
                
                brgyEl.innerHTML = '<option value="" disabled selected hidden>-- Select Barangay --</option>';
                brgys.forEach(b => {
                    const opt = document.createElement('option');
                    opt.value = b.name;
                    opt.textContent = b.name;
                    if (b.name === selectedBrgy) opt.selected = true;
                    brgyEl.appendChild(opt);
                });
                brgyEl.disabled = false;
            } catch (e) {
                console.warn('API Error, keeping dropdowns empty:', e);
                brgyEl.innerHTML = '<option value="" disabled selected hidden>Error Loading</option>';
                brgyEl.disabled = false;
            }
        } else {
            brgyEl.disabled = true;
        }
    }

    window.currentDeliveryFee = 0;
    window.deliveryFeeStatus = "pending";

    const updateHiddenVenue = async function() {
        const provEl = document.getElementById('province_select');
        const cityEl = document.getElementById('city_select');
        const brgyEl = document.getElementById('barangay_select');
        
        const p = provEl ? (provEl.tagName === 'SELECT' ? (provEl.options[provEl.selectedIndex]?.text || '') : provEl.value) : '';
        const c = cityEl ? (cityEl.tagName === 'SELECT' ? (cityEl.options[cityEl.selectedIndex]?.text || '') : cityEl.value) : '';
        const b = brgyEl ? (brgyEl.tagName === 'SELECT' ? (brgyEl.options[brgyEl.selectedIndex]?.text || '') : brgyEl.value) : '';
        
        if (p && c && b && p !== '-- Province --' && c !== '-- Select City --' && b !== '-- Select Barangay --') {
            venueHidden.value = `${b}, ${c}, ${p}`;
            
            // Fetch dynamic delivery fee
            try {
                const res = await fetch(`/customer/api/caterer/${catererId}/delivery-fee?province=${encodeURIComponent(p)}&municipality=${encodeURIComponent(c)}`);
                const data = await res.json();
                
                if (data.found) {
                    if (data.is_manual_quote) {
                        window.currentDeliveryFee = 0;
                        window.deliveryFeeStatus = "manual_quote";
                    } else {
                        window.currentDeliveryFee = data.fee;
                        window.deliveryFeeStatus = "calculated";
                    }
                } else {
                    if (data.out_of_coverage_action === 'manual') {
                        window.currentDeliveryFee = 0;
                        window.deliveryFeeStatus = "manual_quote";
                    } else if (data.out_of_coverage_action === 'reject') {
                        window.currentDeliveryFee = 0;
                        window.deliveryFeeStatus = "error";
                    } else {
                        window.currentDeliveryFee = data.base_fee || 0;
                        window.deliveryFeeStatus = "calculated";
                    }
                }
            } catch (e) {
                console.error("Failed to fetch delivery fee", e);
                window.currentDeliveryFee = 0;
                window.deliveryFeeStatus = "error";
            }
            updateCalculator();
        } else {
            venueHidden.value = "";
            window.currentDeliveryFee = 0;
            window.deliveryFeeStatus = "pending";
            updateCalculator();
        }
    };
    window.updateHiddenVenue = updateHiddenVenue;

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
        eventName.addEventListener('blur', () => validateField(eventName, 'err-name', v => v.trim().length > 0));
    }

    if (eventTypeSelect) {
        eventTypeSelect.addEventListener('change', () => {
            validateField(eventTypeSelect, 'err-type', v => v !== '');
            if (eventTypeSelect.value === 'Other') {
                validateField(otherEventInput, 'err-other-type', v => v.trim().length > 0);
            }
        });
        eventTypeSelect.addEventListener('blur', () => validateField(eventTypeSelect, 'err-type', v => v !== ''));
    }
    if (otherEventInput) {
        otherEventInput.addEventListener('input', () => {
            if (eventTypeSelect.value === 'Other') validateField(otherEventInput, 'err-other-type', v => v.trim().length > 0);
        });
        otherEventInput.addEventListener('blur', () => {
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
        guestDisplay.addEventListener('blur', validateGuestCount);
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
            
            const maxDate = new Date();
            maxDate.setMonth(maxDate.getMonth() + 7); // Exactly 7 months
            maxDate.setHours(23,59,59,999);
            
            if (selectedDate <= minDate) {
                document.getElementById('err-date').innerText = `Please select a date at least ${leadTime} days in advance.`;
                return false;
            }
            if (selectedDate > maxDate) {
                document.getElementById('err-date').innerText = `Bookings can only be made up to 7 months in advance.`;
                return false;
            }
            
            // Operating days check
            if (window.catererRules && window.catererRules.business_hours && window.catererRules.business_hours.operating_days) {
                const daysOfWeek = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
                const selectedDayName = daysOfWeek[selectedDate.getDay()];
                const operatingDays = window.catererRules.business_hours.operating_days;
                if (operatingDays.length > 0 && operatingDays.length < 7 && !operatingDays.includes(selectedDayName)) {
                    document.getElementById('err-date').innerText = `Caterer is closed on ${selectedDayName}s. (${operatingDays.join(', ')})`;
                    return false;
                }
            }
            
            return true;
        }, `Invalid date.`);
    };
    if (dateInput) {
        dateInput.addEventListener('input', validateEventDate);
        dateInput.addEventListener('change', validateEventDate);
        dateInput.addEventListener('blur', validateEventDate);
    }

    const validateEventTime = () => {
        if (!timeInput) return true;
        return validateField(timeInput, 'err-time', v => {
            const customTrigger = document.querySelector('#custom-time-select .form-input');
            if (!v) {
                if (customTrigger) customTrigger.classList.add('error');
                return false;
            }
            const parts = v.split(':');
            if (parts.length !== 2) {
                if (customTrigger) customTrigger.classList.add('error');
                return false;
            }
            const hour = parseInt(parts[0]);
            const min = parseInt(parts[1]);
            
            let openTime = '08:00';
            let closeTime = '20:00';
            if (window.catererRules && window.catererRules.business_hours) {
                openTime = window.catererRules.business_hours.open_time || openTime;
                closeTime = window.catererRules.business_hours.close_time || closeTime;
            }
            
            const parseTime = (timeStr) => {
                const [h, m] = timeStr.split(':').map(Number);
                return h * 60 + m;
            };
            
            const formatAmPm = (mins) => {
                const h = Math.floor(mins / 60);
                const m = mins % 60;
                const ampm = h >= 12 ? 'PM' : 'AM';
                const h12 = h % 12 || 12;
                return `${h12}:${m.toString().padStart(2, '0')} ${ampm}`;
            };
            
            const selectedMins = hour * 60 + min;
            const openMins = parseTime(openTime);
            const closeMins = parseTime(closeTime);
            
            // Strict 8 AM - 8 PM fallback limit
            const fallbackOpen = 8 * 60; // 8:00 AM
            const fallbackClose = 20 * 60; // 8:00 PM
            
            const finalOpenMins = Math.max(openMins, fallbackOpen);
            const finalCloseMins = Math.min(closeMins, fallbackClose);
            
            const openFormatted = formatAmPm(finalOpenMins);
            const closeFormatted = formatAmPm(finalCloseMins);
            
            if (selectedMins < finalOpenMins || selectedMins > finalCloseMins) {
                document.getElementById('err-time').innerText = `Please choose an event start time between ${openFormatted} and ${closeFormatted}.`;
                if (customTrigger) customTrigger.classList.add('error');
                return false;
            }
            if (customTrigger) customTrigger.classList.remove('error');
            return true;
        }, "Please select a valid time.");
    };
    if (timeInput) {
        let openTime = '08:00';
        let closeTime = '20:00';
        if (window.catererRules && window.catererRules.business_hours) {
            openTime = window.catererRules.business_hours.open_time || openTime;
            closeTime = window.catererRules.business_hours.close_time || closeTime;
        }
        
        const parseTimeStr = (t) => {
            const [h,m] = t.split(':').map(Number);
            return h*60 + m;
        };
        const formatTimeStr = (mins) => {
            const h = Math.floor(mins / 60);
            const m = mins % 60;
            return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
        };
        const formatAmPmStr = (mins) => {
            const h = Math.floor(mins / 60);
            const m = mins % 60;
            const ampm = h >= 12 ? 'PM' : 'AM';
            const h12 = h % 12 || 12;
            return `${h12}:${m.toString().padStart(2, '0')} ${ampm}`;
        };
        
        const openMins = Math.max(parseTimeStr(openTime), 8*60);
        const closeMins = Math.min(parseTimeStr(closeTime), 20*60);
        
        if (timeInput) {
            timeInput.style.display = 'none';
            const initialVal = timeInput.getAttribute('data-initial') || timeInput.value || '';
            
            let customSelect = document.getElementById('custom-time-select');
            let menu = document.getElementById('time-dropdown-menu');
            let triggerText = document.getElementById('time-trigger-text');
            let icon = null;
            let grid = null;

            if (!customSelect) {
                customSelect = document.createElement('div');
                customSelect.id = 'custom-time-select';
                customSelect.style.position = 'relative';
                
                // Trigger button
                const trigger = document.createElement('div');
                trigger.className = 'form-input';
                trigger.style.cursor = 'pointer';
                trigger.style.display = 'flex';
                trigger.style.justifyContent = 'space-between';
                trigger.style.alignItems = 'center';
                
                triggerText = document.createElement('span');
                triggerText.id = 'time-trigger-text';
                triggerText.innerText = initialVal ? formatAmPmStr(parseTimeStr(initialVal)) : '-- Select Time --';
                triggerText.style.color = initialVal ? '#334155' : '#94a3b8';
                
                icon = document.createElement('i');
                icon.className = 'fas fa-chevron-down';
                icon.style.color = '#94a3b8';
                icon.style.fontSize = '0.8rem';
                
                trigger.appendChild(triggerText);
                trigger.appendChild(icon);
                
                // Dropdown Menu
                menu = document.createElement('div');
                menu.id = 'time-dropdown-menu';
                menu.style.display = 'none';
                menu.style.width = '100%';
                menu.style.background = '#fff';
                menu.style.border = '1px solid #e2e8f0';
                menu.style.borderRadius = '0.5rem';
                menu.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)';
                menu.style.padding = '1rem';
                menu.style.marginTop = '0.5rem';
                menu.style.maxHeight = '220px';
                menu.style.overflowY = 'auto';
                
                // Grid layout (Three columns for compactness)
                grid = document.createElement('div');
                grid.style.display = 'grid';
                grid.style.gridTemplateColumns = 'repeat(3, 1fr)';
                grid.style.gap = '0.5rem';
                
                menu.appendChild(grid);
                customSelect.appendChild(trigger);
                customSelect.appendChild(menu);
                
                timeInput.parentNode.insertBefore(customSelect, timeInput.nextSibling);
                
                // Toggle Dropdown
                trigger.onclick = (e) => {
                    e.stopPropagation();
                    const isVisible = menu.style.display === 'block';
                    menu.style.display = isVisible ? 'none' : 'block';
                    icon.className = isVisible ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
                };
                
                // Close on outside click
                document.addEventListener('click', (e) => {
                    if (!customSelect.contains(e.target)) {
                        menu.style.display = 'none';
                        icon.className = 'fas fa-chevron-down';
                    }
                });
            } else {
                grid = menu.querySelector('div');
                icon = customSelect.querySelector('i');
            }
            
            grid.innerHTML = '';
            
            for (let m = openMins; m <= closeMins; m += 30) {
                const valStr = formatTimeStr(m);
                const labelStr = formatAmPmStr(m);
                
                const chip = document.createElement('button');
                chip.type = 'button';
                chip.className = 'time-chip';
                chip.innerText = labelStr;
                chip.style.padding = '0.6rem 0.2rem';
                chip.style.border = '1px solid #cbd5e1';
                chip.style.borderRadius = '0.375rem';
                chip.style.background = '#f8fafc';
                chip.style.color = '#475569';
                chip.style.cursor = 'pointer';
                chip.style.fontSize = '0.8rem';
                chip.style.textAlign = 'center';
                chip.style.transition = 'all 0.1s';
                
                if (valStr === initialVal) {
                    chip.style.background = 'var(--wiz-primary, #ff7b54)';
                    chip.style.color = '#fff';
                    chip.style.borderColor = 'var(--wiz-primary, #ff7b54)';
                }
                
                chip.onmouseenter = function() {
                    if (timeInput.value !== valStr) {
                        this.style.background = '#e2e8f0';
                    }
                };
                chip.onmouseleave = function() {
                    if (timeInput.value !== valStr) {
                        this.style.background = '#f8fafc';
                    }
                };
                
                chip.onclick = function(e) {
                    e.stopPropagation();
                    
                    Array.from(grid.children).forEach(c => {
                        c.style.background = '#f8fafc';
                        c.style.color = '#475569';
                        c.style.borderColor = '#cbd5e1';
                    });
                    
                    this.style.background = 'var(--wiz-primary, #ff7b54)';
                    this.style.color = '#fff';
                    this.style.borderColor = 'var(--wiz-primary, #ff7b54)';
                    
                    timeInput.value = valStr;
                    triggerText.innerText = labelStr;
                    triggerText.style.color = '#334155';
                    
                    menu.style.display = 'none';
                    icon.className = 'fas fa-chevron-down';
                    
                    timeInput.classList.remove('error');
                    const errTime = document.getElementById('err-time');
                    if (errTime) errTime.classList.remove('show');
                    
                    if (typeof validateEventTime === 'function') validateEventTime();
                };
                
                grid.appendChild(chip);
            }
        }
        
        let hintLabel = document.getElementById('time-hint-label');
        if (!hintLabel) {
            hintLabel = document.createElement('div');
            hintLabel.id = 'time-hint-label';
            hintLabel.style.fontSize = '0.75rem';
            hintLabel.style.color = '#64748b';
            hintLabel.style.marginTop = '0.5rem';
            timeInput.parentNode.insertBefore(hintLabel, timeInput.nextSibling);
        }
        hintLabel.innerText = `Select your preferred start time from the available schedule.`;

        timeInput.addEventListener('change', validateEventTime);
        timeInput.addEventListener('blur', validateEventTime);
    }

    if (provinceSelect) {
        provinceSelect.addEventListener('change', () => validateField(provinceSelect, 'err-province', v => v !== ''));
        provinceSelect.addEventListener('blur', () => validateField(provinceSelect, 'err-province', v => v !== ''));
    }
    if (citySelect) {
        citySelect.addEventListener('change', () => validateField(citySelect, 'err-city', v => v !== ''));
        citySelect.addEventListener('blur', () => validateField(citySelect, 'err-city', v => v !== ''));
    }
    if (barangaySelect) {
        barangaySelect.addEventListener('change', () => validateField(barangaySelect, 'err-barangay', v => v !== ''));
        barangaySelect.addEventListener('blur', () => validateField(barangaySelect, 'err-barangay', v => v !== ''));
    }

    if (form) {
        form.addEventListener('submit', function (e) {
            try {
                let isValid = true;
                const check = (result) => { if (!result) isValid = false; };

                if (eventName) check(validateField(eventName, 'err-name', v => (v || '').trim().length > 0));
                
                if (eventTypeSelect) {
                    check(validateField(eventTypeSelect, 'err-type', v => v !== ''));
                    if (eventTypeSelect.value === 'Other') {
                        check(validateField(otherEventInput, 'err-other-type', v => (v || '').trim().length > 0));
                    }
                }

                if (guestDisplay) check(validateGuestCount());
                if (dateInput) check(validateEventDate());
                if (timeInput) check(validateEventTime());
                
                if (provinceSelect) check(validateField(provinceSelect, 'err-province', v => v !== ''));
                if (citySelect) check(validateField(citySelect, 'err-city', v => v !== ''));
                if (barangaySelect) check(validateField(barangaySelect, 'err-barangay', v => v !== ''));
                
                // Selection Rules Validation
                const selectionGroups = document.querySelectorAll('.selection-group');
                let selectionErrorMsg = '';
                if (selectionGroups && selectionGroups.length > 0) {
                    selectionGroups.forEach(group => {
                        try {
                            const limit = parseInt(group.dataset.limit) || 0;
                            const catRaw = group.dataset.category;
                            if (!catRaw) return;
                            const count = group.querySelectorAll('input[type="checkbox"]:checked').length;
                            
                            if (count !== limit && limit > 0) {
                                isValid = false;
                                selectionErrorMsg += `• Please select exactly ${limit} item(s) for ${catRaw.replace(/([A-Z])/g, ' $1').trim()}.\n`;
                                const counterEl = document.getElementById(`counter-${catRaw}`);
                                if (counterEl) {
                                    counterEl.style.background = '#fee2e2';
                                    counterEl.style.color = '#b91c1c';
                                }
                            }
                        } catch(err) {
                            console.error("Selection rule check error:", err);
                        }
                    });
                }

                if (selectionErrorMsg) {
                    alert("Incomplete Menu Setup:\n\n" + selectionErrorMsg);
                }

                if (!isValid) {
                    e.preventDefault();
                    e.stopPropagation();
                    const firstError = document.querySelector('.field-error.show');
                    if (firstError) {
                        firstError.parentElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                    
                    // Recover the submit button from loading state if it was activated by main.js
                    const submitBtn = document.getElementById('submitBtn');
                    if (submitBtn && submitBtn.classList.contains('is-loading')) {
                        submitBtn.innerHTML = `Next: Verify Identity <i class="fas fa-id-card"></i>`;
                        submitBtn.disabled = false;
                        submitBtn.classList.remove('is-loading');
                    }
                }
            } catch (err) {
                console.error("Fatal validation error:", err);
                e.preventDefault();
                alert("An error occurred during form validation. Please check your inputs.");
            }
        });
    }

    // Handle Backend Validation Errors
    const urlParams = new URLSearchParams(window.location.search);
    const bookingError = urlParams.get('booking_error');
    if (bookingError) {
        let errorId = 'err-date';
        let errorMsg = decodeURIComponent(bookingError);
        let targetInput = dateInput;
        
        if (errorMsg.includes(':')) {
            const parts = errorMsg.split(':');
            errorId = parts[0];
            errorMsg = parts.slice(1).join(':');
            
            if (errorId === 'err-type') targetInput = eventTypeSelect;
            else if (errorId === 'err-name') targetInput = eventName;
            else if (errorId === 'err-time') targetInput = timeInput;
        }
        
        const errSpan = document.getElementById(errorId);
        if (errSpan && targetInput) {
            errSpan.innerText = errorMsg;
            errSpan.classList.add('show');
            targetInput.classList.add('error');
            targetInput.scrollIntoView({behavior: 'smooth', block: 'center'});
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
        const catSelect = document.getElementById('swapCategoryFilter');

        title.innerText = `Swap Dish`;
        container.innerHTML = '<p class="form-subtitle">Loading items...</p>';
        modal.style.display = 'flex';

        // Get all unique categories for the dropdown
        const allOptions = window.allMenuItems.filter(i => !i.is_addon);
        const categories = [...new Set(allOptions.map(i => i.category))].sort();
        
        if (catSelect) {
            catSelect.innerHTML = `<option value="all">All Categories</option>`;
            categories.forEach(cat => {
                const opt = document.createElement('option');
                opt.value = cat;
                opt.innerText = cat;
                if (cat === category) opt.selected = true;
                catSelect.appendChild(opt);
            });
        }

        window.filterSwapOptions(category);
    };

    window.filterSwapOptions = function(categoryFilter) {
        const container = document.getElementById('swapOptionsContainer');
        container.innerHTML = '';
        
        let options = window.allMenuItems.filter(i => !i.is_addon);
        if (categoryFilter !== 'all') {
            options = options.filter(i => i.category === categoryFilter);
        }

        // Exclude items already selected in the package
        const selectedIds = Array.from(document.querySelectorAll('.slot-input, input[name="selected_items"]:checked')).map(input => parseInt(input.value));
        options = options.filter(i => !selectedIds.includes(i.id));

        if (options.length === 0) {
            container.innerHTML = `<p class="form-subtitle">No alternative options available.</p>`;
            return;
        }

        options.forEach(item => {
            const card = document.createElement('div');
            card.className = 'swap-option-card';
            let feeBadge = '';
            if (item.upgrade_fee > 0) {
                feeBadge = `<span style="font-size: 0.65rem; color: #4338ca; background: #eef2ff; padding: 1px 6px; border-radius: 4px; font-weight: 700; margin-top: 4px; display: inline-block; width: fit-content;">+₱${item.upgrade_fee}/pax</span>`;
            }
            card.innerHTML = `
                <div class="soc-info">
                    <span class="soc-name">${item.name}</span>
                    <span class="soc-cat">${item.category}</span>
                    ${feeBadge}
                </div>
                <button type="button" class="btn-select-swap" onclick="selectSwapItem(${item.id}, '${item.name.replace(/'/g, "\\'")}', ${item.upgrade_fee || 0})">Select</button>
            `;
            card.onclick = () => selectSwapItem(item.id, item.name, item.upgrade_fee || 0);
            container.appendChild(card);
        });
    };

    window.closeSwapModal = function() {
        document.getElementById('swapModal').style.display = 'none';
        activeSlotIndex = null;
    };

    window.selectSwapItem = function(itemId, itemName, upgradeFee = 0) {
        if (!activeSlotIndex) return;

        const slot = document.getElementById(`slot-${activeSlotIndex}`);
        const input = slot.querySelector('.slot-input');
        const nameSpan = document.getElementById(`name-${activeSlotIndex}`);

        if (input && nameSpan) {
            input.value = itemId;
            input.setAttribute('data-upgrade-fee', upgradeFee);
            
            nameSpan.innerText = itemName;
            
            const infoDiv = nameSpan.parentElement;
            const existingBadge = infoDiv.querySelector('.upgrade-badge');
            if (existingBadge) existingBadge.remove();

            if (upgradeFee > 0) {
                const badge = document.createElement('span');
                badge.className = 'upgrade-badge';
                badge.style.cssText = 'font-size: 0.65rem; color: #4338ca; background: #eef2ff; padding: 1px 6px; border-radius: 4px; font-weight: 700; margin-top: 4px; display: inline-block; width: fit-content;';
                badge.innerText = `+₱${upgradeFee}/pax`;
                infoDiv.appendChild(badge);
            }
            
            // Visual feedback
            slot.style.borderColor = 'var(--wiz-primary)';
            slot.style.background = 'rgba(255, 123, 84, 0.05)';
            setTimeout(() => {
                slot.style.background = 'var(--wiz-slate-50)';
            }, 500);
            
            window.updateCalculator();
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

    // Initialize checkmarks for already selected items (like back navigation or edit mode)
    document.querySelectorAll('.menu-item-card input[type="checkbox"]:checked').forEach(cb => {
        if (cb.closest('.selection-group')) {
            // Trigger rule limit UI without resetting the others immediately
            window.handleSelectionRuleLimit(cb);
        } else {
            window.handleMenuCardToggle(cb);
        }
    });
    } catch (globalErr) {
        console.error("FATAL SCRIPT ERROR:", globalErr);
        alert("Fatal JS Error: " + globalErr.message);
    }
});
