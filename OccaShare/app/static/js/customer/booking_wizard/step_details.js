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

    const evAvail = parsedRules.event_availability || {};
    const leadTime = Number(evAvail.lead_time_days || window.bookingLeadTime || 3);
    const maxAdvVal = Number(evAvail.max_advance_val || 6);
    const maxAdvUnit = (evAvail.max_advance_unit || 'months').toLowerCase();

    let eventEarliest = evAvail.opening_time || '08:00';
    let eventLatest = evAvail.closing_time || '22:00';
    if (!evAvail.opening_time && parsedRules.service_rules) {
        eventEarliest = parsedRules.service_rules.earliest_start || eventEarliest;
        eventLatest = parsedRules.service_rules.latest_end || eventLatest;
    }

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

    // --- 1. Set Min and Max Date based on Lead Time and Max Advance ---
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
    if (maxAdvUnit === 'days') {
        maxCalendarDate.setDate(maxCalendarDate.getDate() + maxAdvVal);
    } else if (maxAdvUnit === 'years') {
        maxCalendarDate.setFullYear(maxCalendarDate.getFullYear() + maxAdvVal);
    } else {
        // default months
        maxCalendarDate.setMonth(maxCalendarDate.getMonth() + maxAdvVal);
    }
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

    // --- 2. Dynamic Package Switching & Inclusions Rendering ---
    window.switchPackage = function (packageId) {
        if (!window.packagesMap || !window.packagesMap[packageId]) return;
        const pkg = window.packagesMap[packageId];
        window.currentPackageId = packageId;

        // 1. Update package_id form control & event_type
        const pkgSelect = document.getElementById('package_id_select');
        if (pkgSelect) pkgSelect.value = pkg.id;

        const pkgHidden = document.getElementById('package_id_hidden');
        if (pkgHidden) pkgHidden.value = pkg.id;

        const eventTypeHidden = document.getElementById('event_type_hidden');
        if (eventTypeHidden) eventTypeHidden.value = pkg.event_type || 'General Catering';

        const eventTypeTextVal = document.getElementById('event_type_text_val');
        if (eventTypeTextVal) eventTypeTextVal.innerText = pkg.event_type || 'General Catering';

        // 2. Update pricing & capacity state
        window.pricingMode = pkg.pricing_mode || 'per_pax';
        window.pricePerHead = Number(pkg.price_per_head || 0);
        window.basePrice = Number(pkg.price || 0);
        window.additionalGuestPrice = Number(pkg.additional_guest_price || 0);
        window.minGuests = Number(pkg.min_guests || 1);
        window.maxGuests = Number(pkg.max_guests || 1000);

        // 3. Update guest count labels & bounds
        const minSpan = document.getElementById('min_guests_span');
        if (minSpan) minSpan.innerText = window.minGuests;
        const maxSpan = document.getElementById('max_guests_span');
        if (maxSpan) maxSpan.innerText = window.maxGuests || '1,000';
        const errGuests = document.getElementById('err-guests');
        if (errGuests) errGuests.innerText = `Please enter at least ${window.minGuests} guests for this package.`;

        // 4. Update sidebar price row
        const calcPkgPriceLabel = document.getElementById('calc-pkg-price-label');
        if (calcPkgPriceLabel) {
            if (window.pricingMode === 'per_pax' || pkg.price_unit === 'per_guest') {
                calcPkgPriceLabel.innerText = `₱${window.pricePerHead.toLocaleString(undefined, { minimumFractionDigits: 2 })}/pax`;
            } else {
                calcPkgPriceLabel.innerText = `₱${window.basePrice.toLocaleString(undefined, { minimumFractionDigits: 2 })} total`;
            }
        }

        // 5. Update Inclusions Section
        window.renderInclusions(pkg.grouped_inclusions || { food: [], services: [], equipment: [] });

        // 6. Recalculate Total
        window.updateCalculator();
    };

    window.renderInclusions = function (inclusions) {
        const card = document.getElementById('package-inclusions-card');
        const foodBlock = document.getElementById('inclusions-food-block');
        const foodGrid = document.getElementById('inclusions-food-grid');
        const foodCount = document.getElementById('inclusions-food-count');

        const servBlock = document.getElementById('inclusions-services-block');
        const servGrid = document.getElementById('inclusions-services-grid');
        const servCount = document.getElementById('inclusions-services-count');

        const equipBlock = document.getElementById('inclusions-equipment-block');
        const equipGrid = document.getElementById('inclusions-equipment-grid');
        const equipCount = document.getElementById('inclusions-equipment-count');

        const escapeHtml = (str) => {
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        };

        const renderGroup = (items, block, grid, countEl) => {
            if (!block || !grid) return;
            if (!items || items.length === 0) {
                block.style.display = 'none';
                grid.innerHTML = '';
                return;
            }
            block.style.display = 'block';
            if (countEl) countEl.innerText = `${items.length} items`;

            let html = '';
            items.forEach(item => {
                const qtyStr = item.quantity ? ` <span style="color: #64748b; font-weight: 500;"> — ${escapeHtml(item.quantity)}</span>` : '';
                const descStr = item.description ? `<div style="font-size: 0.75rem; color: #94a3b8; margin-top: 1px;">${escapeHtml(item.description)}</div>` : '';
                html += `
                <div class="inclusion-line-item" style="display: flex; align-items: flex-start; gap: 8px; font-size: 0.875rem; line-height: 1.45;">
                    <span style="color: var(--wiz-primary, #FF7B54); font-weight: 900; font-size: 1rem; line-height: 1.2;">•</span>
                    <div style="flex: 1; min-width: 0; word-break: break-word;">
                        <strong style="color: #1e293b; font-weight: 700;">${escapeHtml(item.name)}</strong>${qtyStr}
                        ${descStr}
                    </div>
                </div>`;
            });
            grid.innerHTML = html;
        };

        renderGroup(inclusions.food, foodBlock, foodGrid, foodCount);
        renderGroup(inclusions.services, servBlock, servGrid, servCount);
        renderGroup(inclusions.equipment, equipBlock, equipGrid, equipCount);

        const hasAny = (inclusions.food && inclusions.food.length > 0) ||
                       (inclusions.services && inclusions.services.length > 0) ||
                       (inclusions.equipment && inclusions.equipment.length > 0);

        if (card) {
            card.style.display = hasAny ? 'block' : 'none';
        }
    };

    // --- 2.5. Update Calculator ---
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

        const activePricePerHead = Number(window.pricePerHead || 0);
        const activeBasePrice = Number(window.basePrice || 0);
        const activeMinGuests = Number(window.minGuests || 1);
        const activeAddPrice = Number(window.additionalGuestPrice || 0);

        if (window.pricingMode === 'fixed') {
            basePackageTotal = activeBasePrice;
            if (guests > activeMinGuests && activeAddPrice > 0) {
                excessGuestsTotal = (guests - activeMinGuests) * activeAddPrice;
            }
            total = basePackageTotal + excessGuestsTotal;
        } else {
            total = guests * activePricePerHead;
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
            } else if (window.deliveryFeeStatus === "error") {
                calcDeliveryFee.innerHTML = '<span style="color:red;">Out of Coverage</span>';
            } else if (window.deliveryFeeStatus === "pending") {
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

    // --- 3. Check Date & Time Availability ---
    let isAvailabilityValid = true;

    window.checkAvailability = async function () {
        const chip = document.getElementById('availability-chip');
        if (!chip) return;

        const date = dateInput ? dateInput.value : '';
        const time = timeInput ? timeInput.value : '';

        if (!date) {
            chip.style.display = 'none';
            return;
        }

        // 1. Client-Side instant checks
        // 1.1 Caterer temporarily unavailable status
        if (evAvail.status === 'temporarily_unavailable') {
            chip.className = 'availability-chip booked';
            chip.style.display = 'inline-flex';
            chip.innerHTML = '<i class="fas fa-ban"></i> This caterer is temporarily unavailable and not accepting new bookings.';
            if (submitBtn) submitBtn.disabled = true;
            isAvailabilityValid = false;
            return;
        }

        // 1.2 Operating days check
        const parts = date.split('-');
        if (parts.length === 3) {
            const selectedDate = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
            const daysOfWeek = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
            const selectedDayName = daysOfWeek[selectedDate.getDay()];
            const operatingDays = evAvail.operating_days || ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

            if (operatingDays.length > 0 && operatingDays.length < 7 && !operatingDays.includes(selectedDayName)) {
                chip.className = 'availability-chip booked';
                chip.style.display = 'inline-flex';
                chip.innerHTML = '<i class="fas fa-calendar-times"></i> The caterer does not accept bookings on this day. Please select another date.';
                if (submitBtn) submitBtn.disabled = true;
                isAvailabilityValid = false;
                return;
            }

            // 1.3 Minimum booking lead time check
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const diffDays = Math.ceil((selectedDate - today) / (1000 * 60 * 60 * 24));
            if (diffDays < leadTime) {
                chip.className = 'availability-chip booked';
                chip.style.display = 'inline-flex';
                chip.innerHTML = `<i class="fas fa-clock"></i> This caterer requires bookings at least ${leadTime} days before the event date. Please select a later date.`;
                if (submitBtn) submitBtn.disabled = true;
                isAvailabilityValid = false;
                return;
            }

            // 1.4 Maximum advance booking check
            const maxBound = new Date(maxCalendarDate);
            maxBound.setHours(23, 59, 59, 999);
            if (selectedDate > maxBound) {
                chip.className = 'availability-chip booked';
                chip.style.display = 'inline-flex';
                const advText = maxAdvUnit === 'years' ? (maxAdvVal === 1 ? '1 year' : `${maxAdvVal} years`) : (maxAdvUnit === 'days' ? `${maxAdvVal} days` : (maxAdvVal === 1 ? '1 month' : `${maxAdvVal} months`));
                chip.innerHTML = `<i class="fas fa-calendar-times"></i> This caterer only accepts bookings up to ${advText} in advance.`;
                if (submitBtn) submitBtn.disabled = true;
                isAvailabilityValid = false;
                return;
            }

            // 1.5 Blocked dates check from settings
            const blocked = evAvail.blocked_dates || [];
            const isBlocked = blocked.some(b => (typeof b === 'string' ? b : b.date) === date);
            if (isBlocked) {
                chip.className = 'availability-chip booked';
                chip.style.display = 'inline-flex';
                chip.innerHTML = '<i class="fas fa-ban"></i> This date is unavailable for this caterer. Please select another date.';
                if (submitBtn) submitBtn.disabled = true;
                isAvailabilityValid = false;
                return;
            }
        }

        // 1.6 Time operating hours check (if time provided)
        if (time) {
            const parseMinutes = (tStr) => {
                const [h, m] = (tStr || '0:0').split(':').map(Number);
                return (h || 0) * 60 + (m || 0);
            };
            const selMins = parseMinutes(time);
            const openMins = parseMinutes(eventEarliest);
            const closeMins = parseMinutes(eventLatest);
            if (selMins < openMins || selMins > closeMins) {
                chip.className = 'availability-chip booked';
                chip.style.display = 'inline-flex';
                chip.innerHTML = '<i class="fas fa-clock"></i> The selected event time is outside the caterer’s available hours. Please select another time.';
                if (submitBtn) submitBtn.disabled = true;
                isAvailabilityValid = false;
                return;
            }
        }

        // 2. Query backend API for DB-level checks (capacity, availability table, collisions)
        chip.className = 'availability-chip checking';
        chip.style.display = 'inline-flex';
        chip.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking availability...';

        const bookingIdInput = document.querySelector('input[name="booking_id"]');
        const bookingIdVal = bookingIdInput ? bookingIdInput.value : '';

        let apiUrl = `/packages/api/check-availability?caterer_id=${catererId}&date_str=${date}`;
        if (time) apiUrl += `&time_str=${time}`;
        if (bookingIdVal) apiUrl += `&booking_id=${bookingIdVal}`;

        try {
            const response = await fetch(apiUrl);
            if (!response.ok) throw new Error('API request failed');
            const data = await response.json();

            if (data.available) {
                chip.className = 'availability-chip available';
                chip.style.display = 'inline-flex';
                chip.innerHTML = `<i class="fas fa-check-circle"></i> ${data.message || 'This date and time is available for booking.'}`;
                if (submitBtn) submitBtn.disabled = false;
                isAvailabilityValid = true;
            } else {
                chip.className = 'availability-chip booked';
                chip.style.display = 'inline-flex';
                chip.innerHTML = `<i class="fas fa-times-circle"></i> ${data.message || 'This date is unavailable for this caterer. Please select another date.'}`;
                if (submitBtn) submitBtn.disabled = true;
                isAvailabilityValid = false;
            }
        } catch (error) {
            console.warn('Could not verify availability with server:', error);
            chip.className = 'availability-chip available';
            chip.style.display = 'inline-flex';
            chip.innerHTML = '<i class="fas fa-check-circle"></i> Date selected (offline check passed)';
            if (submitBtn) submitBtn.disabled = false;
            isAvailabilityValid = true;
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
            const errEl = document.getElementById('err-date');
            if (!v) {
                if (errEl) errEl.innerText = `Please select an event date.`;
                return false;
            }
            const parts = v.split('-');
            if(parts.length !== 3) {
                if (errEl) errEl.innerText = `Please enter a valid date.`;
                return false;
            }
            const selectedDate = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
            
            const minDate = new Date();
            minDate.setDate(minDate.getDate() + leadTime - 1);
            minDate.setHours(0,0,0,0);
            
            const maxDate = new Date(maxCalendarDate);
            maxDate.setHours(23,59,59,999);
            
            if (selectedDate <= minDate) {
                if (errEl) errEl.innerText = `This caterer requires bookings at least ${leadTime} days before the event date.`;
                return false;
            }
            if (selectedDate > maxDate) {
                const advText = maxAdvUnit === 'years' ? (maxAdvVal === 1 ? '1 year' : `${maxAdvVal} years`) : (maxAdvUnit === 'days' ? `${maxAdvVal} days` : (maxAdvVal === 1 ? '1 month' : `${maxAdvVal} months`));
                if (errEl) errEl.innerText = `Bookings can only be made up to ${advText} in advance.`;
                return false;
            }
            
            // Operating days check
            const opDays = evAvail.operating_days || (window.catererRules && window.catererRules.business_hours && window.catererRules.business_hours.operating_days);
            if (opDays && opDays.length > 0 && opDays.length < 7) {
                const daysOfWeek = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
                const selectedDayName = daysOfWeek[selectedDate.getDay()];
                if (!opDays.includes(selectedDayName)) {
                    if (errEl) errEl.innerText = `Caterer does not accept bookings on ${selectedDayName}s.`;
                    return false;
                }
            }
            
            return true;
        }, null);
    };
    if (dateInput) {
        dateInput.addEventListener('input', () => { validateEventDate(); window.checkAvailability(); });
        dateInput.addEventListener('change', () => { validateEventDate(); window.checkAvailability(); });
        dateInput.addEventListener('blur', validateEventDate);
    }

    const validateEventTime = () => {
        if (!timeInput) return true;
        return validateField(timeInput, 'err-time', v => {
            const customTrigger = document.getElementById('time-trigger-btn') || document.querySelector('#custom-time-select .form-input');
            if (!v) {
                if (customTrigger) customTrigger.classList.add('error');
                return false;
            }
            const parts = v.split(':');
            if (parts.length !== 2) {
                if (customTrigger) customTrigger.classList.add('error');
                return false;
            }
            const hour = parseInt(parts[0], 10);
            const min = parseInt(parts[1], 10);
            
            const parseTime = (timeStr) => {
                const [h, m] = (timeStr || '0:0').split(':').map(Number);
                return (h || 0) * 60 + (m || 0);
            };
            
            const formatAmPm = (mins) => {
                const h = Math.floor(mins / 60);
                const m = mins % 60;
                const ampm = h >= 12 ? 'PM' : 'AM';
                const h12 = h % 12 || 12;
                return `${h12}:${m.toString().padStart(2, '0')} ${ampm}`;
            };
            
            const selectedMins = hour * 60 + min;
            const eventStartMins = parseTime(eventEarliest);
            const eventEndMins = parseTime(eventLatest);
            
            const startFormatted = formatAmPm(eventStartMins);
            const endFormatted = formatAmPm(eventEndMins);
            
            if (selectedMins < eventStartMins || selectedMins > eventEndMins) {
                const errTime = document.getElementById('err-time');
                if (errTime) errTime.innerText = `The selected event time is outside the caterer’s available hours (${startFormatted} - ${endFormatted}).`;
                if (customTrigger) customTrigger.classList.add('error');
                return false;
            }
            if (customTrigger) customTrigger.classList.remove('error');
            return true;
        }, "Please select a valid time.");
    };

    if (timeInput) {
        const parseTimeStr = (t) => {
            const [h,m] = (t || '').split(':').map(Number);
            return (h || 0) * 60 + (m || 0);
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
        
        const eventStartMins = parseTimeStr(eventEarliest);
        const eventEndMins = parseTimeStr(eventLatest);
        
        const initialVal = timeInput.getAttribute('data-initial') || timeInput.value || '';
        
        const triggerBtn = document.getElementById('time-trigger-btn');
        const triggerText = document.getElementById('time-trigger-text');
        const triggerIcon = document.getElementById('time-trigger-icon');
        const dropdownMenu = document.getElementById('time-dropdown-menu');
        const chipsGrid = document.getElementById('time-chips-grid');

        if (triggerBtn && dropdownMenu && chipsGrid) {
            if (initialVal) {
                timeInput.value = initialVal;
                if (triggerText) {
                    triggerText.innerText = formatAmPmStr(parseTimeStr(initialVal));
                    triggerText.style.color = '#0f172a';
                }
            }

            // Toggle Dropdown
            triggerBtn.onclick = (e) => {
                e.stopPropagation();
                const isVisible = dropdownMenu.style.display === 'block';
                dropdownMenu.style.display = isVisible ? 'none' : 'block';
                if (triggerIcon) triggerIcon.className = isVisible ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
            };

            // Close on outside click
            document.addEventListener('click', (e) => {
                const customSelect = document.getElementById('custom-time-select');
                if (customSelect && !customSelect.contains(e.target)) {
                    dropdownMenu.style.display = 'none';
                    if (triggerIcon) triggerIcon.className = 'fas fa-chevron-down';
                }
            });

            // Populate time chips for event hours
            chipsGrid.innerHTML = '';
            for (let m = eventStartMins; m <= eventEndMins; m += 30) {
                const valStr = formatTimeStr(m);
                const labelStr = formatAmPmStr(m);
                
                const chip = document.createElement('button');
                chip.type = 'button';
                chip.className = 'time-chip';
                chip.innerText = labelStr;
                chip.style.padding = '0.6rem 0.2rem';
                chip.style.border = '1px solid #cbd5e1';
                chip.style.borderRadius = '0.375rem';
                chip.style.background = (valStr === initialVal) ? 'var(--wiz-primary, #ff7b54)' : '#f8fafc';
                chip.style.color = (valStr === initialVal) ? '#fff' : '#475569';
                chip.style.borderColor = (valStr === initialVal) ? 'var(--wiz-primary, #ff7b54)' : '#cbd5e1';
                chip.style.cursor = 'pointer';
                chip.style.fontSize = '0.8rem';
                chip.style.fontWeight = '600';
                chip.style.textAlign = 'center';
                chip.style.transition = 'all 0.15s ease';
                
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
                    
                    Array.from(chipsGrid.children).forEach(c => {
                        c.style.background = '#f8fafc';
                        c.style.color = '#475569';
                        c.style.borderColor = '#cbd5e1';
                    });
                    
                    this.style.background = 'var(--wiz-primary, #ff7b54)';
                    this.style.color = '#fff';
                    this.style.borderColor = 'var(--wiz-primary, #ff7b54)';
                    
                    timeInput.value = valStr;
                    if (triggerText) {
                        triggerText.innerText = labelStr;
                        triggerText.style.color = '#0f172a';
                    }
                    
                    dropdownMenu.style.display = 'none';
                    if (triggerIcon) triggerIcon.className = 'fas fa-chevron-down';
                    
                    if (triggerBtn) triggerBtn.classList.remove('error');
                    timeInput.classList.remove('error');
                    const errTime = document.getElementById('err-time');
                    if (errTime) errTime.classList.remove('show');
                    
                    validateEventTime();
                    if (typeof window.checkAvailability === 'function') {
                        window.checkAvailability();
                    }
                };
                
                chipsGrid.appendChild(chip);
            }
        }

        timeInput.addEventListener('change', () => { validateEventTime(); window.checkAvailability(); });
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
                console.log('[BookingWizard] Form submit triggered');
                let isValid = true;
                const check = (label, result) => {
                    if (!result) {
                        console.warn('[BookingWizard] FAILED:', label);
                        isValid = false;
                    } else {
                        console.log('[BookingWizard] OK:', label);
                    }
                };

                // 1. Event name
                check('event_name', eventName ? validateField(eventName, 'err-name', v => (v || '').trim().length > 0) : true);

                // 2. Event type (locked from package — hidden input)
                const eventTypeHidden = document.getElementById('event_type_hidden');
                if (eventTypeHidden) {
                    check('event_type_hidden', validateField(eventTypeHidden, 'err-type', v => (v || '').trim().length > 0));
                } else if (eventTypeSelect) {
                    check('event_type_select', validateField(eventTypeSelect, 'err-type', v => v !== ''));
                    if (eventTypeSelect.value === 'Other' && otherEventInput) {
                        check('other_event_type', validateField(otherEventInput, 'err-other-type', v => (v || '').trim().length > 0));
                    }
                }

                // 3. Guest count
                check('guest_count', guestDisplay ? validateGuestCount() : true);

                // 4. Event date
                check('event_date', dateInput ? validateEventDate() : true);

                // 5. Event time
                check('event_time', timeInput ? validateEventTime() : true);

                // 5.1 Booking availability
                if (!isAvailabilityValid) {
                    console.warn('[BookingWizard] FAILED: caterer availability check failed');
                    isValid = false;
                }

                // 6. Location — construct venue_address from selects NOW (in case async hasn't updated the hidden)
                const pEl = document.getElementById('province_select');
                const cEl = document.getElementById('city_select');
                const bEl = document.getElementById('barangay_select');
                const pVal = pEl ? (pEl.options[pEl.selectedIndex] ? pEl.options[pEl.selectedIndex].value : '') : '';
                const cVal = cEl ? (cEl.options[cEl.selectedIndex] ? cEl.options[cEl.selectedIndex].value : '') : '';
                const bVal = bEl ? (bEl.options[bEl.selectedIndex] ? bEl.options[bEl.selectedIndex].value : '') : '';

                if (pVal && pVal !== '' && cVal && cVal !== '' && bVal && bVal !== '') {
                    // Update the hidden venue_address right now before submission
                    if (venueHidden) venueHidden.value = `${bVal}, ${cVal}, ${pVal}`;
                }

                const hasProvince = pVal && pVal !== '';
                const hasCity = cVal && cVal !== '';
                const hasBarangay = bVal && bVal !== '';

                if (!hasProvince) {
                    console.warn('[BookingWizard] FAILED: province');
                    if (provinceSelect) validateField(provinceSelect, 'err-province', v => v !== '');
                    isValid = false;
                } else if (!hasCity) {
                    console.warn('[BookingWizard] FAILED: city');
                    if (citySelect) validateField(citySelect, 'err-city', v => v !== '');
                    isValid = false;
                } else if (!hasBarangay) {
                    console.warn('[BookingWizard] FAILED: barangay');
                    if (barangaySelect) validateField(barangaySelect, 'err-barangay', v => v !== '');
                    isValid = false;
                } else {
                    console.log('[BookingWizard] OK: location =', venueHidden ? venueHidden.value : 'n/a');
                }

                // 7. Delivery fee coverage
                if (window.deliveryFeeStatus === "error") {
                    console.warn('[BookingWizard] FAILED: out of delivery coverage');
                    isValid = false;
                    if (window.Swal) {
                        Swal.fire({ icon: 'error', title: 'Out of Coverage', text: 'Sorry, the caterer does not deliver to your specified location.', confirmButtonColor: '#FF7B54' });
                    } else {
                        alert('Out of Coverage: Sorry, the caterer does not deliver to your specified location.');
                    }
                }

                // 8. Menu selection rules
                const selectionGroups = document.querySelectorAll('.selection-group');
                let selectionErrorMsg = '';
                if (selectionGroups && selectionGroups.length > 0) {
                    selectionGroups.forEach(group => {
                        try {
                            const limit = parseInt(group.dataset.limit) || 0;
                            const catRaw = group.dataset.category;
                            if (!catRaw || limit === 0) return;
                            const count = group.querySelectorAll('input[type="checkbox"]:checked').length;

                            if (count !== limit) {
                                isValid = false;
                                selectionErrorMsg += `• Please select exactly ${limit} item(s) for ${catRaw.replace(/([A-Z])/g, ' $1').trim()}.
`;
                                const counterEl = document.getElementById(`counter-${catRaw}`);
                                if (counterEl) {
                                    counterEl.style.background = '#fee2e2';
                                    counterEl.style.color = '#b91c1c';
                                }
                            }
                        } catch(err) {
                            console.error('Selection rule check error:', err);
                        }
                    });
                }

                if (selectionErrorMsg) {
                    if (window.Swal) {
                        Swal.fire({ icon: 'warning', title: 'Incomplete Menu Setup', text: selectionErrorMsg, confirmButtonColor: '#FF7B54' });
                    } else {
                        alert('Incomplete Menu Setup:\n\n' + selectionErrorMsg);
                    }
                }

                console.log('[BookingWizard] isValid =', isValid);

                if (!isValid) {
                    e.preventDefault();
                    e.stopPropagation();

                    const firstError = document.querySelector('.field-error.show');
                    if (firstError) {
                        firstError.parentElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }

                    // Reset the submit button if main.js already started its loading state
                    const submitBtnEl = document.getElementById('submitBtn');
                    if (submitBtnEl) {
                        submitBtnEl.innerHTML = `Next Step: Identity <i class="fas fa-arrow-right"></i>`;
                        submitBtnEl.disabled = false;
                        submitBtnEl.classList.remove('is-loading');
                    }

                    if (!isAvailabilityValid) {
                        const chip = document.getElementById('availability-chip');
                        const chipMsg = chip ? chip.innerText : 'The selected date or time is not available for booking.';
                        if (window.Swal) {
                            Swal.fire({
                                icon: 'warning',
                                title: 'Date / Time Unavailable',
                                text: chipMsg || 'The selected date or time is not available for booking. Please select another date or time.',
                                confirmButtonColor: '#FF7B54'
                            });
                        } else {
                            alert(chipMsg || 'The selected date or time is not available for booking. Please select another date or time.');
                        }
                    } else if (!selectionErrorMsg && window.deliveryFeeStatus !== 'error') {
                        if (window.Swal) {
                            Swal.fire({
                                icon: 'warning',
                                title: 'Please complete all required fields',
                                text: 'Check your Event Date, Time, Venue Location, and Guest Count.',
                                confirmButtonColor: '#FF7B54'
                            });
                        } else {
                            alert('Please fill in all required fields (Date, Time, Location, Guest Count).');
                        }
                    }
                } else {
                    console.log('[BookingWizard] All valid — submitting form to server');
                }
            } catch (err) {
                console.error('Fatal validation error:', err);
                e.preventDefault();
                alert('An error occurred during form validation: ' + err.message);
            }
        });
    }

    // Handle Backend Validation Errors
    const urlParams = new URLSearchParams(window.location.search);
    const bookingError = urlParams.get('booking_error');
    if (bookingError) {
        let errorId = null;
        let errorMsg = decodeURIComponent(bookingError).replace(/\+/g, ' ');
        let targetInput = null;

        if (errorMsg.startsWith('err-')) {
            const colonIdx = errorMsg.indexOf(':');
            if (colonIdx !== -1) {
                errorId = errorMsg.substring(0, colonIdx).trim();
                errorMsg = errorMsg.substring(colonIdx + 1).trim();
            } else {
                errorId = errorMsg.trim();
                errorMsg = 'Please correct this field.';
            }

            if (errorId === 'err-date') targetInput = dateInput;
            else if (errorId === 'err-time') {
                // time-trigger-btn is a div, not an input — mark it visually
                targetInput = timeInput;
                const timeTrigger = document.getElementById('time-trigger-btn');
                if (timeTrigger) timeTrigger.classList.add('error');
            }
            else if (errorId === 'err-name') targetInput = eventName;
            else if (errorId === 'err-type') {
                // event_type is a locked display box, highlight the parent card
                targetInput = document.getElementById('event_type_hidden');
                const displayBox = document.getElementById('event_type_display_box');
                if (displayBox) displayBox.style.border = '1.5px solid #ef4444';
            }
            else if (errorId === 'err-guests') targetInput = guestDisplay;
            else if (errorId === 'err-province') targetInput = provinceSelect;
            else if (errorId === 'err-city') targetInput = citySelect;
            else if (errorId === 'err-barangay') targetInput = barangaySelect;
        }

        const errSpan = errorId ? document.getElementById(errorId) : null;
        if (errSpan) {
            errSpan.innerText = errorMsg;
            errSpan.classList.add('show');
            if (targetInput) {
                if (targetInput.classList) targetInput.classList.add('error');
                targetInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else {
                errSpan.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        } else {
            // Generic fallback — always show the error to the user
            if (window.Swal) {
                Swal.fire({
                    icon: 'error',
                    title: 'Cannot proceed',
                    text: errorMsg,
                    confirmButtonColor: '#FF7B54'
                });
            } else {
                alert('Error: ' + errorMsg);
            }
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
    if (dateInput && dateInput.value) {
        window.checkAvailability();
    }

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
